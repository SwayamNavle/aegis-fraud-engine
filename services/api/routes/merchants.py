"""
Aegis Merchant Risk Profiling Routes
Exposes merchant transaction volumes, fraud rates, and category risk indices.
"""

from typing import Dict, Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from services.api.database.connection import get_db_session
from services.api.models.db_models import MerchantProfileRecord
from risk_engine.profiler import ProfileManager

router = APIRouter(prefix="/merchants", tags=["Merchant Profiling"])


@router.get("")
async def list_merchant_profiles(
    min_fraud_rate: Optional[float] = Query(None, ge=0.0, le=100.0),
    category: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db_session)
) -> Dict[str, Any]:
    """Returns paginated merchant risk rankings."""
    query = select(MerchantProfileRecord).order_by(desc(MerchantProfileRecord.merchant_risk_score))
    if min_fraud_rate is not None:
        query = query.where(MerchantProfileRecord.fraud_rate >= min_fraud_rate)
    if category:
        query = query.where(MerchantProfileRecord.category == category.lower())

    query = query.limit(limit).offset(offset)
    res = await db.execute(query)
    records = res.scalars().all()

    # If DB table empty, pull from active profile manager
    if not records:
        manager = ProfileManager.get_instance()
        items = [p.to_dict() for p in list(manager.merchants.values())[:limit]]
        return {"items": items, "count": len(items), "limit": limit, "offset": offset}

    return {
        "items": [r.to_dict() for r in records],
        "count": len(records),
        "limit": limit,
        "offset": offset
    }


@router.get("/{merchant_id}")
async def get_merchant_profile(
    merchant_id: str,
    db: AsyncSession = Depends(get_db_session)
) -> Dict[str, Any]:
    """Returns detailed merchant risk dossier and fraud history."""
    res = await db.execute(select(MerchantProfileRecord).where(MerchantProfileRecord.merchant_id == merchant_id))
    record = res.scalar_one_or_none()
    if record:
        return record.to_dict()

    manager = ProfileManager.get_instance()
    if merchant_id in manager.merchants:
        return manager.merchants[merchant_id].to_dict()

    raise HTTPException(status_code=404, detail=f"Merchant '{merchant_id}' profile not found.")

