"""
Aegis Online Feature Store
Maintains low-latency sliding window state per account with event-time semantics,
kinematics, and optional Redis integration for distributed feature caching.
"""

import math
import os
import json
import numpy as np
from collections import deque
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any

from features.feature_definitions import (
    FEATURE_NAMES, MERCHANT_RISK_WEIGHTS, DEFAULT_MERCHANT_RISK
)
from features.offline_features import haversine_distance_km
from streaming.schemas.transaction_schema import FeatureVector


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
    Online feature store maintaining stateful sliding window state per account.
    Used during streaming evaluation, real-time API scoring, and local fallback streaming.
    Can be backed by Redis in clustered setups.
    """
    def __init__(self, redis_client: Optional[Any] = None):
        self.accounts: Dict[str, AccountState] = {}
        self.redis = redis_client
        if self.redis is None and os.getenv("ENABLE_REDIS", "false").lower() == "true":
            try:
                import redis
                redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
                self.redis = redis.from_url(redis_url, decode_responses=True)
            except Exception:
                self.redis = None

    def _parse_timestamp(self, ts_val: Any) -> float:
        if isinstance(ts_val, (int, float)):
            return float(ts_val)
        if isinstance(ts_val, str):
            clean_ts = ts_val.replace("Z", "+00:00")
            dt = datetime.fromisoformat(clean_ts)
            return dt.timestamp()
        if isinstance(ts_val, datetime):
            return ts_val.timestamp()
        return datetime.now(timezone.utc).timestamp()

    def extract_features(self, txn: Dict[str, Any]) -> FeatureVector:
        """
        Calculates all 20 features for a transaction against the current sliding window state.
        Updates internal sliding window state with the new event.
        """
        acc_id = txn["account_id"]
        txn_id = txn["transaction_id"]
        amount = float(txn["amount"])
        curr_ts = self._parse_timestamp(txn["timestamp"])
        curr_lat = float(txn.get("latitude", 0.0))
        curr_lon = float(txn.get("longitude", 0.0))
        device_id = txn.get("device_id", "dev_unknown")
        country = txn.get("country", "IN")
        merchant_id = txn.get("merchant_id", "merch_unknown")
        merch_cat = txn.get("merchant_category", "retail")
        is_intl = 1 if txn.get("is_international", False) else 0

        if acc_id not in self.accounts:
            self.accounts[acc_id] = AccountState(acc_id)
        state = self.accounts[acc_id]

        # -------------------------------------------------------------
        # 1. KINEMATICS RELATIVE TO PREVIOUS TRANSACTION
        # -------------------------------------------------------------
        if state.events:
            prev_event = state.events[-1]
            time_since_prev = max(0.1, curr_ts - prev_event["ts"])
            distance_from_prev = haversine_distance_km(
                prev_event["lat"], prev_event["lon"], curr_lat, curr_lon
            )
            geo_velocity_kmh = (distance_from_prev / time_since_prev) * 3600.0
        else:
            time_since_prev = 86400.0  # default 24h for fresh accounts
            distance_from_prev = 0.0
            geo_velocity_kmh = 0.0

        # -------------------------------------------------------------
        # 2. SLIDING WINDOW AGGREGATIONS (1m, 5m, 10m, 30m)
        # -------------------------------------------------------------
        c_1m = 0
        c_5m = 0
        sum_5m = 0.0
        max_5m = 0.0
        amounts_5m = []

        merchants_10m = set()
        countries_30m = set()
        devices_30m = set()
        intl_count_30m = 0

        cutoff_1m = curr_ts - 60
        cutoff_5m = curr_ts - 300
        cutoff_10m = curr_ts - 600
        cutoff_30m = curr_ts - 1800

        for ev in reversed(state.events):
            t = ev["ts"]
            if t < cutoff_30m:
                break
            # 30m window
            countries_30m.add(ev["country"])
            devices_30m.add(ev["device_id"])
            if ev["is_intl"]:
                intl_count_30m += 1

            # 10m window
            if t >= cutoff_10m:
                merchants_10m.add(ev["merchant_id"])

            # 5m window
            if t >= cutoff_5m:
                c_5m += 1
                sum_5m += ev["amount"]
                max_5m = max(max_5m, ev["amount"])
                amounts_5m.append(ev["amount"])

            # 1m window
            if t >= cutoff_1m:
                c_1m += 1

        # Current event included in aggregations
        c_1m += 1
        c_5m += 1
        sum_5m += amount
        max_5m = max(max_5m, amount)
        amounts_5m.append(amount)
        merchants_10m.add(merchant_id)
        countries_30m.add(country)
        devices_30m.add(device_id)
        if is_intl:
            intl_count_30m += 1

        avg_5m = sum_5m / max(1, c_5m)
        std_5m = float(np.std(amounts_5m)) if len(amounts_5m) > 1 else 10.0
        if std_5m < 1.0:
            std_5m = 10.0

        # -------------------------------------------------------------
        # 3. BEHAVIORAL DEVIATION & CONTEXT SCORES
        # -------------------------------------------------------------
        amount_z_score = (amount - avg_5m) / std_5m

        # Historical baseline comparison
        hist_avg = (sum(state.historical_amounts) / len(state.historical_amounts)) if state.historical_amounts else amount
        user_amount_deviation = amount / max(10.0, hist_avg)

        # Velocity score (frequency index)
        velocity_score = (c_1m * 2.0) + (c_5m * 0.4)

        # Context flags
        device_change_flag = 1 if state.primary_device_id and device_id != state.primary_device_id else 0
        country_change_flag = 1 if state.primary_country and country != state.primary_country else 0
        merchant_risk_score = MERCHANT_RISK_WEIGHTS.get(merch_cat, DEFAULT_MERCHANT_RISK)
        card_present = 1 if txn.get("card_present", False) else 0

        # Update account state
        state.add_event(curr_ts, amount, merchant_id, country, device_id, curr_lat, curr_lon, bool(is_intl))

        return FeatureVector(
            transaction_id=txn_id,
            account_id=acc_id,
            timestamp=txn.get("timestamp", ""),
            transaction_count_1m=c_1m,
            transaction_count_5m=c_5m,
            transaction_amount_sum_5m=round(sum_5m, 2),
            transaction_amount_avg_5m=round(avg_5m, 2),
            transaction_amount_std_5m=round(std_5m, 2),
            max_transaction_amount_5m=round(max_5m, 2),
            unique_merchants_10m=len(merchants_10m),
            unique_countries_30m=len(countries_30m),
            unique_devices_30m=len(devices_30m),
            international_transaction_count=intl_count_30m,
            time_since_previous_transaction=round(time_since_prev, 2),
            distance_from_previous_transaction=round(distance_from_prev, 2),
            geo_velocity_kmh=round(geo_velocity_kmh, 2),
            amount_z_score=round(amount_z_score, 4),
            user_amount_deviation=round(user_amount_deviation, 4),
            velocity_score=round(velocity_score, 2),
            merchant_risk_score=round(merchant_risk_score, 2),
            device_change_flag=device_change_flag,
            country_change_flag=country_change_flag,
            card_present=card_present,
            is_international=is_intl
        )
