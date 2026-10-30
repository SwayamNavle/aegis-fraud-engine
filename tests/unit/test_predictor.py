"""
Unit tests for Aegis FraudPredictor inference, reason codes, and risk calibration.
"""

import pytest
from services.scoring.predictor import FraudPredictor
from streaming.schemas.transaction_schema import FeatureVector


def test_predictor_deterministic_reason_codes():
    predictor = FraudPredictor()

    fv_anomaly = FeatureVector(
        transaction_id="txn_test_reason",
        account_id="acc_reason",
        timestamp="2026-10-30T12:00:00Z",
        transaction_count_1m=5,
        velocity_score=9.5,
        geo_velocity_kmh=1200.0,
        amount_z_score=4.5,
        merchant_risk_score=0.90,
        device_change_flag=1,
        country_change_flag=1
    )

    codes = predictor.derive_reason_codes(fv_anomaly, prob=0.95)
    assert "IMPOSSIBLE_TRAVEL" in codes
    assert "UNUSUAL_AMOUNT" in codes
    assert "HIGH_TRANSACTION_VELOCITY" in codes
    assert "UNUSUAL_MERCHANT" in codes
    assert "NEW_DEVICE" in codes


def test_predictor_scoring_calibration():
    predictor = FraudPredictor()

    # Extreme fraud payload
    fraud_txn = {
        "transaction_id": "txn_unit_fraud",
        "account_id": "acc_fraud_99",
        "timestamp": "2026-10-30T12:00:00Z",
        "amount": 95000.0,
        "latitude": 51.5074,
        "longitude": -0.1278,
        "country": "GB",
        "city": "London",
        "merchant_id": "merch_crypto_9",
        "merchant_category": "crypto_exchange",
        "device_id": "dev_emulator",
        "device_type": "Android_Emulator",
        "is_international": True
    }
    res = predictor.predict(raw_txn=fraud_txn)
    assert res.fraud_probability > 0.50
    assert res.risk_score > 50.0
    assert res.decision in ["FRAUD", "SUSPICIOUS"]
    assert res.latency_ms > 0.0
