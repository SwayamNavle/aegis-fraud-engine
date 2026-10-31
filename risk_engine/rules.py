"""
Aegis Fraud Rule Engine
Configurable deterministic rule evaluation returning structured rule violations.
"""

from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field


class RuleEvaluationResult(BaseModel):
    rule_id: str
    triggered: bool
    severity: str  # LOW, MEDIUM, HIGH, CRITICAL
    message: str
    weight: float = Field(default=10.0, description="Risk contribution points [0-40]")


class RuleEngineConfig(BaseModel):
    velocity_1m_threshold: int = 4
    velocity_score_threshold: float = 7.5
    burst_amount_5m_threshold: float = 50000.0
    amount_z_score_threshold: float = 2.5
    user_amount_deviation_threshold: float = 3.5
    geo_velocity_kmh_threshold: float = 600.0
    merchant_risk_threshold: float = 0.70
    rapid_succession_seconds: float = 15.0


class FraudRuleEngine:
    def __init__(self, config: Optional[RuleEngineConfig] = None):
        self.config = config or RuleEngineConfig()

    def evaluate_rules(self,
                       feature_vector: Any,
                       raw_txn: Optional[Dict[str, Any]] = None,
                       customer_profile: Optional[Dict[str, Any]] = None,
                       merchant_profile: Optional[Dict[str, Any]] = None) -> List[RuleEvaluationResult]:
        """
        Evaluates 8 deterministic business and behavioral rules against the current transaction.
        Returns a list of triggered rule evaluations.
        """
        triggered: List[RuleEvaluationResult] = []

        # Rule 1: High Transaction Velocity
        tx_1m = getattr(feature_vector, "transaction_count_1m", 0)
        vel_score = getattr(feature_vector, "velocity_score", 0.0)
        if tx_1m >= self.config.velocity_1m_threshold or vel_score >= self.config.velocity_score_threshold:
            triggered.append(RuleEvaluationResult(
                rule_id="HIGH_TRANSACTION_VELOCITY",
                triggered=True,
                severity="HIGH",
                message=f"High velocity: {tx_1m} transactions in 1m (velocity score: {vel_score:.1f})",
                weight=25.0
            ))

        # Rule 2: Unusual Amount Anomaly
        z_score = getattr(feature_vector, "amount_z_score", 0.0)
        dev = getattr(feature_vector, "user_amount_deviation", 0.0)
        if z_score >= self.config.amount_z_score_threshold or dev >= self.config.user_amount_deviation_threshold:
            triggered.append(RuleEvaluationResult(
                rule_id="UNUSUAL_AMOUNT",
                triggered=True,
                severity="HIGH" if dev >= 5.0 else "MEDIUM",
                message=f"Amount anomaly: spend is {dev:.1f}x customer standard deviation (z-score: {z_score:.2f})",
                weight=20.0
            ))

        # Rule 3: Impossible Travel (Geographic Velocity)
        geo_vel = getattr(feature_vector, "geo_velocity_kmh", 0.0)
        if geo_vel >= self.config.geo_velocity_kmh_threshold:
            triggered.append(RuleEvaluationResult(
                rule_id="IMPOSSIBLE_TRAVEL",
                triggered=True,
                severity="CRITICAL",
                message=f"Physical impossibility: geographical displacement requires {geo_vel:,.0f} km/h travel speed",
                weight=35.0
            ))

        # Rule 4: New Device
        dev_change = getattr(feature_vector, "device_change_flag", 0)
        if dev_change == 1:
            triggered.append(RuleEvaluationResult(
                rule_id="NEW_DEVICE",
                triggered=True,
                severity="MEDIUM",
                message="Transaction initiated from an unrecognized hardware device ID",
                weight=15.0
            ))

        # Rule 5: New Country / Geolocation Shift
        country_change = getattr(feature_vector, "country_change_flag", 0)
        if country_change == 1:
            triggered.append(RuleEvaluationResult(
                rule_id="NEW_COUNTRY",
                triggered=True,
                severity="MEDIUM",
                message="Transaction origin differs from customer primary registered billing country",
                weight=15.0
            ))

        # Rule 6: Unusual or High-Risk Merchant Category
        merch_risk = getattr(feature_vector, "merchant_risk_score", 0.0)
        if merch_risk >= self.config.merchant_risk_threshold:
            triggered.append(RuleEvaluationResult(
                rule_id="UNUSUAL_MERCHANT",
                triggered=True,
                severity="HIGH",
                message=f"High-risk merchant terminal category (risk index: {merch_risk:.2f})",
                weight=20.0
            ))

        # Rule 7: International Transaction Spike
        is_intl = getattr(feature_vector, "is_international", 0)
        intl_count = getattr(feature_vector, "international_transaction_count", 0)
        if is_intl == 1 and intl_count >= 2:
            triggered.append(RuleEvaluationResult(
                rule_id="INTERNATIONAL_SPIKE",
                triggered=True,
                severity="HIGH",
                message=f"Cross-border spike: {intl_count} international charges detected within window",
                weight=25.0
            ))

        # Rule 8: Rapid Multiple Transactions (< 15 seconds)
        time_since_prev = getattr(feature_vector, "time_since_previous_transaction", 999.0)
        if time_since_prev < self.config.rapid_succession_seconds and tx_1m >= 2:
            triggered.append(RuleEvaluationResult(
                rule_id="MULTIPLE_RAPID_TRANSACTIONS",
                triggered=True,
                severity="HIGH",
                message=f"Sub-second burst: previous transaction occurred {time_since_prev:.1f}s ago",
                weight=20.0
            ))

        return triggered

