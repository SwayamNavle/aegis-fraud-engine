"""
Unit tests for Aegis sliding window feature engineering.
"""

import pytest
from datetime import datetime, timezone, timedelta
from ml.training.feature_engineering import OnlineFeatureStore, haversine_distance_km


def test_haversine_distance():
    # Mumbai to London is approx 7,190 km
    mumbai_lat, mumbai_lon = 19.0760, 72.8777
    london_lat, london_lon = 51.5074, -0.1278
    dist = haversine_distance_km(mumbai_lat, mumbai_lon, london_lat, london_lon)
    assert 7100 < dist < 7300, f"Expected approx 7200 km, got {dist}"


def test_sliding_window_counts():
    store = OnlineFeatureStore()
    base_time = datetime(2026, 10, 30, 12, 0, 0, tzinfo=timezone.utc)
    
    # Event 1
    txn1 = {
        "transaction_id": "txn_test_1",
        "account_id": "acc_window_test",
        "timestamp": base_time.isoformat(),
        "amount": 1000.0,
        "latitude": 19.0760,
        "longitude": 72.8777,
        "country": "IN",
        "merchant_id": "merch_1",
        "merchant_category": "grocery",
        "device_id": "dev_1"
    }
    fv1 = store.extract_features(txn1)
    assert fv1.transaction_count_1m == 1
    assert fv1.transaction_count_5m == 1

    # Event 2: 30 seconds later (within 1m window)
    t2 = base_time + timedelta(seconds=30)
    txn2 = {
        "transaction_id": "txn_test_2",
        "account_id": "acc_window_test",
        "timestamp": t2.isoformat(),
        "amount": 1500.0,
        "latitude": 19.0760,
        "longitude": 72.8777,
        "country": "IN",
        "merchant_id": "merch_2",
        "merchant_category": "grocery",
        "device_id": "dev_1"
    }
    fv2 = store.extract_features(txn2)
    assert fv2.transaction_count_1m == 2
    assert fv2.transaction_count_5m == 2
    assert fv2.transaction_amount_sum_5m == 2500.0
    assert fv2.transaction_amount_avg_5m == 1250.0
    assert fv2.unique_merchants_10m == 2


def test_geo_velocity_calculation():
    store = OnlineFeatureStore()
    base_time = datetime(2026, 10, 30, 12, 0, 0, tzinfo=timezone.utc)

    # Event in Mumbai
    txn1 = {
        "transaction_id": "txn_geo_1",
        "account_id": "acc_geo_test",
        "timestamp": base_time.isoformat(),
        "amount": 500.0,
        "latitude": 19.0760,
        "longitude": 72.8777,
        "country": "IN",
        "merchant_id": "m1",
        "device_id": "d1"
    }
    store.extract_features(txn1)

    # Event 2 minutes later in London
    txn2 = {
        "transaction_id": "txn_geo_2",
        "account_id": "acc_geo_test",
        "timestamp": (base_time + timedelta(minutes=2)).isoformat(),
        "amount": 25000.0,
        "latitude": 51.5074,
        "longitude": -0.1278,
        "country": "GB",
        "merchant_id": "m2",
        "device_id": "d2"
    }
    fv2 = store.extract_features(txn2)
    # Velocity should be thousands of km/h
    assert fv2.geo_velocity_kmh > 100000.0
    assert fv2.country_change_flag == 1
    assert fv2.device_change_flag == 1
