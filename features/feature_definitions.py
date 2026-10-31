"""
Aegis Feature Definitions & Schema Registry
Single source of truth for all engineered features shared across:
- Offline batch training and model evaluation
- PySpark Structured Streaming sliding window jobs
- Online feature store & low-latency FastAPI inference
"""

from typing import List, Dict, Any

# Canonical feature ordering used across training and inference
FEATURE_NAMES: List[str] = [
    "transaction_count_1m",
    "transaction_count_5m",
    "transaction_amount_sum_5m",
    "transaction_amount_avg_5m",
    "transaction_amount_std_5m",
    "amount_z_score",
    "unique_merchants_10m",
    "unique_countries_30m",
    "unique_devices_30m",
    "international_transaction_count",
    "time_since_previous_transaction",
    "distance_from_previous_transaction",
    "geo_velocity_kmh",
    "device_change_flag",
    "country_change_flag",
    "velocity_score",
    "merchant_risk_score",
    "user_amount_deviation",
    "card_present",
    "is_international"
]

FEATURE_DEFINITIONS: List[Dict[str, Any]] = [
    {"name": name, "type": "float" if "score" in name or "amount" in name or "km" in name or "time" in name or "deviation" in name else "integer"}
    for name in FEATURE_NAMES
]

# Merchant risk categorization map [0.0 - 1.0]
MERCHANT_RISK_WEIGHTS: Dict[str, float] = {
    "crypto_exchange": 0.95,
    "online_gambling": 0.90,
    "offshore_gaming": 0.85,
    "luxury_watches": 0.80,
    "wire_remittance": 0.75,
    "department_store": 0.30,
    "electronics": 0.40,
    "entertainment": 0.25,
    "restaurants": 0.15,
    "pharmacy": 0.10,
    "fuel": 0.10,
    "grocery": 0.05,
    "utilities": 0.05,
}
DEFAULT_MERCHANT_RISK: float = 0.20
