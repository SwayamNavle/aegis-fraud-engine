"""
Aegis Fraud Predictor & Reason Code Engine
Calculates:
- Probability of fraud from XGBoost classifier
- Calibrated 0-100 risk score
- Deterministic explainability reason codes
- Top feature contributions
"""

import time
import numpy as np
import pandas as pd
from typing import Dict, Any, List, Optional, Tuple

from services.scoring.model_loader import ModelRegistry
from streaming.schemas.transaction_schema import FeatureVector, PredictionResult, FEATURE_NAMES
from ml.training.feature_engineering import OnlineFeatureStore


class FraudPredictor:
    def __init__(self):
        self.registry = ModelRegistry.get_instance()
        self.model = self.registry.model
        self.model_version = self.registry.model_version
        self.fraud_threshold = self.registry.optimal_threshold
        self.medium_risk_threshold = self.registry.medium_risk_threshold
        self.feature_store = OnlineFeatureStore()

    def derive_reason_codes(self, fv: FeatureVector, prob: float) -> List[str]:
        """
        Deterministic reason code generation based on feature kinematics & thresholds.
        Provides business-understandable explanations for why a transaction was flagged.
        """
        codes = []
        if fv.geo_velocity_kmh >= 600.0:
            codes.append("IMPOSSIBLE_TRAVEL")
        if fv.amount_z_score >= 2.5 or fv.user_amount_deviation >= 4.0:
            codes.append("UNUSUAL_AMOUNT")
        if fv.transaction_count_1m >= 4 or fv.velocity_score >= 8.0:
            codes.append("HIGH_TRANSACTION_VELOCITY")
        if fv.merchant_risk_score >= 0.70:
            codes.append("UNUSUAL_MERCHANT")
        if fv.device_change_flag == 1:
            codes.append("NEW_DEVICE")
        if fv.country_change_flag == 1:
            codes.append("NEW_COUNTRY")
        if fv.is_international == 1 and fv.international_transaction_count >= 2:
            codes.append("INTERNATIONAL_SPIKE")
        if fv.transaction_amount_sum_5m >= 50000.0:
            codes.append("BURST_AMOUNT_EXCEEDED")

        if prob >= self.fraud_threshold and not codes:
            codes.append("STATISTICAL_ANOMALY")
        return codes

    def compute_feature_contributions(self, feature_values: List[float]) -> Dict[str, float]:
        """
        Calculates local feature contributions relative to model weights.
        Returns top features driving the current prediction.
        """
        importances = self.model.feature_importances_ if self.model else [1.0 / len(FEATURE_NAMES)] * len(FEATURE_NAMES)
        contributions = {}
        for name, val, imp in zip(FEATURE_NAMES, feature_values, importances):
            # Scale contribution by importance weight and standardized magnitude
            norm_val = min(10.0, abs(val) / (1000.0 if "sum" in name or "amount" in name else 1.0))
            score = round(float(norm_val * imp), 4)
            if score > 0:
                contributions[name] = score

        # Sort and return top 5
        sorted_top = dict(sorted(contributions.items(), key=lambda x: x[1], reverse=True)[:5])
        return sorted_top

    def predict(self, raw_txn: Optional[Dict[str, Any]] = None,
                feature_vector: Optional[FeatureVector] = None) -> PredictionResult:
        """
        Executes prediction with microsecond latency timing.
        Accepts either an already engineered FeatureVector or raw transaction event dictionary.
        """
        t0 = time.perf_counter()

        if feature_vector is None:
            if raw_txn is None:
                raise ValueError("Must provide either raw_txn or feature_vector")
            feature_vector = self.feature_store.extract_features(raw_txn)

        txn_id = feature_vector.transaction_id
        feat_list = feature_vector.to_feature_list()
        
        # Batch of 1 row for XGBoost
        X = pd.DataFrame([feat_list], columns=FEATURE_NAMES)
        
        # Inference
        probs = self.model.predict_proba(X)[0]
        # Class 1 = Fraud
        fraud_prob = float(probs[1]) if len(probs) > 1 else float(probs[0])
        risk_score = round(fraud_prob * 100.0, 1)

        # Decision rule with configurable business thresholds
        if fraud_prob >= self.fraud_threshold:
            decision = "FRAUD"
        elif fraud_prob >= self.medium_risk_threshold:
            decision = "SUSPICIOUS"
        else:
            decision = "LEGITIMATE"

        latency_ms = round((time.perf_counter() - t0) * 1000.0, 3)
        reason_codes = self.derive_reason_codes(feature_vector, fraud_prob)
        contributions = self.compute_feature_contributions(feat_list)

        return PredictionResult(
            transaction_id=txn_id,
            fraud_probability=round(fraud_prob, 4),
            risk_score=risk_score,
            decision=decision,
            model_version=self.model_version,
            latency_ms=latency_ms,
            reason_codes=reason_codes,
            feature_contributions=contributions
        )
