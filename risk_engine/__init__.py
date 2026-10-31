"""
Aegis Risk Engine Package
Exposes FraudRuleEngine, RiskDecisionEngine, and ProfileManager.
"""

from risk_engine.rules import FraudRuleEngine, RuleEvaluationResult, RuleEngineConfig
from risk_engine.profiler import ProfileManager, CustomerProfile, MerchantProfile
from risk_engine.decision_engine import RiskDecisionEngine, RiskDecision, RiskEngineConfig

__all__ = [
    "FraudRuleEngine",
    "RuleEvaluationResult",
    "RuleEngineConfig",
    "ProfileManager",
    "CustomerProfile",
    "MerchantProfile",
    "RiskDecisionEngine",
    "RiskDecision",
    "RiskEngineConfig"
]

