"""
Aegis Risk Decision Engine
Combines:
- XGBoost fraud probability (ML Score)
- Rule Engine violations
- Customer behavioral profile risk
- Merchant category and track record risk
- Transaction monetary value

Computes:
- risk_score: 0 to 100
- risk_level: LOW, MEDIUM, HIGH, CRITICAL
- business_decision: APPROVE, REVIEW, DECLINE
- decision: LEGITIMATE, SUSPICIOUS, FRAUD (for backward compatibility)
"""

from typing import Dict, Any, List, Optional, Tuple
from pydantic import BaseModel, Field
from risk_engine.rules import FraudRuleEngine, RuleEvaluationResult, RuleEngineConfig
from risk_engine.profiler import ProfileManager, CustomerProfile, MerchantProfile


class RiskDecision(BaseModel):
    transaction_id: str
    fraud_probability: float
    risk_score: float = Field(ge=0.0, le=100.0)
    risk_level: str  # LOW, MEDIUM, HIGH, CRITICAL
    business_decision: str  # APPROVE, REVIEW, DECLINE
    decision: str  # LEGITIMATE, SUSPICIOUS, FRAUD (compatibility)
    triggered_rules: List[RuleEvaluationResult]
    reason_codes: List[str]
    customer_risk_score: float
    merchant_risk_score: float
    decision_rationale: str


class RiskEngineConfig(BaseModel):
    # Weight distribution [0.0 - 1.0]
    ml_weight: float = 0.55
    rules_weight: float = 0.25
    customer_weight: float = 0.10
    merchant_weight: float = 0.10

    # Business decision cutoffs on composite 0-100 risk score
    decline_threshold: float = 75.0
    review_threshold: float = 45.0

    # Auto-decline rule overrides (e.g. impossible travel with high spend)
    auto_decline_rules: List[str] = ["IMPOSSIBLE_TRAVEL"]


class RiskDecisionEngine:
    def __init__(self,
                 rule_engine: Optional[FraudRuleEngine] = None,
                 config: Optional[RiskEngineConfig] = None):
        self.rule_engine = rule_engine or FraudRuleEngine()
        self.config = config or RiskEngineConfig()
        self.profile_manager = ProfileManager.get_instance()

    def evaluate_transaction(self,
                             transaction_id: str,
                             fraud_probability: float,
                             feature_vector: Any,
                             raw_txn: Optional[Dict[str, Any]] = None,
                             account_id: Optional[str] = None,
                             user_id: Optional[str] = None,
                             merchant_id: Optional[str] = None,
                             merchant_category: Optional[str] = None,
                             amount: float = 0.0) -> RiskDecision:
        """
        Executes multi-factor risk assessment combining ML score with rule violations
        and entity profile context.
        """
        # Fetch or initialize profiles
        acc_id = account_id or getattr(feature_vector, "account_id", "acc_unknown")
        usr_id = user_id or getattr(feature_vector, "user_id", "usr_unknown")
        merch_id = merchant_id or getattr(feature_vector, "merchant_id", "merch_unknown")
        merch_cat = merchant_category or getattr(feature_vector, "merchant_category", "retail")
        amt = amount or getattr(feature_vector, "amount", 0.0)

        cust_profile = self.profile_manager.get_or_create_customer(acc_id, usr_id)
        merch_profile = self.profile_manager.get_or_create_merchant(merch_id, merch_cat)

        # 1. Rule Engine Evaluation
        triggered_rules = self.rule_engine.evaluate_rules(
            feature_vector=feature_vector,
            raw_txn=raw_txn,
            customer_profile=cust_profile.to_dict(),
            merchant_profile=merch_profile.to_dict()
        )
        reason_codes = [r.rule_id for r in triggered_rules]

        # 2. Score Synthesis
        # ML component: 0-100 scale
        ml_score = min(100.0, max(0.0, fraud_probability * 100.0))

        # Rule score: sum of triggered weights capped at 100
        raw_rule_score = sum(r.weight for r in triggered_rules)
        rule_score = min(100.0, raw_rule_score * 1.5)

        # Customer & Merchant scores
        cust_score = cust_profile.customer_risk_score
        merch_score = merch_profile.merchant_risk_score

        # Composite weighted score
        composite_score = (
            (ml_score * self.config.ml_weight) +
            (rule_score * self.config.rules_weight) +
            (cust_score * self.config.customer_weight) +
            (merch_score * self.config.merchant_weight)
        )

        # High amount multiplier (e.g. transactions > ₹50,000 face heightened scrutiny)
        if amt >= 50000.0 and (ml_score > 30.0 or len(triggered_rules) >= 1):
            composite_score = min(100.0, composite_score + 15.0)

        composite_score = round(min(100.0, max(0.0, composite_score)), 1)

        # 3. Categorize Risk Level
        if composite_score >= 80.0:
            risk_level = "CRITICAL"
        elif composite_score >= 60.0:
            risk_level = "HIGH"
        elif composite_score >= 30.0:
            risk_level = "MEDIUM"
        else:
            risk_level = "LOW"

        # 4. Determine Business Decision
        # Check for immediate critical auto-decline overrides
        has_critical_override = any(r.rule_id in self.config.auto_decline_rules for r in triggered_rules) and amt > 10000.0

        if composite_score >= self.config.decline_threshold or has_critical_override:
            business_decision = "DECLINE"
            legacy_decision = "FRAUD"
            rationale = "Risk score exceeds automated decline threshold or critical rule violated"
        elif composite_score >= self.config.review_threshold:
            business_decision = "REVIEW"
            legacy_decision = "SUSPICIOUS"
            rationale = "Elevated risk score flagged for manual fraud analyst verification"
        else:
            business_decision = "APPROVE"
            legacy_decision = "LEGITIMATE"
            rationale = "Transaction passed all behavioral and machine learning risk criteria"

        # If high ML probability but no rules, add STATISTICAL_ANOMALY reason code
        if fraud_probability >= 0.70 and not reason_codes:
            reason_codes.append("STATISTICAL_ANOMALY")

        return RiskDecision(
            transaction_id=transaction_id,
            fraud_probability=round(fraud_probability, 4),
            risk_score=composite_score,
            risk_level=risk_level,
            business_decision=business_decision,
            decision=legacy_decision,
            triggered_rules=triggered_rules,
            reason_codes=reason_codes,
            customer_risk_score=round(cust_score, 1),
            merchant_risk_score=round(merch_score, 1),
            decision_rationale=rationale
        )

