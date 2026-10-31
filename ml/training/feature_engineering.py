"""
Aegis Unified Feature Engineering Engine
Re-exports from features/ module for backward compatibility across existing training,
streaming, and scoring pipelines.
"""

from features import (
    FEATURE_DEFINITIONS,
    FEATURE_NAMES,
    MERCHANT_RISK_WEIGHTS,
    DEFAULT_MERCHANT_RISK,
    haversine_distance_km,
    engineer_features_batch,
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
