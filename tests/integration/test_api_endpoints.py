"""
Integration tests for Aegis REST API endpoints.
"""

import pytest
from httpx import AsyncClient, ASGITransport
from services.api.main import app
from services.api.database.connection import init_db


@pytest.mark.asyncio
async def test_health_and_metrics_endpoints():
    await init_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Test /health
        res = await client.get("/health")
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "ONLINE"

        # Test /metrics
        metrics_res = await client.get("/metrics")
        assert metrics_res.status_code == 200
        assert "aegis_http_requests_total" in metrics_res.text


@pytest.mark.asyncio
async def test_stats_and_monitoring_endpoints():
    await init_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Test /stats
        stats_res = await client.get("/stats")
        assert stats_res.status_code == 200
        stats = stats_res.json()
        assert "total_transactions" in stats
        assert "fraud_detected" in stats

        # Test /stats/throughput
        tp_res = await client.get("/stats/throughput")
        assert tp_res.status_code == 200
        assert isinstance(tp_res.json(), list)

        # Test /monitoring/drift
        drift_res = await client.get("/monitoring/drift")
        assert drift_res.status_code == 200
        drift = drift_res.json()
        assert "features_monitored" in drift
        assert "feature_metrics" in drift

        # Test /system/status
        sys_res = await client.get("/system/status")
        assert sys_res.status_code == 200
        sys_data = sys_res.json()
        assert "services" in sys_data
        assert len(sys_data["services"]) >= 4


@pytest.mark.asyncio
async def test_alerts_query_and_patch():
    await init_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        alerts_res = await client.get("/alerts")
        assert alerts_res.status_code == 200
        data = alerts_res.json()
        assert "items" in data
