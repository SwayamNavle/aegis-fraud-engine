"""
Aegis Customer & Merchant Profiling Engine
Maintains behavioral baselines, historical activity distributions, and entity risk scores.
"""

from typing import Dict, Any, List, Optional, Set
import math


class CustomerProfile:
    def __init__(self, account_id: str, user_id: str):
        self.account_id = account_id
        self.user_id = user_id
        self.total_transactions: int = 0
        self.total_spend: float = 0.0
        self.avg_amount: float = 0.0
        self.std_amount: float = 0.0
        self.max_amount: float = 0.0
        self.fraud_count: int = 0
        self.known_devices: Set[str] = set()
        self.known_countries: Set[str] = set()
        self.customer_risk_score: float = 15.0  # Baseline low risk
        self._amounts_history: List[float] = []

    def update_with_transaction(self, amount: float, device_id: str, country: str, is_fraud: bool = False):
        self.total_transactions += 1
        self.total_spend += amount
        self._amounts_history.append(amount)
        if len(self._amounts_history) > 200:
            self._amounts_history.pop(0)

        self.avg_amount = self.total_spend / self.total_transactions
        self.max_amount = max(self.max_amount, amount)

        # Standard deviation
        if len(self._amounts_history) > 1:
            mean = sum(self._amounts_history) / len(self._amounts_history)
            variance = sum((x - mean) ** 2 for x in self._amounts_history) / (len(self._amounts_history) - 1)
            self.std_amount = math.sqrt(variance)
        else:
            self.std_amount = max(10.0, self.avg_amount * 0.4)

        self.known_devices.add(device_id)
        self.known_countries.add(country)

        if is_fraud:
            self.fraud_count += 1
            self.customer_risk_score = min(100.0, self.customer_risk_score + 25.0)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "account_id": self.account_id,
            "user_id": self.user_id,
            "total_transactions": self.total_transactions,
            "total_spend": round(self.total_spend, 2),
            "avg_amount": round(self.avg_amount, 2),
            "std_amount": round(self.std_amount, 2),
            "max_amount": round(self.max_amount, 2),
            "fraud_count": self.fraud_count,
            "known_devices": list(self.known_devices),
            "known_countries": list(self.known_countries),
            "customer_risk_score": round(self.customer_risk_score, 1)
        }


class MerchantProfile:
    def __init__(self, merchant_id: str, merchant_name: str, category: str):
        self.merchant_id = merchant_id
        self.merchant_name = merchant_name
        self.category = category
        self.total_transactions: int = 0
        self.total_volume: float = 0.0
        self.fraud_count: int = 0
        self.fraud_rate: float = 0.0
        self.merchant_risk_score: float = 20.0

    def update_with_transaction(self, amount: float, is_fraud: bool = False):
        self.total_transactions += 1
        self.total_volume += amount
        if is_fraud:
            self.fraud_count += 1

        self.fraud_rate = (self.fraud_count / max(1, self.total_transactions)) * 100.0
        
        # Risk score calibrated by fraud rate and high-risk industry categories
        base_cat_risk = {
            "crypto_exchange": 65.0,
            "online_gambling": 60.0,
            "offshore_gaming": 55.0,
            "luxury_watches": 45.0,
            "wire_remittance": 40.0,
            "electronics": 25.0,
            "department_store": 15.0,
            "restaurants": 10.0,
            "fuel": 8.0,
            "grocery": 5.0
        }.get(self.category, 20.0)

        self.merchant_risk_score = min(100.0, round(base_cat_risk + (self.fraud_rate * 2.5), 1))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "merchant_id": self.merchant_id,
            "merchant_name": self.merchant_name,
            "category": self.category,
            "total_transactions": self.total_transactions,
            "total_volume": round(self.total_volume, 2),
            "avg_amount": round(self.total_volume / max(1, self.total_transactions), 2),
            "fraud_count": self.fraud_count,
            "fraud_rate": round(self.fraud_rate, 2),
            "merchant_risk_score": round(self.merchant_risk_score, 1)
        }


class ProfileManager:
    _instance: Optional["ProfileManager"] = None

    def __init__(self):
        self.customers: Dict[str, CustomerProfile] = {}
        self.merchants: Dict[str, MerchantProfile] = {}

    @classmethod
    def get_instance(cls) -> "ProfileManager":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def get_or_create_customer(self, account_id: str, user_id: str = "usr_unknown") -> CustomerProfile:
        if account_id not in self.customers:
            self.customers[account_id] = CustomerProfile(account_id=account_id, user_id=user_id)
        return self.customers[account_id]

    def get_or_create_merchant(self, merchant_id: str, category: str = "retail", name: Optional[str] = None) -> MerchantProfile:
        if merchant_id not in self.merchants:
            merchant_name = name or f"Merchant {merchant_id[-6:]}"
            self.merchants[merchant_id] = MerchantProfile(merchant_id=merchant_id, merchant_name=merchant_name, category=category)
        return self.merchants[merchant_id]

