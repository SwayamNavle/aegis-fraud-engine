"""
Aegis Offline Feature Pipeline
Extracts features across historical transaction batches for model training and offline validation.
Chronological ordering is strictly preserved to prevent data leakage.
"""

import math
import numpy as np
import pandas as pd
from typing import Tuple, List, Dict, Any

from features.feature_definitions import (
    FEATURE_NAMES, MERCHANT_RISK_WEIGHTS, DEFAULT_MERCHANT_RISK
)


def haversine_distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculates great-circle distance between two GPS coordinates in kilometers."""
    if (lat1 == 0.0 and lon1 == 0.0) or (lat2 == 0.0 and lon2 == 0.0):
        return 0.0
    r = 6371.0
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = (math.sin(delta_phi / 2.0) ** 2 +
         math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0) ** 2)
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(max(1e-9, 1.0 - a)))
    return r * c


def engineer_features_batch(df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.Series]:
    """
    Simulates chronological sliding-window stream feature generation over a batch dataset.
    Returns:
        X (pd.DataFrame): 20 engineered feature columns
        y (pd.Series): Binary fraud ground-truth label
    """
    from features.online_features import OnlineFeatureStore

    print(f"[Aegis FeatureEng] Processing batch of {len(df):,} transactions chronologically...")
    store = OnlineFeatureStore()
    
    # Sort strictly by timestamp
    df_sorted = df.copy()
    if not pd.api.types.is_datetime64_any_dtype(df_sorted["timestamp"]):
        df_sorted["timestamp_dt"] = pd.to_datetime(df_sorted["timestamp"])
        df_sorted = df_sorted.sort_values("timestamp_dt").reset_index(drop=True)
    else:
        df_sorted = df_sorted.sort_values("timestamp").reset_index(drop=True)

    feature_rows: List[List[float]] = []
    
    # Stream through records chronologically
    records = df_sorted.to_dict(orient="records")
    for r in records:
        fv = store.extract_features(r)
        feature_rows.append(fv.to_feature_list())

    X = pd.DataFrame(feature_rows, columns=FEATURE_NAMES)
    y = df_sorted["label"].astype(int)
    
    print(f"[Aegis FeatureEng] Engineered {len(FEATURE_NAMES)} features across {len(X):,} rows.")
    return X, y
