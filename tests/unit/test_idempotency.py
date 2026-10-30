"""
Unit tests for Aegis idempotent event processing and duplicate event replay protection.
"""

import pytest
import asyncio
from services.api.database.connection import init_db, get_engine, async_sessionmaker, AsyncSession
from services.api.models.db_models import PredictionRecord
from services.api.routes.transactions import score_and_persist
from sqlalchemy import select, func


@pytest.mark.asyncio
async def test_idempotent_duplicate_processing():
    await init_db()
    engine = await get_engine()
    session_factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

    test_payload = {
        "transaction_id": "txn_idempotency_verify_999",
        "timestamp": "2026-10-30T14:30:00Z",
        "user_id": "usr_idem_1",
        "account_id": "acc_idem_1",
        "merchant_id": "merch_grocery_10",
        "merchant_category": "grocery",
        "amount": 1250.0,
        "currency": "INR",
        "country": "IN",
        "city": "Mumbai",
        "latitude": 19.0760,
        "longitude": 72.8777,
        "device_id": "dev_idem_1",
        "device_type": "iPhone",
        "ip_address": "103.21.244.2",
        "payment_method": "upi",
        "card_present": True,
        "is_international": False
    }

    # Step 1: First arrival
    async with session_factory() as session:
        result1 = await score_and_persist(test_payload, db=session)
        assert result1.transaction_id == "txn_idempotency_verify_999"
        first_prob = result1.fraud_probability

    # Step 2: Consumer crashes and replays exact same event
    async with session_factory() as session:
        result2 = await score_and_persist(test_payload, db=session)
        assert result2.transaction_id == "txn_idempotency_verify_999"
        # Must return identical existing score
        assert result2.fraud_probability == first_prob

    # Step 3: Verify strictly 1 row in predictions table (no duplicate insertion)
    async with session_factory() as session:
        count = (await session.execute(
            select(func.count(PredictionRecord.id)).where(
                PredictionRecord.transaction_id == "txn_idempotency_verify_999"
            )
        )).scalar()
        assert count == 1, f"Expected exactly 1 prediction record, found {count}"
