"""
Aegis Unified Feature Store Package
Exports feature definitions, offline feature pipeline, and online feature store.
"""

from features.feature_definitions import (
    FEATURE_DEFINITIONS,
    FEATURE_NAMES,
    MERCHANT_RISK_WEIGHTS,
    DEFAULT_MERCHANT_RISK
)
from features.offline_features import (
    haversine_distance_km,
    engineer_features_batch
)
from features.online_features import (
    OnlineFeatureStore,
    AccountState
)

__all__ = [
    "FEATURE_DEFINITIONS",
    "FEATURE_NAMES",
    "MERCHANT_RISK_WEIGHTS",
    "DEFAULT_MERCHANT_RISK",
    "haversine_distance_km",
    "engineer_features_batch",
    "OnlineFeatureStore",
    "AccountState"
]

