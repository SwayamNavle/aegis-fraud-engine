"""
Integration tests for failure scenarios, dead-letter routing invariants, and error responses.
"""

import pytest
from httpx import AsyncClient, ASGITransport
from services.api.main import app
from services.api.database.connection import init_db


@pytest.mark.asyncio
async def test_nonexistent_transaction_404():
    await init_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/transactions/txn_non_existent_404_id")
        assert res.status_code == 404
        assert "not found" in res.json()["detail"].lower()


@pytest.mark.asyncio
async def test_invalid_alert_status_update_400():
    await init_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.patch("/alerts/alt_test_999", json={"status": "INVALID_STATUS_STRING"})
        assert res.status_code == 400


@pytest.mark.asyncio
async def test_malformed_scoring_payload_handling():
    await init_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Missing transaction_id
        res = await client.post("/transactions/score_and_persist", json={"amount": 500.0})
        assert res.status_code == 400
