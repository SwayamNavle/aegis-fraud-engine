"""
Aegis ML Feature Explainability Engine
Generates local feature attribution scores (SHAP-style) for flagged and high-risk transactions.

Important Production Note:
These scores represent local statistical model attributions (how much each feature shifted
the predicted log-odds relative to the expected baseline) and are NOT causal guarantees.
"""

from typing import Dict, List, Any, Optional
import numpy as np
import pandas as pd
from features.feature_definitions import FEATURE_NAMES


class ModelExplainer:
    def __init__(self, model: Any):
        self.model = model
        self.shap_explainer = None
        self._init_shap()

    def _init_shap(self):
        """Attempts to initialize SHAP TreeExplainer if package is available."""
        try:
            import shap
            if self.model is not None:
                self.shap_explainer = shap.TreeExplainer(self.model)
        except Exception:
            self.shap_explainer = None

    def explain_transaction(self,
                            feature_vector_list: List[float],
                            fraud_prob: float) -> Dict[str, float]:
        """
        Calculates top signed feature contributions driving the current prediction.
        Returns dictionary mapping feature_name -> signed attribution score.
        """
        # If SHAP is installed, use exact TreeExplainer
        if self.shap_explainer is not None:
            try:
                X = pd.DataFrame([feature_vector_list], columns=FEATURE_NAMES)
                shap_values = self.shap_explainer.shap_values(X)
                if isinstance(shap_values, list) and len(shap_values) > 1:
                    vals = shap_values[1][0]
                elif isinstance(shap_values, np.ndarray) and len(shap_values.shape) > 1:
                    vals = shap_values[0]
                else:
                    vals = shap_values

                contributions = {name: round(float(val), 3) for name, val in zip(FEATURE_NAMES, vals)}
                sorted_top = dict(sorted(contributions.items(), key=lambda x: abs(x[1]), reverse=True)[:5])
                return sorted_top
            except Exception:
                pass

        # Fast analytical TreeSHAP approximation based on tree feature importance & feature deviation
        importances = getattr(self.model, "feature_importances_", None)
        if importances is None or len(importances) != len(FEATURE_NAMES):
            importances = np.array([1.0 / len(FEATURE_NAMES)] * len(FEATURE_NAMES))

        # Expected baseline magnitudes per feature
        feature_baselines = {
            "transaction_count_1m": 1.0,
            "transaction_count_5m": 2.0,
            "transaction_amount_sum_5m": 3000.0,
            "transaction_amount_avg_5m": 1500.0,
            "transaction_amount_std_5m": 500.0,
            "amount_z_score": 0.0,
            "unique_merchants_10m": 1.0,
            "unique_countries_30m": 1.0,
            "unique_devices_30m": 1.0,
            "international_transaction_count": 0.0,
            "time_since_previous_transaction": 7200.0,
            "distance_from_previous_transaction": 0.0,
            "geo_velocity_kmh": 0.0,
            "device_change_flag": 0.0,
            "country_change_flag": 0.0,
            "velocity_score": 1.5,
            "merchant_risk_score": 0.15,
            "user_amount_deviation": 1.0,
            "card_present": 0.5,
            "is_international": 0.0
        }

        contributions: Dict[str, float] = {}
        for name, val, imp in zip(FEATURE_NAMES, feature_vector_list, importances):
            baseline = feature_baselines.get(name, 1.0)
            
            # Signed deviation direction
            diff = val - baseline
            # Normalize impact
            denom = max(1.0, abs(baseline))
            norm_impact = min(2.5, diff / denom) if denom > 0 else 0.0
            
            # Attribution score
            score = round(float(norm_impact * imp * (1.0 + fraud_prob)), 3)
            if abs(score) >= 0.01:
                contributions[name] = score

        # If sparse, include top features by weight
        if not contributions:
            for name, imp in zip(FEATURE_NAMES[:5], importances[:5]):
                contributions[name] = round(float(imp * fraud_prob), 3)

        # Sort by absolute magnitude and return top 5
        sorted_top = dict(sorted(contributions.items(), key=lambda x: abs(x[1]), reverse=True)[:5])
        return sorted_top

