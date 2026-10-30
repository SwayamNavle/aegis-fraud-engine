"""
Aegis Transactions API Routes
Provides paginated transaction history, detailed inspection, and idempotent prediction persistence.
"""

from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from services.api.database.connection import get_db_session
from services.api.models.db_models import TransactionRecord, PredictionRecord, FeatureRecord, FraudAlertRecord
from services.scoring.predictor import FraudPredictor
from streaming.schemas.transaction_schema import PredictionResult

router = APIRouter(prefix="/transactions", tags=["Transactions"])

# Shared predictor instance for inline scoring if scoring microservice is co-located
_predictor = None


def get_predictor():
    global _predictor
    if _predictor is None:
        _predictor = FraudPredictor()
    return _predictor


@router.get("")
async def list_transactions(
    decision: Optional[str] = Query(None, description="Filter by decision: LEGITIMATE, SUSPICIOUS, FRAUD"),
    account_id: Optional[str] = Query(None, description="Filter by account ID"),
    min_risk: Optional[float] = Query(None, ge=0.0, le=100.0, description="Minimum risk score"),
    limit: int = Query(50, ge=1, le=200, description="Page limit"),
    offset: int = Query(0, ge=0, description="Page offset"),
    db: AsyncSession = Depends(get_db_session)
):
    """Returns paginated list of scored transactions ordered by timestamp desc."""
    query = select(PredictionRecord).order_by(desc(PredictionRecord.id))

    if decision:
        query = query.where(PredictionRecord.decision == decision.upper())
    if account_id:
        query = query.where(PredictionRecord.account_id == account_id)
    if min_risk is not None:
        query = query.where(PredictionRecord.risk_score >= min_risk)

    query = query.limit(limit).offset(offset)
    result = await db.execute(query)
    records = result.scalars().all()

    return {
        "items": [r.to_dict() for r in records],
        "limit": limit,
        "offset": offset,
        "count": len(records)
    }


@router.get("/{transaction_id}")
async def get_transaction_detail(
    transaction_id: str,
    db: AsyncSession = Depends(get_db_session)
):
    """
    Returns complete transaction inspection dossier:
    - Raw transaction payload
    - Feature vector
    - Scored prediction & decision
    - Deterministic reason codes
    - Top contributing features for explainability
    """
    pred_res = await db.execute(select(PredictionRecord).where(PredictionRecord.transaction_id == transaction_id))
    pred = pred_res.scalar_one_or_none()
    if not pred:
        raise HTTPException(status_code=404, detail=f"Transaction '{transaction_id}' not found.")

    txn_res = await db.execute(select(TransactionRecord).where(TransactionRecord.transaction_id == transaction_id))
    txn = txn_res.scalar_one_or_none()

    feat_res = await db.execute(select(FeatureRecord).where(FeatureRecord.transaction_id == transaction_id))
    feat = feat_res.scalar_one_or_none()

    return {
        "transaction_id": transaction_id,
        "prediction": pred.to_dict(),
        "transaction": txn.to_dict() if txn else None,
        "features": feat.to_dict() if feat else None
    }


@router.post("/score_and_persist", response_model=PredictionResult)
async def score_and_persist(
    payload: Dict[str, Any],
    db: AsyncSession = Depends(get_db_session)
):
    """
    Idempotent processing endpoint.
    1. Checks if transaction_id has already been processed. If yes, returns existing prediction without re-insertion.
    2. Otherwise, extracts features, calculates XGBoost fraud probability, saves to DB, creates alert if high risk.
    """
    txn_id = payload.get("transaction_id")
    if not txn_id:
        raise HTTPException(status_code=400, detail="Missing transaction_id in payload.")

    # IDEMPOTENCY CHECK: Return existing prediction if already recorded
    existing_res = await db.execute(select(PredictionRecord).where(PredictionRecord.transaction_id == txn_id))
    existing = existing_res.scalar_one_or_none()
    if existing:
        return PredictionResult(
            transaction_id=existing.transaction_id,
            fraud_probability=existing.fraud_probability,
            risk_score=existing.risk_score,
            decision=existing.decision,
            model_version=existing.model_version,
            latency_ms=existing.latency_ms,
            reason_codes=existing.reason_codes or [],
            feature_contributions=existing.feature_contributions or {}
        )

    # Perform inference
    predictor = get_predictor()
    # Extract features and predict
    fv = predictor.feature_store.extract_features(payload)
    pred_result = predictor.predict(feature_vector=fv)

    # Persist transaction
    txn_record = TransactionRecord(
        transaction_id=txn_id,
        timestamp=payload.get("timestamp"),
        user_id=payload.get("user_id", "usr_unknown"),
        account_id=payload.get("account_id"),
        merchant_id=payload.get("merchant_id"),
        merchant_category=payload.get("merchant_category", "retail"),
        amount=float(payload.get("amount", 0.0)),
        currency=payload.get("currency", "INR"),
        country=payload.get("country", "IN"),
        city=payload.get("city", "Mumbai"),
        latitude=float(payload.get("latitude", 0.0)),
        longitude=float(payload.get("longitude", 0.0)),
        device_id=payload.get("device_id", "dev_unknown"),
        device_type=payload.get("device_type", "Web"),
        ip_address=payload.get("ip_address", "127.0.0.1"),
        payment_method=payload.get("payment_method", "credit_card"),
        card_present=bool(payload.get("card_present", False)),
        is_international=bool(payload.get("is_international", False)),
        previous_transaction_timestamp=payload.get("previous_transaction_timestamp")
    )
    db.add(txn_record)

    # Persist features
    feat_record = FeatureRecord(
        transaction_id=txn_id,
        account_id=fv.account_id,
        timestamp=fv.timestamp,
        transaction_count_1m=fv.transaction_count_1m,
        transaction_count_5m=fv.transaction_count_5m,
        transaction_amount_sum_5m=fv.transaction_amount_sum_5m,
        transaction_amount_avg_5m=fv.transaction_amount_avg_5m,
        transaction_amount_std_5m=fv.transaction_amount_std_5m,
        max_transaction_amount_5m=fv.max_transaction_amount_5m,
        unique_merchants_10m=fv.unique_merchants_10m,
        unique_countries_30m=fv.unique_countries_30m,
        unique_devices_30m=fv.unique_devices_30m,
        international_transaction_count=fv.international_transaction_count,
        time_since_previous_transaction=fv.time_since_previous_transaction,
        distance_from_previous_transaction=fv.distance_from_previous_transaction,
        geo_velocity_kmh=fv.geo_velocity_kmh,
        amount_z_score=fv.amount_z_score,
        user_amount_deviation=fv.user_amount_deviation,
        velocity_score=fv.velocity_score,
        merchant_risk_score=fv.merchant_risk_score,
        device_change_flag=fv.device_change_flag,
        country_change_flag=fv.country_change_flag
    )
    db.add(feat_record)

    # Persist prediction
    pred_record = PredictionRecord(
        transaction_id=txn_id,
        timestamp=payload.get("timestamp"),
        account_id=payload.get("account_id"),
        amount=float(payload.get("amount", 0.0)),
        merchant_id=payload.get("merchant_id"),
        country=payload.get("country", "IN"),
        fraud_probability=pred_result.fraud_probability,
        risk_score=pred_result.risk_score,
        decision=pred_result.decision,
        model_version=pred_result.model_version,
        latency_ms=pred_result.latency_ms,
        reason_codes=pred_result.reason_codes,
        feature_contributions=pred_result.feature_contributions
    )
    db.add(pred_record)

    # Create alert if FRAUD or SUSPICIOUS
    if pred_result.decision in ["FRAUD", "SUSPICIOUS"]:
        severity = "CRITICAL" if pred_result.risk_score >= 85.0 else ("HIGH" if pred_result.risk_score >= 70.0 else "MEDIUM")
        alert = FraudAlertRecord(
            alert_id=f"alt_{txn_id[-8:]}",
            transaction_id=txn_id,
            account_id=payload.get("account_id"),
            amount=float(payload.get("amount", 0.0)),
            severity=severity,
            risk_score=pred_result.risk_score,
            fraud_probability=pred_result.fraud_probability,
            reason_codes=pred_result.reason_codes,
            status="OPEN"
        )
        db.add(alert)

    await db.commit()
    return pred_result
