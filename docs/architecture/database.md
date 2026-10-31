# Database Schema & Entity-Relationship Architecture

This document documents the relational database architecture, indexes, and entity relationships backing Aegis.

```mermaid
erDiagram
    TRANSACTIONS ||--o| PREDICTIONS : "generates"
    TRANSACTIONS ||--o| FEATURES : "extracted into"
    TRANSACTIONS ||--o| FRAUD_ALERTS : "triggers"
    CUSTOMER_PROFILES ||--o{ TRANSACTIONS : "submits"
    MERCHANT_PROFILES ||--o{ TRANSACTIONS : "receives"
    MODEL_VERSIONS ||--o{ PREDICTIONS : "scored_by"

    TRANSACTIONS {
        string transaction_id PK
        string account_id FK
        float amount
        string currency
        timestamp timestamp
        string merchant_id FK
        string merchant_category
        float latitude
        float longitude
        string device_id
        string ip_address
        string channel
        string status
        string correlation_id
        timestamp created_at
    }

    PREDICTIONS {
        string prediction_id PK
        string transaction_id FK
        float fraud_probability
        string decision
        float risk_score
        string business_decision
        string model_version FK
        float latency_ms
        jsonb explanation
        timestamp created_at
    }

    FEATURES {
        string transaction_id PK
        float amount
        int hour_of_day
        int day_of_week
        int is_weekend
        int card_present
        int transaction_count_1m
        int transaction_count_5m
        int transaction_count_10m
        int transaction_count_30m
        float transaction_amount_sum_5m
        float transaction_amount_mean_5m
        float transaction_amount_std_5m
        float distance_from_last_txn_km
        float time_since_last_txn_sec
        float geo_velocity_kmh
        float amount_to_mean_ratio_5m
        int unique_merchants_30m
        int unique_countries_30m
        int failed_attempts_30m
        float device_risk_score
        timestamp created_at
    }

    FRAUD_ALERTS {
        string alert_id PK
        string transaction_id FK
        string severity
        float risk_score
        jsonb triggered_rules
        string status
        string reviewer
        string notes
        int final_ground_truth
        timestamp updated_at
        timestamp created_at
    }

    CUSTOMER_PROFILES {
        string account_id PK
        float normal_amount_mean
        float normal_amount_std
        float max_normal_amount
        int total_transactions
        jsonb common_countries
        jsonb common_merchants
        jsonb common_devices
        float customer_risk_score
        timestamp last_seen
        timestamp created_at
        timestamp updated_at
    }

    MERCHANT_PROFILES {
        string merchant_id PK
        string merchant_category
        int total_transactions
        int fraud_count
        float chargeback_rate
        float merchant_risk_score
        timestamp last_seen
        timestamp created_at
        timestamp updated_at
    }

    MODEL_VERSIONS {
        string version PK
        string model_type
        jsonb metrics
        jsonb parameters
        string artifact_path
        string dataset_version
        string feature_version
        string status
        int is_active
        timestamp created_at
        timestamp updated_at
    }

    IDEMPOTENCY_KEYS {
        string key PK
        string transaction_id
        timestamp created_at
        timestamp expires_at
    }
```

## Indexing Strategy
To guarantee sub-millisecond lookups during high-velocity streaming:
1. `idx_transactions_account_timestamp`: Composite B-Tree index on `(account_id, timestamp DESC)` for fast historical sliding window retrieval.
2. `idx_predictions_decision`: Single-column index on `predictions(decision)` and `predictions(business_decision)` for triage filtering.
3. `idx_alerts_status`: B-Tree on `fraud_alerts(status)` for SOC analyst queue queries (`NEW`, `UNDER_REVIEW`).
4. `idx_idempotency_key`: Unique primary index on `idempotency_keys(key)` ensuring hardware-level constraint enforcement.

