"""
Aegis Transactions API Routes
Provides paginated transaction history, detailed inspection, data quality validation,
and idempotent prediction persistence with customer/merchant profiling.
"""

from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from services.api.database.connection import get_db_session
from services.api.models.db_models import (
    TransactionRecord, PredictionRecord, FeatureRecord, FraudAlertRecord,
    CustomerProfileRecord, MerchantProfileRecord
)
from services.scoring.predictor import FraudPredictor
from services.api.data_quality import DataQualityValidator, DeadLetterQueue, DUPLICATE_TRANSACTIONS_TOTAL
from streaming.schemas.transaction_schema import PredictionResult
from risk_engine.profiler import ProfileManager

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
    decision: Optional[str] = Query(None, description="Filter: LEGITIMATE, SUSPICIOUS, FRAUD, APPROVE, REVIEW, DECLINE"),
    account_id: Optional[str] = Query(None, description="Filter by account ID"),
    min_risk: Optional[float] = Query(None, ge=0.0, le=100.0, description="Minimum risk score"),
    limit: int = Query(50, ge=1, le=200, description="Page limit"),
    offset: int = Query(0, ge=0, description="Page offset"),
    db: AsyncSession = Depends(get_db_session)
):
    """Returns paginated list of scored transactions ordered by timestamp desc."""
    query = select(PredictionRecord).order_by(desc(PredictionRecord.id))

    if decision:
        d = decision.upper()
        # Handle both business decisions and legacy decisions
        if d in ["APPROVE", "LEGITIMATE"]:
            query = query.where(PredictionRecord.decision.in_(["LEGITIMATE", "APPROVE"]))
        elif d in ["REVIEW", "SUSPICIOUS"]:
            query = query.where(PredictionRecord.decision.in_(["SUSPICIOUS", "REVIEW"]))
        elif d in ["DECLINE", "FRAUD"]:
            query = query.where(PredictionRecord.decision.in_(["FRAUD", "DECLINE"]))
        else:
            query = query.where(PredictionRecord.decision == d)

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
    - Scored prediction, business decision, and risk level
    - Deterministic reason codes and rule violations
    - Top contributing features for explainability (TreeSHAP)
    """
    pred_res = await db.execute(select(PredictionRecord).where(PredictionRecord.transaction_id == transaction_id))
    pred = pred_res.scalar_one_or_none()
    if not pred:
        raise HTTPException(status_code=404, detail=f"Transaction '{transaction_id}' not found.")

    txn_res = await db.execute(select(TransactionRecord).where(TransactionRecord.transaction_id == transaction_id))
    txn = txn_res.scalar_one_or_none()

    feat_res = await db.execute(select(FeatureRecord).where(FeatureRecord.transaction_id == transaction_id))
    feat = feat_res.scalar_one_or_none()

    # Get customer & merchant profile info if available
    acc_id = pred.account_id
    merch_id = pred.merchant_id
    profile_mgr = ProfileManager.get_instance()
    cust_profile = profile_mgr.customers.get(acc_id)
    merch_profile = profile_mgr.merchants.get(merch_id)

    return {
        "transaction_id": transaction_id,
        "prediction": pred.to_dict(),
        "transaction": txn.to_dict() if txn else None,
        "features": feat.to_dict() if feat else None,
        "customer_profile": cust_profile.to_dict() if cust_profile else None,
        "merchant_profile": merch_profile.to_dict() if merch_profile else None
    }


@router.post("/score_and_persist", response_model=PredictionResult)
async def score_and_persist(
    payload: Dict[str, Any],
    db: AsyncSession = Depends(get_db_session)
):
    """
    Idempotent processing endpoint with Data Quality validation.
    1. Validates payload invariants. Malformed events are routed to Dead-Letter Queue (DLQ).
    2. Idempotency Check: Returns existing prediction if transaction_id has already been processed.
    3. Executes multi-factor feature extraction and risk decision scoring.
    4. Updates customer and merchant risk profiles.
    5. Persists records to database and creates fraud alert if elevated risk.
    """
    # 1. DATA QUALITY LAYER
    is_valid, validation_error = DataQualityValidator.validate(payload)
    if not is_valid:
        DeadLetterQueue.send_to_dlq(payload, reason=validation_error or "Data quality validation failed")
        raise HTTPException(status_code=400, detail=f"Data Quality Violation: {validation_error}")

    txn_id = payload["transaction_id"]

    # 2. IDEMPOTENCY CHECK
    existing_res = await db.execute(select(PredictionRecord).where(PredictionRecord.transaction_id == txn_id))
    existing = existing_res.scalar_one_or_none()
    if existing:
        DUPLICATE_TRANSACTIONS_TOTAL.inc()
        return PredictionResult(
            transaction_id=existing.transaction_id,
            correlation_id=existing.correlation_id,
            fraud_probability=existing.fraud_probability,
            risk_score=existing.risk_score,
            decision=existing.decision,
            business_decision=existing.business_decision or "APPROVE",
            model_version=existing.model_version,
            latency_ms=existing.latency_ms,
            reason_codes=existing.reason_codes or [],
            feature_contributions=existing.feature_contributions or {}
        )

    # 3. FEATURE EXTRACTION & INFERENCE
    predictor = get_predictor()
    fv = predictor.feature_store.extract_features(payload)
    pred_result = predictor.predict(raw_txn=payload, feature_vector=fv)

    # 4. PROFILE UPDATES
    profile_mgr = ProfileManager.get_instance()
    is_fraud = pred_result.business_decision in ["DECLINE", "REVIEW"] or pred_result.decision in ["FRAUD", "SUSPICIOUS"]
    
    cust = profile_mgr.get_or_create_customer(fv.account_id, payload.get("user_id", "usr_unknown"))
    cust.update_with_transaction(
        amount=float(payload.get("amount", 0.0)),
        device_id=payload.get("device_id", "dev_unknown"),
        country=payload.get("country", "IN"),
        is_fraud=is_fraud
    )

    merch = profile_mgr.get_or_create_merchant(
        merchant_id=payload.get("merchant_id", "merch_unknown"),
        category=payload.get("merchant_category", "retail")
    )
    merch.update_with_transaction(amount=float(payload.get("amount", 0.0)), is_fraud=is_fraud)

    # 5. PERSIST TRANSACTION
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

    # 6. PERSIST FEATURES
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

    # 7. PERSIST PREDICTION
    pred_record = PredictionRecord(
        transaction_id=txn_id,
        correlation_id=payload.get("correlation_id"),
        timestamp=payload.get("timestamp"),
        account_id=payload.get("account_id"),
        amount=float(payload.get("amount", 0.0)),
        merchant_id=payload.get("merchant_id"),
        country=payload.get("country", "IN"),
        fraud_probability=pred_result.fraud_probability,
        risk_score=pred_result.risk_score,
        decision=pred_result.decision,
        business_decision=pred_result.business_decision or "APPROVE",
        model_version=pred_result.model_version,
        latency_ms=pred_result.latency_ms,
        reason_codes=pred_result.reason_codes,
        feature_contributions=pred_result.feature_contributions
    )
    db.add(pred_record)

    # 8. CREATE ALERT IF HIGH RISK OR SUSPICIOUS
    if is_fraud or pred_result.risk_score >= 45.0:
        severity = "CRITICAL" if pred_result.risk_score >= 80.0 else ("HIGH" if pred_result.risk_score >= 60.0 else "MEDIUM")
        alert = FraudAlertRecord(
            alert_id=f"alt_{txn_id[-8:]}",
            transaction_id=txn_id,
            account_id=payload.get("account_id"),
            amount=float(payload.get("amount", 0.0)),
            severity=severity,
            risk_score=pred_result.risk_score,
            fraud_probability=pred_result.fraud_probability,
            reason_codes=pred_result.reason_codes,
            status="NEW"
        )
        db.add(alert)

    await db.commit()
    return pred_result
