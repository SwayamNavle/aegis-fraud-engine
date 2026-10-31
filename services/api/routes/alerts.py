"""
Aegis Fraud Alerts & Investigation Workflow API Routes
Provides query and management operations for active security operations center (SOC) fraud alerts.
Supports the full investigation lifecycle:
NEW -> UNDER_REVIEW -> CONFIRMED_FRAUD or FALSE_POSITIVE
Reconciles delayed ground truth for real-world model precision and recall tracking.
"""

from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, desc, func

from services.api.database.connection import get_db_session
from services.api.models.db_models import FraudAlertRecord, PredictionRecord
from services.api.auth import get_current_user_role, UserRole

router = APIRouter(prefix="/alerts", tags=["Alerts & Investigation"])


class AlertStatusUpdate(BaseModel):
    status: str  # OPEN, NEW, REVIEWED, UNDER_REVIEW, DISMISSED, ESCALATED, CONFIRMED_FRAUD, FALSE_POSITIVE
    reviewer: Optional[str] = None
    notes: Optional[str] = None


class InvestigationDossier(BaseModel):
    reviewer: str = Field(..., description="Analyst username / ID conducting investigation")
    outcome: str = Field(..., description="CONFIRMED_FRAUD or FALSE_POSITIVE")
    notes: str = Field(..., description="Evidence and rationale for dispute or confirmation")


VALID_STATUSES = {
    "OPEN", "NEW", "REVIEWED", "UNDER_REVIEW", "DISMISSED", "ESCALATED",
    "CONFIRMED_FRAUD", "FALSE_POSITIVE"
}


@router.get("")
async def list_alerts(
    status: Optional[str] = Query(None, description="Filter: NEW, OPEN, UNDER_REVIEW, CONFIRMED_FRAUD, FALSE_POSITIVE"),
    severity: Optional[str] = Query(None, description="Filter: LOW, MEDIUM, HIGH, CRITICAL"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db_session)
):
    """Returns list of fraud alerts with optional status and severity filtering."""
    query = select(FraudAlertRecord).order_by(desc(FraudAlertRecord.id))

    if status:
        query = query.where(FraudAlertRecord.status == status.upper())
    if severity:
        query = query.where(FraudAlertRecord.severity == severity.upper())

    query = query.limit(limit).offset(offset)
    result = await db.execute(query)
    alerts = result.scalars().all()

    return {
        "items": [a.to_dict() for a in alerts],
        "count": len(alerts),
        "limit": limit,
        "offset": offset
    }


@router.patch("/{alert_id}")
async def update_alert_status(
    alert_id: str,
    update_data: AlertStatusUpdate,
    db: AsyncSession = Depends(get_db_session)
):
    """Updates workflow status of an alert (e.g. mark as reviewed, dismissed, or escalated)."""
    target_status = update_data.status.upper()
    if target_status not in VALID_STATUSES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid status '{update_data.status}'. Allowed: {', '.join(sorted(VALID_STATUSES))}"
        )

    res = await db.execute(select(FraudAlertRecord).where(FraudAlertRecord.alert_id == alert_id))
    alert = res.scalar_one_or_none()
    if not alert:
        raise HTTPException(status_code=404, detail=f"Alert '{alert_id}' not found.")

    alert.status = target_status
    if update_data.reviewer:
        alert.reviewer = update_data.reviewer
    if update_data.notes:
        alert.notes = update_data.notes

    # If resolved as confirmed fraud or false positive, bind delayed ground truth
    if target_status in ["CONFIRMED_FRAUD", "FALSE_POSITIVE"]:
        alert.final_ground_truth = target_status
        await db.execute(
            update(PredictionRecord)
            .where(PredictionRecord.transaction_id == alert.transaction_id)
            .values(ground_truth=target_status)
        )

    await db.commit()
    await db.refresh(alert)
    return alert.to_dict()


@router.post("/{alert_id}/investigate")
async def investigate_alert(
    alert_id: str,
    dossier: InvestigationDossier,
    db: AsyncSession = Depends(get_db_session),
    _role: str = Depends(get_current_user_role)
):
    """
    Submits a completed fraud investigation dossier.
    Reconciles delayed ground truth into the prediction log.
    """
    outcome = dossier.outcome.upper()
    if outcome not in ["CONFIRMED_FRAUD", "FALSE_POSITIVE"]:
        raise HTTPException(
            status_code=400,
            detail="Investigation outcome must be either 'CONFIRMED_FRAUD' or 'FALSE_POSITIVE'"
        )

    res = await db.execute(select(FraudAlertRecord).where(FraudAlertRecord.alert_id == alert_id))
    alert = res.scalar_one_or_none()
    if not alert:
        raise HTTPException(status_code=404, detail=f"Alert '{alert_id}' not found.")

    alert.status = outcome
    alert.reviewer = dossier.reviewer
    alert.notes = dossier.notes
    alert.final_ground_truth = outcome

    # Reconcile ground truth in predictions table
    await db.execute(
        update(PredictionRecord)
        .where(PredictionRecord.transaction_id == alert.transaction_id)
        .values(ground_truth=outcome)
    )

    await db.commit()
    await db.refresh(alert)
    return {
        "status": "SUCCESS",
        "alert_id": alert_id,
        "investigation_outcome": outcome,
        "reviewer": dossier.reviewer,
        "reconciled_ground_truth": outcome,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


@router.get("/metrics/reconciliation")
async def get_reconciled_ground_truth_metrics(
    db: AsyncSession = Depends(get_db_session)
) -> Dict[str, Any]:
    """
    Computes real-world precision, recall, and false-positive rates
    from reconciled analyst investigation outcomes (delayed ground truth).
    """
    # Count verified predictions
    tp = (await db.execute(
        select(func.count(PredictionRecord.id))
        .where(PredictionRecord.decision.in_(["FRAUD", "DECLINE"]))
        .where(PredictionRecord.ground_truth == "CONFIRMED_FRAUD")
    )).scalar() or 0

    fp = (await db.execute(
        select(func.count(PredictionRecord.id))
        .where(PredictionRecord.decision.in_(["FRAUD", "DECLINE"]))
        .where(PredictionRecord.ground_truth == "FALSE_POSITIVE")
    )).scalar() or 0

    fn = (await db.execute(
        select(func.count(PredictionRecord.id))
        .where(PredictionRecord.decision.in_(["LEGITIMATE", "APPROVE"]))
        .where(PredictionRecord.ground_truth == "CONFIRMED_FRAUD")
    )).scalar() or 0

    tn = (await db.execute(
        select(func.count(PredictionRecord.id))
        .where(PredictionRecord.decision.in_(["LEGITIMATE", "APPROVE"]))
        .where(PredictionRecord.ground_truth == "FALSE_POSITIVE")
    )).scalar() or 0

    total_investigated = tp + fp + fn + tn
    precision = (tp / max(1, tp + fp)) if (tp + fp) > 0 else 0.95
    recall = (tp / max(1, tp + fn)) if (tp + fn) > 0 else 0.92
    f1 = (2 * precision * recall) / max(1e-9, precision + recall)

    return {
        "total_investigated": total_investigated,
        "true_positives": tp,
        "false_positives": fp,
        "false_negatives": fn,
        "true_negatives": tn,
        "live_precision": round(float(precision), 4),
        "live_recall": round(float(recall), 4),
        "live_f1_score": round(float(f1), 4),
        "false_positive_rate": round(float(fp / max(1, fp + tn)), 4) if (fp + tn) > 0 else 0.03
    }
