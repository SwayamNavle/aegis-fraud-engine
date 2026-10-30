"""
Aegis SQLAlchemy Database Models
Defines ORM entities with idempotent constraints and JSON serialization helpers.
"""

from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from sqlalchemy import (
    Column, Integer, BigInteger, String, Float, Boolean, DateTime, JSON, ForeignKey, Index
)
from sqlalchemy.orm import relationship
from services.api.database.connection import Base


class TransactionRecord(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    transaction_id = Column(String(64), unique=True, nullable=False, index=True)
    timestamp = Column(String(64), nullable=False, index=True)
    user_id = Column(String(64), nullable=False)
    account_id = Column(String(64), nullable=False, index=True)
    merchant_id = Column(String(64), nullable=False)
    merchant_category = Column(String(64), nullable=False)
    amount = Column(Float, nullable=False)
    currency = Column(String(8), default="INR")
    country = Column(String(8), nullable=False)
    city = Column(String(64), nullable=False)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    device_id = Column(String(64), nullable=False)
    device_type = Column(String(32), nullable=False)
    ip_address = Column(String(45), nullable=False)
    payment_method = Column(String(32), nullable=False)
    card_present = Column(Boolean, default=False)
    is_international = Column(Boolean, default=False)
    previous_transaction_timestamp = Column(String(64), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "transaction_id": self.transaction_id,
            "timestamp": self.timestamp,
            "user_id": self.user_id,
            "account_id": self.account_id,
            "merchant_id": self.merchant_id,
            "merchant_category": self.merchant_category,
            "amount": self.amount,
            "currency": self.currency,
            "country": self.country,
            "city": self.city,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "device_id": self.device_id,
            "device_type": self.device_type,
            "ip_address": self.ip_address,
            "payment_method": self.payment_method,
            "card_present": self.card_present,
            "is_international": self.is_international,
            "previous_transaction_timestamp": self.previous_transaction_timestamp
        }


class PredictionRecord(Base):
    __tablename__ = "predictions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    transaction_id = Column(String(64), unique=True, nullable=False, index=True)
    timestamp = Column(String(64), nullable=False, index=True)
    account_id = Column(String(64), nullable=False, index=True)
    amount = Column(Float, nullable=False)
    merchant_id = Column(String(64), nullable=False)
    country = Column(String(8), nullable=False)
    fraud_probability = Column(Float, nullable=False)
    risk_score = Column(Float, nullable=False)
    decision = Column(String(32), nullable=False, index=True)
    model_version = Column(String(64), nullable=False)
    latency_ms = Column(Float, nullable=False)
    reason_codes = Column(JSON, default=list)
    feature_contributions = Column(JSON, default=dict)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "transaction_id": self.transaction_id,
            "timestamp": self.timestamp,
            "account_id": self.account_id,
            "amount": self.amount,
            "merchant_id": self.merchant_id,
            "country": self.country,
            "fraud_probability": self.fraud_probability,
            "risk_score": self.risk_score,
            "decision": self.decision,
            "model_version": self.model_version,
            "latency_ms": self.latency_ms,
            "reason_codes": self.reason_codes or [],
            "feature_contributions": self.feature_contributions or {}
        }


class FeatureRecord(Base):
    __tablename__ = "features"

    id = Column(Integer, primary_key=True, autoincrement=True)
    transaction_id = Column(String(64), unique=True, nullable=False, index=True)
    account_id = Column(String(64), nullable=False, index=True)
    timestamp = Column(String(64), nullable=False)
    transaction_count_1m = Column(Integer, nullable=False)
    transaction_count_5m = Column(Integer, nullable=False)
    transaction_amount_sum_5m = Column(Float, nullable=False)
    transaction_amount_avg_5m = Column(Float, nullable=False)
    transaction_amount_std_5m = Column(Float, nullable=False)
    max_transaction_amount_5m = Column(Float, nullable=False)
    unique_merchants_10m = Column(Integer, nullable=False)
    unique_countries_30m = Column(Integer, nullable=False)
    unique_devices_30m = Column(Integer, nullable=False)
    international_transaction_count = Column(Integer, nullable=False)
    time_since_previous_transaction = Column(Float, nullable=False)
    distance_from_previous_transaction = Column(Float, nullable=False)
    geo_velocity_kmh = Column(Float, nullable=False)
    amount_z_score = Column(Float, nullable=False)
    user_amount_deviation = Column(Float, nullable=False)
    velocity_score = Column(Float, nullable=False)
    merchant_risk_score = Column(Float, nullable=False)
    device_change_flag = Column(Integer, nullable=False)
    country_change_flag = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "transaction_id": self.transaction_id,
            "account_id": self.account_id,
            "timestamp": self.timestamp,
            "transaction_count_1m": self.transaction_count_1m,
            "transaction_count_5m": self.transaction_count_5m,
            "transaction_amount_sum_5m": self.transaction_amount_sum_5m,
            "transaction_amount_avg_5m": self.transaction_amount_avg_5m,
            "transaction_amount_std_5m": self.transaction_amount_std_5m,
            "max_transaction_amount_5m": self.max_transaction_amount_5m,
            "unique_merchants_10m": self.unique_merchants_10m,
            "unique_countries_30m": self.unique_countries_30m,
            "unique_devices_30m": self.unique_devices_30m,
            "international_transaction_count": self.international_transaction_count,
            "time_since_previous_transaction": self.time_since_previous_transaction,
            "distance_from_previous_transaction": self.distance_from_previous_transaction,
            "geo_velocity_kmh": self.geo_velocity_kmh,
            "amount_z_score": self.amount_z_score,
            "user_amount_deviation": self.user_amount_deviation,
            "velocity_score": self.velocity_score,
            "merchant_risk_score": self.merchant_risk_score,
            "device_change_flag": self.device_change_flag,
            "country_change_flag": self.country_change_flag
        }


class FraudAlertRecord(Base):
    __tablename__ = "fraud_alerts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    alert_id = Column(String(64), unique=True, nullable=False, index=True)
    transaction_id = Column(String(64), nullable=False, index=True)
    account_id = Column(String(64), nullable=False, index=True)
    amount = Column(Float, nullable=False)
    severity = Column(String(16), nullable=False, index=True)  # LOW, MEDIUM, HIGH, CRITICAL
    risk_score = Column(Float, nullable=False)
    fraud_probability = Column(Float, nullable=False)
    reason_codes = Column(JSON, default=list)
    status = Column(String(32), default="OPEN", index=True)  # OPEN, REVIEWED, DISMISSED, ESCALATED
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "alert_id": self.alert_id,
            "transaction_id": self.transaction_id,
            "account_id": self.account_id,
            "amount": self.amount,
            "severity": self.severity,
            "risk_score": self.risk_score,
            "fraud_probability": self.fraud_probability,
            "reason_codes": self.reason_codes or [],
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }


class ModelVersionRecord(Base):
    __tablename__ = "model_versions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    model_version = Column(String(64), unique=True, nullable=False)
    algorithm = Column(String(64), nullable=False)
    training_timestamp = Column(String(64), nullable=False)
    dataset_rows = Column(Integer, nullable=False)
    fraud_threshold = Column(Float, nullable=False)
    metrics = Column(JSON, nullable=False)
    model_path = Column(String(256), nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "model_version": self.model_version,
            "algorithm": self.algorithm,
            "training_timestamp": self.training_timestamp,
            "dataset_rows": self.dataset_rows,
            "fraud_threshold": self.fraud_threshold,
            "metrics": self.metrics,
            "model_path": self.model_path,
            "is_active": self.is_active
        }
