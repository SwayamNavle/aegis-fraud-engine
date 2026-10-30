"""
Aegis Model Loader
Singleton model registry that loads the serialized XGBoost fraud detector once at startup.
"""

import json
import os
import sys
from typing import Dict, Any, Optional
from xgboost import XGBClassifier

# Ensure project root is in python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from streaming.schemas.transaction_schema import FEATURE_NAMES


class ModelRegistry:
    _instance: Optional["ModelRegistry"] = None

    def __init__(self,
                 model_path: str = "ml/models/xgb_fraud_model.json",
                 schema_path: str = "ml/artifacts/feature_schema.json",
                 metadata_path: str = "ml/artifacts/training_metadata.json"):
        self.model_path = model_path
        self.schema_path = schema_path
        self.metadata_path = metadata_path
        
        self.model: Optional[XGBClassifier] = None
        self.model_version: str = "xgb-v1.0.0"
        self.optimal_threshold: float = float(os.getenv("FRAUD_THRESHOLD", "0.70"))
        self.medium_risk_threshold: float = float(os.getenv("MEDIUM_RISK_THRESHOLD", "0.40"))
        self.feature_names = FEATURE_NAMES
        self.metadata: Dict[str, Any] = {}
        
        self.load_model()

    @classmethod
    def get_instance(cls) -> "ModelRegistry":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def load_model(self) -> None:
        """Loads serialized XGBoost model and configuration."""
        if not os.path.exists(self.model_path):
            raise FileNotFoundError(f"Model file not found at: {self.model_path}. Run 'python ml/training/train.py' first.")

        print(f"[Aegis ModelLoader] Loading model from {self.model_path}...")
        self.model = XGBClassifier()
        self.model.load_model(self.model_path)

        # Load metadata if present
        if os.path.exists(self.metadata_path):
            with open(self.metadata_path, "r") as f:
                self.metadata = json.load(f)
                self.model_version = self.metadata.get("model_version", self.model_version)
                self.optimal_threshold = float(self.metadata.get("optimal_threshold", self.optimal_threshold))

        # Check environment override
        env_threshold = os.getenv("FRAUD_THRESHOLD")
        if env_threshold:
            self.optimal_threshold = float(env_threshold)

        print(f"[Aegis ModelLoader] Model {self.model_version} loaded. Active Fraud Threshold: {self.optimal_threshold:.2f}")

    def get_info(self) -> Dict[str, Any]:
        return {
            "model_version": self.model_version,
            "algorithm": "XGBoost",
            "fraud_threshold": self.optimal_threshold,
            "medium_risk_threshold": self.medium_risk_threshold,
            "feature_count": len(self.feature_names),
            "features": self.feature_names,
            "metadata": self.metadata
        }
