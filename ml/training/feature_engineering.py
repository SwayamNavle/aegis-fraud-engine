"""
Aegis Unified Feature Engineering Engine
Shared feature calculations across:
1. Offline Batch Training & Evaluation (Pandas / NumPy / PySpark)
2. Streaming Inference (PySpark Structured Streaming & Online Feature Store)
3. Microservice Scoring (FastAPI inference)

This ensures ZERO training-serving skew.
"""

import math
import numpy as np
import pandas as pd
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Tuple
from collections import deque

from streaming.schemas.transaction_schema import FeatureVector, FEATURE_NAMES

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
DEFAULT_MERCHANT_RISK = 0.20


def haversine_distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculates great-circle distance between two GPS coordinates in kilometers."""
    if lat1 == 0.0 and lon1 == 0.0:
        return 0.0
    r = 6371.0
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = (math.sin(delta_phi / 2.0) ** 2 +
         math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0) ** 2)
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return r * c


class AccountState:
    """Sliding-window state accumulator for a single account."""
    def __init__(self, account_id: str):
        self.account_id = account_id
        # sliding windows stored as deque of (timestamp_epoch, amount, merchant_id, country, device_id, lat, lon)
        self.events: deque = deque()
        self.primary_device_id: Optional[str] = None
        self.primary_country: Optional[str] = None
        self.historical_amounts: List[float] = []

    def add_event(self, ts_epoch: float, amount: float, merchant_id: str,
                  country: str, device_id: str, lat: float, lon: float, is_intl: bool):
        self.events.append({
            "ts": ts_epoch,
            "amount": amount,
            "merchant_id": merchant_id,
            "country": country,
            "device_id": device_id,
            "lat": lat,
            "lon": lon,
            "is_intl": is_intl
        })
        self.historical_amounts.append(amount)
        if len(self.historical_amounts) > 500:
            self.historical_amounts.pop(0)

        if self.primary_device_id is None:
            self.primary_device_id = device_id
        if self.primary_country is None:
            self.primary_country = country

        # Prune events older than 35 minutes to bound memory
        cutoff = ts_epoch - (35 * 60)
        while self.events and self.events[0]["ts"] < cutoff:
            self.events.popleft()


class OnlineFeatureStore:
    """
    In-memory stateful feature store maintaining sliding windows per account.
    Used during streaming evaluation, real-time API scoring, and local fallback streaming.
    Can be backed by Redis in clustered setups.
    """
    def __init__(self):
        self.accounts: Dict[str, AccountState] = {}

    def extract_features(self, txn: Dict[str, Any]) -> FeatureVector:
        acc_id = txn["account_id"]
        if acc_id not in self.accounts:
            self.accounts[acc_id] = AccountState(acc_id)

        state = self.accounts[acc_id]

        # Parse timestamp to epoch seconds
        raw_ts = txn["timestamp"]
        if isinstance(raw_ts, str):
            # Parse ISO timestamp
            dt = datetime.fromisoformat(raw_ts.replace("Z", "+00:00"))
            ts_epoch = dt.timestamp()
        else:
            ts_epoch = float(raw_ts)

        amount = float(txn.get("amount", 0.0))
        lat = float(txn.get("latitude", 0.0))
        lon = float(txn.get("longitude", 0.0))
        country = txn.get("country", "IN")
        device_id = txn.get("device_id", f"dev_{acc_id[-4:]}")
        cat = txn.get("merchant_category", "retail")
        is_intl = bool(txn.get("is_international", False))
        card_present = bool(txn.get("card_present", False))

        # Sliding window lookbacks relative to current ts_epoch
        w1m_cutoff = ts_epoch - 60.0
        w5m_cutoff = ts_epoch - 300.0
        w10m_cutoff = ts_epoch - 600.0
        w30m_cutoff = ts_epoch - 1800.0

        # Preceding events in window (excluding the current event about to be recorded)
        ev_1m = [e for e in state.events if e["ts"] >= w1m_cutoff]
        ev_5m = [e for e in state.events if e["ts"] >= w5m_cutoff]
        ev_10m = [e for e in state.events if e["ts"] >= w10m_cutoff]
        ev_30m = [e for e in state.events if e["ts"] >= w30m_cutoff]

        # 1. Windowed Counts
        count_1m = len(ev_1m) + 1  # include current
        count_5m = len(ev_5m) + 1

        # 2. Windowed Amount Aggregations (5m)
        amounts_5m = [e["amount"] for e in ev_5m] + [amount]
        amt_sum_5m = float(np.sum(amounts_5m))
        amt_avg_5m = float(np.mean(amounts_5m))
        amt_std_5m = float(np.std(amounts_5m)) if len(amounts_5m) > 1 else 0.0
        max_amt_5m = float(np.max(amounts_5m))

        # 3. Cardinality features
        unique_merchants_10m = len(set([e["merchant_id"] for e in ev_10m] + [txn["merchant_id"]]))
        unique_countries_30m = len(set([e["country"] for e in ev_30m] + [country]))
        unique_devices_30m = len(set([e["device_id"] for e in ev_30m] + [device_id]))
        intl_count = sum(1 for e in ev_30m if e["is_intl"]) + (1 if is_intl else 0)

        # 4. Kinematics (distance and speed from previous event)
        if state.events:
            last_ev = state.events[-1]
            time_since_prev = max(1.0, ts_epoch - last_ev["ts"])
            dist_prev = haversine_distance_km(last_ev["lat"], last_ev["lon"], lat, lon)
            hours_elapsed = time_since_prev / 3600.0
            geo_velocity_kmh = dist_prev / max(0.0001, hours_elapsed)
        else:
            time_since_prev = 3600.0
            dist_prev = 0.0
            geo_velocity_kmh = 0.0

        # 5. Deviation & Risk Scores
        hist_amounts = state.historical_amounts if state.historical_amounts else [amount]
        hist_mean = float(np.mean(hist_amounts))
        hist_std = float(np.std(hist_amounts)) if len(hist_amounts) > 1 else 100.0
        hist_std = max(1.0, hist_std)
        amount_z_score = (amount - hist_mean) / hist_std

        user_amount_deviation = amount / max(1.0, amt_avg_5m)
        velocity_score = (count_1m * 3.0) + (count_5m * 1.0)
        merchant_risk = MERCHANT_RISK_WEIGHTS.get(cat, DEFAULT_MERCHANT_RISK)

        # 6. Categorical Flags
        device_change = 1 if (state.primary_device_id and state.primary_device_id != device_id) else 0
        country_change = 1 if (state.primary_country and state.primary_country != country) else 0

        # Record event in state
        state.add_event(ts_epoch, amount, txn["merchant_id"], country, device_id, lat, lon, is_intl)

        return FeatureVector(
            transaction_id=txn["transaction_id"],
            account_id=acc_id,
            timestamp=txn["timestamp"],
            transaction_count_1m=count_1m,
            transaction_count_5m=count_5m,
            transaction_amount_sum_5m=round(amt_sum_5m, 2),
            transaction_amount_avg_5m=round(amt_avg_5m, 2),
            transaction_amount_std_5m=round(amt_std_5m, 2),
            max_transaction_amount_5m=round(max_amt_5m, 2),
            unique_merchants_10m=unique_merchants_10m,
            unique_countries_30m=unique_countries_30m,
            unique_devices_30m=unique_devices_30m,
            international_transaction_count=intl_count,
            time_since_previous_transaction=round(time_since_prev, 2),
            distance_from_previous_transaction=round(dist_prev, 2),
            geo_velocity_kmh=round(geo_velocity_kmh, 2),
            amount_z_score=round(amount_z_score, 4),
            user_amount_deviation=round(user_amount_deviation, 4),
            velocity_score=round(velocity_score, 2),
            merchant_risk_score=round(merchant_risk, 4),
            device_change_flag=device_change,
            country_change_flag=country_change,
            card_present=1 if card_present else 0,
            is_international=1 if is_intl else 0
        )


def engineer_features_batch(df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.Series]:
    """
    Computes identical feature vectors for a historical DataFrame (for training/evaluation).
    Iterates chronologically by account to calculate genuine rolling window features without lookahead.
    """
    print(f"[Aegis FeatureEng] Processing batch of {len(df):,} transactions chronologically...")
    
    # Sort chronologically to guarantee no future data leakage
    df = df.copy()
    df["dt"] = pd.to_datetime(df["timestamp"])
    df = df.sort_values("dt").reset_index(drop=True)

    store = OnlineFeatureStore()
    feature_rows = []

    for _, row in df.iterrows():
        txn_dict = row.to_dict()
        fv = store.extract_features(txn_dict)
        feature_rows.append(fv.to_feature_list())

    X = pd.DataFrame(feature_rows, columns=FEATURE_NAMES)
    y = df["label"] if "label" in df.columns else None
    
    print(f"[Aegis FeatureEng] Engineered {X.shape[1]} features across {len(X):,} rows.")
    return X, y
