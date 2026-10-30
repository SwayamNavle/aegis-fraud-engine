"""
Aegis Transaction Schemas
Defines Pydantic schemas for raw transactions, feature vectors, scoring outputs, and alerts.
"""

from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, ConfigDict


class TransactionEvent(BaseModel):
    """
    Standard transaction event schema.
    Includes ground-truth 'label' which is only populated during training/evaluation dataset creation.
    """
    model_config = ConfigDict(extra="ignore")

    transaction_id: str = Field(..., description="Unique transaction identifier (e.g. txn_...)")
    timestamp: str = Field(..., description="ISO 8601 transaction timestamp")
    user_id: str = Field(..., description="Unique customer user ID")
    account_id: str = Field(..., description="Account ID used for Kafka partition affinity")
    merchant_id: str = Field(..., description="Merchant identifier")
    merchant_category: str = Field(..., description="Category: grocery, fuel, retail, crypto, gambling, luxury, travel")
    amount: float = Field(..., ge=0.01, description="Transaction amount")
    currency: str = Field(default="INR", description="Three-letter ISO currency code")
    country: str = Field(..., description="Two-letter ISO country code (e.g. IN, US, GB)")
    city: str = Field(..., description="City of origin")
    latitude: float = Field(..., description="Latitude coordinate")
    longitude: float = Field(..., description="Longitude coordinate")
    device_id: str = Field(..., description="Device fingerprint hash")
    device_type: str = Field(..., description="iPhone, Android, Web, Tablet")
    ip_address: str = Field(..., description="IPv4 / IPv6 client address")
    payment_method: str = Field(..., description="credit_card, debit_card, upi, wire_transfer")
    card_present: bool = Field(default=False, description="True if physical POS terminal chip/tap")
    is_international: bool = Field(default=False, description="True if transaction country differs from account home country")
    previous_transaction_timestamp: Optional[str] = Field(None, description="Timestamp of preceding transaction for account")
    
    # Ground truth label: 0 = Legitimate, 1 = Fraud.
    # Excluded in live production scoring payloads.
    label: Optional[int] = Field(default=None, description="0=Legitimate, 1=Fraud (Only for offline/training)")

    def to_production_dict(self) -> Dict[str, Any]:
        """Returns payload without ground truth label for live production scoring."""
        d = self.model_dump()
        d.pop("label", None)
        return d


class ProductionTransactionEvent(BaseModel):
    """Production transaction payload where ground-truth label is strictly absent."""
    model_config = ConfigDict(extra="ignore")

    transaction_id: str
    timestamp: str
    user_id: str
    account_id: str
    merchant_id: str
    merchant_category: str
    amount: float
    currency: str = "INR"
    country: str
    city: str
    latitude: float
    longitude: float
    device_id: str
    device_type: str
    ip_address: str
    payment_method: str
    card_present: bool
    is_international: bool
    previous_transaction_timestamp: Optional[str] = None


class FeatureVector(BaseModel):
    """
    Standardized sliding-window and behavioral feature vector.
    This exact schema is shared between ML training, PySpark streaming, and scoring inference.
    """
    model_config = ConfigDict(extra="ignore")

    transaction_id: str
    account_id: str
    timestamp: str

    # Windowed count and amount aggregations (1m, 5m)
    transaction_count_1m: int = Field(default=1, description="Count of transactions in last 1 minute")
    transaction_count_5m: int = Field(default=1, description="Count of transactions in last 5 minutes")
    transaction_amount_sum_5m: float = Field(default=0.0, description="Sum of transaction amounts in last 5 minutes")
    transaction_amount_avg_5m: float = Field(default=0.0, description="Average transaction amount in last 5 minutes")
    transaction_amount_std_5m: float = Field(default=0.0, description="Std dev of transaction amounts in last 5 minutes")
    max_transaction_amount_5m: float = Field(default=0.0, description="Max transaction amount in last 5 minutes")

    # Cardinality features
    unique_merchants_10m: int = Field(default=1, description="Distinct merchants visited in last 10 minutes")
    unique_countries_30m: int = Field(default=1, description="Distinct countries visited in last 30 minutes")
    unique_devices_30m: int = Field(default=1, description="Distinct devices used in last 30 minutes")
    international_transaction_count: int = Field(default=0, description="Count of international transactions in window")

    # Velocity and distance kinematics
    time_since_previous_transaction: float = Field(default=3600.0, description="Seconds elapsed since preceding event")
    distance_from_previous_transaction: float = Field(default=0.0, description="Kilometers from previous transaction coordinates")
    geo_velocity_kmh: float = Field(default=0.0, description="Implied travel velocity in km/h")

    # Deviation and anomaly scores
    amount_z_score: float = Field(default=0.0, description="Z-score deviation relative to user historical average")
    user_amount_deviation: float = Field(default=1.0, description="Ratio of current amount to 5m window average")
    velocity_score: float = Field(default=0.0, description="Composite velocity frequency score")
    merchant_risk_score: float = Field(default=0.1, description="Risk weight assigned to merchant category [0.0 - 1.0]")
    
    # Categorical flags
    device_change_flag: int = Field(default=0, description="1 if device differs from primary device")
    country_change_flag: int = Field(default=0, description="1 if country differs from primary country")
    card_present: int = Field(default=0, description="1 if card present, else 0")
    is_international: int = Field(default=0, description="1 if international, else 0")

    def to_feature_list(self) -> List[float]:
        """Returns numerical feature array aligned with XGBoost training order."""
        return [
            float(self.transaction_count_1m),
            float(self.transaction_count_5m),
            float(self.transaction_amount_sum_5m),
            float(self.transaction_amount_avg_5m),
            float(self.transaction_amount_std_5m),
            float(self.amount_z_score),
            float(self.unique_merchants_10m),
            float(self.unique_countries_30m),
            float(self.unique_devices_30m),
            float(self.international_transaction_count),
            float(self.time_since_previous_transaction),
            float(self.distance_from_previous_transaction),
            float(self.geo_velocity_kmh),
            float(self.device_change_flag),
            float(self.country_change_flag),
            float(self.velocity_score),
            float(self.merchant_risk_score),
            float(self.user_amount_deviation),
            float(self.card_present),
            float(self.is_international)
        ]


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


class PredictionResult(BaseModel):
    """Inference result returned by XGBoost scoring engine."""
    transaction_id: str
    fraud_probability: float
    risk_score: float = Field(..., description="Calibrated risk score between 0.0 and 100.0")
    decision: str = Field(..., description="LEGITIMATE, SUSPICIOUS, or FRAUD")
    model_version: str
    latency_ms: float
    reason_codes: List[str] = Field(default_factory=list)
    feature_contributions: Optional[Dict[str, float]] = None


class FraudAlert(BaseModel):
    """Alert record for high-risk and fraud transactions."""
    alert_id: str
    transaction_id: str
    timestamp: str
    severity: str = Field(..., description="LOW, MEDIUM, HIGH, CRITICAL")
    risk_score: float
    fraud_probability: float
    reason_codes: List[str]
    status: str = Field(default="OPEN", description="OPEN, REVIEWED, DISMISSED, ESCALATED")
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
