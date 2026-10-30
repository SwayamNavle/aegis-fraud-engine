"""
Aegis Fraud Alerts API Routes
Provides query and management operations for active security operations center (SOC) fraud alerts.
"""

from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from services.api.database.connection import get_db_session
from services.api.models.db_models import FraudAlertRecord

router = APIRouter(prefix="/alerts", tags=["Alerts"])


class AlertStatusUpdate(BaseModel):
    status: str  # OPEN, REVIEWED, DISMISSED, ESCALATED


@router.get("")
async def list_alerts(
    status: Optional[str] = Query(None, description="Filter: OPEN, REVIEWED, DISMISSED, ESCALATED"),
    severity: Optional[str] = Query(None, description="Filter: LOW, MEDIUM, HIGH, CRITICAL"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db_session)
):
    """Returns list of fraud alerts with optional filtering."""
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
    update: AlertStatusUpdate,
    db: AsyncSession = Depends(get_db_session)
):
    """Updates workflow status of an alert (e.g. mark as reviewed, dismissed, or escalated)."""
    valid_statuses = {"OPEN", "REVIEWED", "DISMISSED", "ESCALATED"}
    target_status = update.status.upper()
    if target_status not in valid_statuses:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid status '{update.status}'. Allowed: {', '.join(valid_statuses)}"
        )

    res = await db.execute(select(FraudAlertRecord).where(FraudAlertRecord.alert_id == alert_id))
    alert = res.scalar_one_or_none()
    if not alert:
        raise HTTPException(status_code=404, detail=f"Alert '{alert_id}' not found.")

    alert.status = target_status
    await db.commit()
    await db.refresh(alert)
    return alert.to_dict()
