-- ==============================================================================
-- AEGIS ENGINE POSTGRESQL INITIALIZATION SCHEMA
-- ==============================================================================

CREATE TABLE IF NOT EXISTS transactions (
    id BIGSERIAL PRIMARY KEY,
    transaction_id VARCHAR(64) UNIQUE NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    user_id VARCHAR(64) NOT NULL,
    account_id VARCHAR(64) NOT NULL,
    merchant_id VARCHAR(64) NOT NULL,
    merchant_category VARCHAR(64) NOT NULL,
    amount NUMERIC(12, 2) NOT NULL,
    currency VARCHAR(8) DEFAULT 'INR',
    country VARCHAR(8) NOT NULL,
    city VARCHAR(64) NOT NULL,
    latitude DOUBLE PRECISION NOT NULL,
    longitude DOUBLE PRECISION NOT NULL,
    device_id VARCHAR(64) NOT NULL,
    device_type VARCHAR(32) NOT NULL,
    ip_address VARCHAR(45) NOT NULL,
    payment_method VARCHAR(32) NOT NULL,
    card_present BOOLEAN DEFAULT FALSE,
    is_international BOOLEAN DEFAULT FALSE,
    previous_transaction_timestamp TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS features (
    id BIGSERIAL PRIMARY KEY,
    transaction_id VARCHAR(64) UNIQUE NOT NULL REFERENCES transactions(transaction_id) ON DELETE CASCADE,
    account_id VARCHAR(64) NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    transaction_count_1m INT NOT NULL,
    transaction_count_5m INT NOT NULL,
    transaction_amount_sum_5m NUMERIC(12, 2) NOT NULL,
    transaction_amount_avg_5m NUMERIC(12, 2) NOT NULL,
    transaction_amount_std_5m NUMERIC(12, 2) NOT NULL,
    max_transaction_amount_5m NUMERIC(12, 2) NOT NULL,
    unique_merchants_10m INT NOT NULL,
    unique_countries_30m INT NOT NULL,
    unique_devices_30m INT NOT NULL,
    international_transaction_count INT NOT NULL,
    time_since_previous_transaction DOUBLE PRECISION NOT NULL,
    distance_from_previous_transaction DOUBLE PRECISION NOT NULL,
    geo_velocity_kmh DOUBLE PRECISION NOT NULL,
    amount_z_score DOUBLE PRECISION NOT NULL,
    user_amount_deviation DOUBLE PRECISION NOT NULL,
    velocity_score DOUBLE PRECISION NOT NULL,
    merchant_risk_score DOUBLE PRECISION NOT NULL,
    device_change_flag INT NOT NULL,
    country_change_flag INT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS predictions (
    id BIGSERIAL PRIMARY KEY,
    transaction_id VARCHAR(64) UNIQUE NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    account_id VARCHAR(64) NOT NULL,
    amount NUMERIC(12, 2) NOT NULL,
    merchant_id VARCHAR(64) NOT NULL,
    country VARCHAR(8) NOT NULL,
    fraud_probability DOUBLE PRECISION NOT NULL,
    risk_score DOUBLE PRECISION NOT NULL,
    decision VARCHAR(32) NOT NULL,
    model_version VARCHAR(64) NOT NULL,
    latency_ms DOUBLE PRECISION NOT NULL,
    reason_codes JSONB DEFAULT '[]'::jsonb,
    feature_contributions JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS fraud_alerts (
    id BIGSERIAL PRIMARY KEY,
    alert_id VARCHAR(64) UNIQUE NOT NULL,
    transaction_id VARCHAR(64) UNIQUE NOT NULL REFERENCES predictions(transaction_id) ON DELETE CASCADE,
    account_id VARCHAR(64) NOT NULL,
    amount NUMERIC(12, 2) NOT NULL,
    severity VARCHAR(16) NOT NULL,
    risk_score DOUBLE PRECISION NOT NULL,
    fraud_probability DOUBLE PRECISION NOT NULL,
    reason_codes JSONB DEFAULT '[]'::jsonb,
    status VARCHAR(32) DEFAULT 'OPEN',
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS model_versions (
    id SERIAL PRIMARY KEY,
    model_version VARCHAR(64) UNIQUE NOT NULL,
    algorithm VARCHAR(64) NOT NULL,
    training_timestamp TIMESTAMPTZ NOT NULL,
    dataset_rows INT NOT NULL,
    fraud_threshold DOUBLE PRECISION NOT NULL,
    metrics JSONB NOT NULL,
    model_path VARCHAR(256) NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS system_metrics (
    id BIGSERIAL PRIMARY KEY,
    timestamp TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    throughput_events_per_sec DOUBLE PRECISION NOT NULL,
    average_latency_ms DOUBLE PRECISION NOT NULL,
    p95_latency_ms DOUBLE PRECISION NOT NULL,
    p99_latency_ms DOUBLE PRECISION NOT NULL,
    fraud_count INT NOT NULL,
    total_events INT NOT NULL
);

CREATE TABLE IF NOT EXISTS feature_statistics (
    id BIGSERIAL PRIMARY KEY,
    timestamp TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    feature_name VARCHAR(64) NOT NULL,
    mean DOUBLE PRECISION NOT NULL,
    std DOUBLE PRECISION NOT NULL,
    min_val DOUBLE PRECISION NOT NULL,
    max_val DOUBLE PRECISION NOT NULL,
    psi_drift_score DOUBLE PRECISION DEFAULT 0.0
);

-- ==============================================================================
-- INDEXES FOR LOW-LATENCY FILTERING & ANALYTICS
-- ==============================================================================
CREATE INDEX IF NOT EXISTS idx_transactions_account_ts ON transactions(account_id, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_predictions_account_id ON predictions(account_id);
CREATE INDEX IF NOT EXISTS idx_predictions_timestamp ON predictions(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_predictions_decision ON predictions(decision);
CREATE INDEX IF NOT EXISTS idx_fraud_alerts_severity ON fraud_alerts(severity);
CREATE INDEX IF NOT EXISTS idx_fraud_alerts_status ON fraud_alerts(status);
CREATE INDEX IF NOT EXISTS idx_fraud_alerts_created_at ON fraud_alerts(created_at DESC);
