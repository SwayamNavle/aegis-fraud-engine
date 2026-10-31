"""
Aegis Customer Intelligence & Behavioral Profiling Routes
Exposes customer historical spend curves, device graphs, and risk scores.
"""

from typing import Dict, Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from services.api.database.connection import get_db_session
from services.api.models.db_models import CustomerProfileRecord
from risk_engine.profiler import ProfileManager

router = APIRouter(prefix="/customers", tags=["Customer Intelligence"])


@router.get("")
async def list_customer_profiles(
    min_risk: Optional[float] = Query(None, ge=0.0, le=100.0),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db_session)
) -> Dict[str, Any]:
    """Returns paginated customer behavioral risk profiles."""
    query = select(CustomerProfileRecord).order_by(desc(CustomerProfileRecord.customer_risk_score))
    if min_risk is not None:
        query = query.where(CustomerProfileRecord.customer_risk_score >= min_risk)

    query = query.limit(limit).offset(offset)
    res = await db.execute(query)
    records = res.scalars().all()

    # If DB table empty, pull from active in-memory profile manager
    if not records:
        manager = ProfileManager.get_instance()
        items = [p.to_dict() for p in list(manager.customers.values())[:limit]]
        return {"items": items, "count": len(items), "limit": limit, "offset": offset}

    return {
        "items": [r.to_dict() for r in records],
        "count": len(records),
        "limit": limit,
        "offset": offset
    }


@router.get("/{account_id}")
async def get_customer_profile(
    account_id: str,
    db: AsyncSession = Depends(get_db_session)
) -> Dict[str, Any]:
    """Returns detailed customer behavioral dossier for fraud investigation."""
    res = await db.execute(select(CustomerProfileRecord).where(CustomerProfileRecord.account_id == account_id))
    record = res.scalar_one_or_none()
    if record:
        return record.to_dict()

    manager = ProfileManager.get_instance()
    if account_id in manager.customers:
        return manager.customers[account_id].to_dict()

    raise HTTPException(status_code=404, detail=f"Customer account '{account_id}' profile not found.")

