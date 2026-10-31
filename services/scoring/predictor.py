"""
Aegis Fraud Predictor & Reason Code Engine
Calculates:
- Probability of fraud from XGBoost classifier
- Multi-factor Risk Decision Engine (ML + Rules + Customer/Merchant profiles)
- Calibrated 0-100 risk score and risk level (LOW, MEDIUM, HIGH, CRITICAL)
- Business decision (APPROVE, REVIEW, DECLINE) and legacy decision (LEGITIMATE, SUSPICIOUS, FRAUD)
- Deterministic explainability reason codes & SHAP feature contributions
"""

import time
import numpy as np
import pandas as pd
from typing import Dict, Any, List, Optional, Tuple

from services.scoring.model_loader import ModelRegistry
from services.scoring.explainability import ModelExplainer
from streaming.schemas.transaction_schema import FeatureVector, PredictionResult, FEATURE_NAMES
from features.online_features import OnlineFeatureStore
from risk_engine.decision_engine import RiskDecisionEngine, RiskDecision


class FraudPredictor:
    def __init__(self):
        self.registry = ModelRegistry.get_instance()
        self.model = self.registry.model
        self.model_version = self.registry.model_version
        self.fraud_threshold = self.registry.optimal_threshold
        self.medium_risk_threshold = self.registry.medium_risk_threshold
        self.feature_store = OnlineFeatureStore()
        self.risk_engine = RiskDecisionEngine()
        self.explainer = ModelExplainer(self.model)

    def derive_reason_codes(self, fv: FeatureVector, prob: float) -> List[str]:
        """
        Deterministic reason code generation based on feature kinematics & thresholds.
        Provides business-understandable explanations for why a transaction was flagged.
        """
        codes = []
        if fv.geo_velocity_kmh >= 600.0:
            codes.append("IMPOSSIBLE_TRAVEL")
        if fv.amount_z_score >= 2.5 or fv.user_amount_deviation >= 3.5:
            codes.append("UNUSUAL_AMOUNT")
        if fv.transaction_count_1m >= 4 or fv.velocity_score >= 7.5:
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

    def compute_feature_contributions(self, feature_values: List[float], prob: float = 0.5) -> Dict[str, float]:
        """Calculates local feature contributions via ModelExplainer (TreeSHAP)."""
        return self.explainer.explain_transaction(feature_values, prob)

    def predict(self, raw_txn: Optional[Dict[str, Any]] = None,
                feature_vector: Optional[FeatureVector] = None) -> PredictionResult:
        """
        Executes end-to-end prediction and business risk evaluation with microsecond latency timing.
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

        # Extract transaction context for Risk Decision Engine
        account_id = getattr(feature_vector, "account_id", "acc_unknown")
        user_id = raw_txn.get("user_id", "usr_unknown") if raw_txn else "usr_unknown"
        merchant_id = raw_txn.get("merchant_id", "merch_unknown") if raw_txn else "merch_unknown"
        merchant_category = raw_txn.get("merchant_category", "retail") if raw_txn else "retail"
        amount = float(raw_txn.get("amount", 0.0)) if raw_txn else 0.0

        # Run Multi-factor Risk Decision Engine
        risk_decision: RiskDecision = self.risk_engine.evaluate_transaction(
            transaction_id=txn_id,
            fraud_probability=fraud_prob,
            feature_vector=feature_vector,
            raw_txn=raw_txn,
            account_id=account_id,
            user_id=user_id,
            merchant_id=merchant_id,
            merchant_category=merchant_category,
            amount=amount
        )

        latency_ms = round((time.perf_counter() - t0) * 1000.0, 3)
        contributions = self.compute_feature_contributions(feat_list, fraud_prob)

        # Merge reason codes (ensuring backward compatibility with tests)
        deterministic_reasons = self.derive_reason_codes(feature_vector, fraud_prob)
        all_reasons = list(dict.fromkeys(risk_decision.reason_codes + deterministic_reasons))

        return PredictionResult(
            transaction_id=txn_id,
            correlation_id=raw_txn.get("correlation_id") if raw_txn else None,
            fraud_probability=round(fraud_prob, 4),
            risk_score=risk_decision.risk_score,
            risk_level=risk_decision.risk_level,
            business_decision=risk_decision.business_decision,
            decision=risk_decision.decision,
            model_version=self.model_version,
            latency_ms=latency_ms,
            reason_codes=all_reasons,
            rule_violations=[r.model_dump() for r in risk_decision.triggered_rules],
            feature_contributions=contributions,
            decision_rationale=risk_decision.decision_rationale
        )
