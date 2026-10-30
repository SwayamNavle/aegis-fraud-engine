"""
Unit tests for Aegis synthetic transaction generator and fraud patterns.
"""

import pytest
from streaming.producer.producer import SyntheticTransactionGenerator
from streaming.schemas.transaction_schema import TransactionEvent


def test_generator_legitimate_event():
    gen = SyntheticTransactionGenerator(num_users=50, fraud_ratio=0.0)
    event = gen.generate_event(force_fraud=False)
    
    assert isinstance(event, TransactionEvent)
    assert event.label == 0
    assert event.amount >= 10.0
    assert event.currency == "INR"
    assert event.transaction_id.startswith("txn_")
    assert event.account_id.startswith("acc_")


def test_generator_fraud_event():
    gen = SyntheticTransactionGenerator(num_users=50, fraud_ratio=1.0)
    event = gen.generate_event(force_fraud=True)
    
    assert isinstance(event, TransactionEvent)
    assert event.label == 1
    # Production payload should strip label
    prod_dict = event.to_production_dict()
    assert "label" not in prod_dict
    assert "transaction_id" in prod_dict


def test_burst_fraud_ratio():
    gen = SyntheticTransactionGenerator(num_users=100, fraud_ratio=0.02)
    events = [gen.generate_event() for _ in range(500)]
    fraud_count = sum(1 for e in events if e.label == 1)
    
    # Check that fraud is rare (between 0.5% and 5.0%)
    fraud_pct = fraud_count / len(events)
    assert 0.005 <= fraud_pct <= 0.05
