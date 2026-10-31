# Aegis System Audit: Current State Architecture & Capability Analysis

**Audit Date:** October 30, 2026  
**Auditor:** Aegis Principal Distributed Systems & ML Engineer  
**Scope:** In-place architectural and codebase audit of `/Users/swayamnavle/Aegis- Distributed Event-Streaming & Real-Time Fraud Engine`

---

## 1. Current Architecture
The current Aegis engine is an end-to-end distributed stream-processing and real-time fraud detection engine consisting of:
- **Event Producer**: Synthetic event generator producing realistic multi-pattern transactions (velocity attacks, geographic impossibility, amount anomalies, emulator device spoofing, foreign remittance spikes, benign shopping bursts).
- **Streaming Ingestion**: Apache Kafka in KRaft mode (KRaft broker/controller on port 9092) with account-based partitioning (`account_id`).
- **Stream Processing**: PySpark Structured Streaming with 10-minute watermarking and 5-minute sliding windows (1-minute slide), backed by an in-memory streaming fallback (`run_standalone_streaming`).
- **ML Fraud Scoring**: Serialized XGBoost binary classifier (`xgb_fraud_model.json`) with sub-2ms prediction latency, calibrated risk scoring, and heuristic reason-code derivation.
- **Persistence Layer**: PostgreSQL 16 ACID database with unique constraints on `transaction_id` for idempotent processing, plus SQLite compatibility for local testing.
- **API Gateway**: FastAPI service with CORS, Prometheus instrumentation, asynchronous SQLAlchemy connection pooling, and REST + WebSocket endpoints.
- **Frontend Dashboard**: React + TypeScript single-page application built with Vite and Tailwind CSS ("Aegis Command Center").
- **Monitoring**: Prometheus scraper on `/metrics` and Grafana with pre-configured dashboard JSON.
- **Containerization & Orchestration**: Multi-stage Dockerfiles, Docker Compose, and Kubernetes manifests under `k8s/`.

```
[Synthetic Producer]
         │ (JSON over Kafka)
         ▼
[Kafka Broker: transactions.raw] (partitioned by account_id)
         │
         ▼
[PySpark Structured Streaming] ──(dead-letter)──► [transactions.dead_letter]
         │ (5m sliding window, 1m slide, 10m watermark)
         ▼
[Online Feature Store]
         │ (20 engineered features)
         ▼
[XGBoost Predictor] ──► [Risk Score & Heuristic Reason Codes]
         │
         ▼
[PostgreSQL Database] (ACID Idempotent Tables)
         │
         ├──────────────────────────────┐
         ▼                              ▼
  [FastAPI Gateway]            [Prometheus & Grafana]
         │                              │
         ▼ (WebSockets / REST)          ▼
[React Aegis Command Center]   [Operational Dashboards]
```

---

## 2. Existing Services

| Service Name | Technology | Location | Port | Functionality |
| :--- | :--- | :--- | :--- | :--- |
| **Kafka** | Apache Kafka 3.5 (KRaft mode) | Docker container (`bashj79/kafka-kraft`) | 9092 | Event broker, topic partitioning by `account_id` |
| **PostgreSQL** | PostgreSQL 16 Alpine | `database/init.sql` / Docker container | 5432 | Relational ACID persistence, unique transaction constraints |
| **Redis** | Redis 7 Alpine | Docker container (`redis:7-alpine`) | 6379 | In-memory feature cache & deduplication |
| **Scoring Microservice** | Python 3.11/3.13, FastAPI, XGBoost | `services/scoring/` | 8001 | Standalone model inference microservice (`POST /predict`) |
| **API Gateway** | FastAPI, SQLAlchemy, Uvicorn | `services/api/` | 8000 | Central REST gateway, WebSocket `/ws/transactions`, Prometheus |
| **Spark Streaming** | PySpark 3.5 Structured Streaming | `streaming/spark/` | - | Windowed stream aggregations and feature engineering |
| **Producer** | Python asyncio, Pydantic | `streaming/producer/` | - | Multi-pattern financial transaction stream generator |
| **Frontend UI** | React 18, Vite, TypeScript, Tailwind | `frontend/` | 3000 / 8000 | Real-time cyber-defense dashboard ("Aegis Command Center") |
| **Prometheus** | Prometheus v2.45 | `monitoring/prometheus/` | 9090 | Telemetry scraper pulling `/metrics` every 5 seconds |
| **Grafana** | Grafana 10.0 | `monitoring/grafana/` | 3001 | Visualization dashboard with pre-provisioned datasource |

---

## 3. Current Data Flow
1. **Generation**: `SyntheticTransactionGenerator` emits transactions with user profiles, geolocations, devices, amounts, and optional ground-truth `label`.
2. **Sanitization**: Ground-truth `label` is stripped via `to_production_dict()` before entering the streaming/scoring pipeline.
3. **Ingestion**: Transaction is published to Kafka topic `transactions.raw` using `account_id` as the partition key.
4. **Windowing & Feature Generation**: PySpark (or the in-memory fallback `OnlineFeatureStore`) extracts 20 features across 1m/5m/10m/30m sliding windows.
5. **Inference**: Features are passed to `FraudPredictor.predict()`. XGBoost outputs fraud probability; a 0–100 risk score and heuristic reason codes are calculated.
6. **Idempotency & Persistence**: `score_and_persist` checks PostgreSQL for existing `transaction_id`. If unseen, records are committed to `transactions`, `features`, `predictions`, and `fraud_alerts`.
7. **Broadcast & Metrics**: The API broadcast loop dispatches `TRANSACTION_EVENT` and alerts over `/ws/transactions` to the React dashboard. Prometheus increments HTTP request counters and observes latency histograms.

---

## 4. Existing ML Pipeline
- **Dataset Generation**: `scripts/generate_demo_data.py` creates 50,000 synthetic transactions sorted chronologically.
- **Feature Engineering**: `ml/training/feature_engineering.py` extracts 20 features:
  - Sliding counts and sums: `transaction_count_1m`, `transaction_count_5m`, `transaction_amount_sum_5m`, `transaction_amount_avg_5m`, `transaction_amount_std_5m`, `max_transaction_amount_5m`
  - Cardinality & state metrics: `unique_merchants_10m`, `unique_countries_30m`, `unique_devices_30m`, `international_transaction_count`
  - Kinematics & deviations: `time_since_previous_transaction`, `distance_from_previous_transaction`, `geo_velocity_kmh`, `amount_z_score`, `user_amount_deviation`, `velocity_score`, `merchant_risk_score`, `device_change_flag`, `country_change_flag`, `is_international`
- **Training Split**: Strictly chronological 70% Train, 15% Validation, 15% Test.
- **Model Comparison**: Trains and evaluates:
  1. Baseline XGBoost (unweighted)
  2. Class-Weighted XGBoost (`scale_pos_weight = N_neg / N_pos`)
  3. Balanced Synthetic Resampled XGBoost (SMOTE-style minority interpolation)
- **Artifacts Saved**: `ml/models/xgb_fraud_model.json`, `ml/artifacts/metrics.json`, `ml/artifacts/confusion_matrix.json`, `ml/artifacts/feature_importance.json`, `ml/artifacts/training_metadata.json`, `ml/artifacts/feature_schema.json`.

---

## 5. Existing Kafka Topics
- `transactions.raw`: Ingestion topic, partitioned by `account_id`.
- `transactions.features`: Output topic for calculated feature vectors.
- `transactions.predictions`: Scored prediction output.
- `transactions.alerts`: Dedicated topic for triggered high-risk alerts.
- `transactions.dead_letter`: Dead-letter queue for schema-invalid or malformed records.

---

## 6. Existing Database Tables
- `transactions`: Raw transaction metadata (amounts, geolocations, devices, payment methods).
- `features`: 20 windowed engineered features for each transaction.
- `predictions`: Scored predictions (fraud probability, risk score, decision, model version, latency, reason codes, feature contributions).
- `fraud_alerts`: High/critical risk alerts requiring analyst triage (`OPEN`, `REVIEWED`, `DISMISSED`, `ESCALATED`).
- `model_versions`: Model registry recording algorithm, training timestamp, dataset size, threshold, metrics, and active state.
- `system_metrics`: Historical time-series of throughput and latency percentiles.
- `feature_statistics`: Distribution statistics for Population Stability Index (PSI) drift monitoring.

---

## 7. Existing APIs

| Endpoint | Method | Description |
| :--- | :--- | :--- |
| `/health` | GET | Service liveness & readiness check |
| `/metrics` | GET | Prometheus scrape endpoint (standard format) |
| `/transactions` | GET | Paginated transaction listing with decision, account, and risk filtering |
| `/transactions/{id}` | GET | Full transaction dossier (raw payload, feature vector, prediction, reason codes) |
| `/transactions/score_and_persist` | POST | ACID idempotent transaction scoring and persistence |
| `/alerts` | GET | Paginated fraud alerts filtered by status and severity |
| `/alerts/{id}` | PATCH | Update alert workflow status (`REVIEWED`, `DISMISSED`, `ESCALATED`) |
| `/stats` | GET | Live operational KPIs (total processed, fraud count, latency, current TPS) |
| `/stats/throughput` | GET | Recent throughput and latency time-series for charts |
| `/stats/fraud` | GET | Fraud breakdown by decision, risk distribution, and top countries |
| `/model/info` | GET | Active model metadata, threshold, and feature schema |
| `/monitoring/drift` | GET | Population Stability Index (PSI) feature drift metrics |
| `/system/status` | GET | Infrastructure status (Kafka, Spark, Scoring, Postgres, Prometheus) |
| `/predict` | POST | Inline prediction endpoint for raw transaction or feature vector |
| `/ws/transactions` | WebSocket | Real-time duplex streaming feed of transactions and alerts |

---

## 8. Existing Frontend Pages & Components
- **KPICards**: Live transactions processed, fraud detected, fraud rate percentage, average latency, active alerts, current TPS.
- **SystemHealth**: Cluster mesh status indicators for Kafka, Spark, XGBoost, Postgres, Prometheus.
- **ChartsView**: 4 SVG vector charts (TPS throughput timeline, Decision distribution, Risk score histogram, Top risk countries).
- **LiveFeed**: Real-time ticker table displaying transaction ID, timestamp, user, merchant, amount, location, risk score, decision badge, and detail modal trigger.
- **AlertsPanel**: SOC triage queue showing severity badges (`CRITICAL`, `HIGH`, `MEDIUM`), reason codes, risk scores, and quick action buttons.
- **TransactionModal**: Deep inspection modal showing raw transaction metadata, 20 engineered feature values, and top feature contributions.

---

## 9. Existing Docker Services
- `kafka`: Apache Kafka in KRaft mode with combined log directory and healthcheck.
- `postgres`: PostgreSQL 16 Alpine with volume mounts and automated `init.sql` schema migration.
- `redis`: Redis 7 Alpine hot cache with ping healthcheck.
- `scoring`: Standalone FastAPI XGBoost microservice container.
- `api`: Central FastAPI backend gateway container.
- `spark`: Spark 3.5 streaming worker container with checkpoint volume mount.
- `producer`: Continuous transaction generator container.
- `frontend`: Multi-stage React Vite build served through Nginx Alpine.
- `prometheus`: Prometheus container with scraping configuration.
- `grafana`: Grafana container with pre-configured dashboard and datasource provisioning.

---

## 10. Existing Kubernetes Resources
Manifests defined in `k8s/`:
- `namespace.yaml`: Dedicated `aegis` namespace.
- `kafka/kafka.yaml`: StatefulSet / Deployment + Service for KRaft broker.
- `postgres/postgres.yaml`: PersistentVolumeClaim + Deployment + Service.
- `spark/spark.yaml`: Spark streaming worker deployment with checkpoint PVC.
- `scoring/scoring.yaml`: Scoring microservice deployment + HorizontalPodAutoscaler (HPA).
- `api/api.yaml`: API gateway deployment + Service + HPA.
- `frontend/frontend.yaml`: Nginx frontend deployment + Service.
- `prometheus/prometheus.yaml`: Prometheus deployment + ConfigMap + Service.
- `grafana/grafana.yaml`: Grafana deployment + Service.
- `ingress.yaml`: Ingress controller routing `/api` and `/` paths.

---

## 11. Existing Monitoring
- **Prometheus Scraper**: Scrapes `/metrics` every 5 seconds.
- **Custom Metrics**:
  - `aegis_http_requests_total`: Counter by method, endpoint, and status code.
  - `aegis_http_request_duration_seconds`: Histogram of request latencies.
- **PSI Drift Calculator**: `calculate_psi` in `monitoring.py` computing Population Stability Index against baseline distributions with `<0.10`, `0.10-0.25`, and `>0.25` alerting thresholds.
- **Grafana Dashboard**: `aegis_dashboard.json` pre-configured for throughput, latency, fraud counts, and decision distributions.

---

## 12. Existing Tests
- `tests/unit/test_producer.py`: Validates legitimate event generation, fraud event kinematics, and burst ratio controls.
- `tests/unit/test_features.py`: Tests Haversine distance, sliding window counts, and velocity formulas.
- `tests/unit/test_predictor.py`: Validates deterministic reason codes and 0-100 risk score calibration.
- `tests/unit/test_idempotency.py`: Validates that duplicate transaction IDs return existing predictions without duplicate database records.
- `tests/integration/test_api_endpoints.py`: Tests `/health`, `/metrics`, `/stats`, `/stats/throughput`, `/monitoring/drift`, `/system/status`, and `/alerts`.
- `tests/integration/test_failure_scenarios.py`: Tests 404 for missing transactions, 400 for invalid alert status updates, and 400 for malformed scoring payloads.

---

## 13. Missing Capabilities (Identified Gaps)

1. **Business Decision Separation**: Currently, the model decision is `LEGITIMATE`, `SUSPICIOUS`, or `FRAUD`. The prompt requires realistic fintech business decisions: `APPROVE`, `REVIEW`, `DECLINE`, separating the pure ML risk score from the business rule layer.
2. **Dedicated Fraud Rule Engine**: Reason codes are currently derived heuristically inside `predictor.py`. A structured rule engine returning structured violation objects (`rule_id`, `triggered`, `severity`, `message`) with configurable parameters is required.
3. **Dedicated Risk Engine (`risk_engine/`)**: A dedicated module combining ML probability, rule violations, customer risk profile, merchant risk profile, and transaction amount into a calibrated 0–100 risk score, risk level (`LOW`, `MEDIUM`, `HIGH`, `CRITICAL`), and business decision (`APPROVE`, `REVIEW`, `DECLINE`).
4. **Customer & Merchant Risk Profiling**: Database entities and profiling logic to track historical customer behavior (normal spend, device history, country history, customer risk score) and merchant statistics (volume, fraud count, fraud rate, merchant risk score).
5. **Feature Store Architecture**: Formal separation of features into `features/feature_definitions.py`, `features/offline_features.py`, and `features/online_features.py` to prevent train-serve skew.
6. **Model Registry & Dynamic Rollback**: Model version lifecycle management (`CANDIDATE`, `STAGING`, `PRODUCTION`, `ARCHIVED`) and API endpoints for model promotion and rollback (`GET /models`, `POST /models/{version}/promote`, `POST /models/{version}/rollback`).
7. **Data Quality Layer & DLQ Routing**: Formal pre-scoring data quality validator tracking `invalid_transactions_total`, `data_quality_errors_total`, `duplicate_transactions_total` and routing malformed events to `transactions.dlq`.
8. **Delayed Ground Truth & Investigation Workflow**: Workflow allowing fraud analysts to triage alerts (`NEW` -> `UNDER_REVIEW` -> `CONFIRMED_FRAUD` / `FALSE_POSITIVE`), record analyst notes and reviewer identity, and reconcile delayed ground truth for real-world precision/recall tracking.
9. **Real-time Alert WebSocket (`/ws/alerts`)**: Dedicated WebSocket endpoint broadcasting high-priority fraud alerts immediately to analysts.
10. **SHAP Feature Explainability**: TreeSHAP integration for explainable feature attribution on high-risk transactions.
11. **Comprehensive Dashboard Views**: Expansion of the React dashboard to include dedicated views for:
    - Overview (Command Center)
    - Live Transactions
    - Fraud Alerts & Investigation Triage
    - Customer Profiles
    - Merchant Profiles
    - Model Governance & Rollback
    - System Health & Observability
12. **End-to-End Correlation & Latency Breakdown**: Ingestion of `correlation_id` across all events with latency timestamp tracking (ingestion, feature, scoring, DB, API end-to-end).
13. **Security & Role-Based Access Control (RBAC)**: Authentication layer with `ADMIN`, `ANALYST`, and `VIEWER` roles, securing model management and investigation endpoints.
14. **ML Baseline Comparison**: Empirical comparison between Logistic Regression, Random Forest, and XGBoost on identical splits.
15. **Failure & Chaos Scenarios Testing**: Automated tests for Kafka consumer failure, Spark checkpoint restart, duplicate events, DLQ routing, DB retry recovery, and scoring pod failure.
16. **Architecture Decision Records (ADRs)**: Formal ADRs (`docs/adr/001` through `007`) documenting technical decisions.

---

## 14. Recommended Upgrade Plan
The upgrade should proceed in 10 sequential, non-breaking phases:
1. **Architecture & Scaffolding**: Add `docs/upgrade-plan.md` and feature store definitions.
2. **Rule & Risk Decision Engine**: Create `risk_engine/` implementing configurable rules, customer/merchant profiling, and `APPROVE / REVIEW / DECLINE` logic.
3. **Customer & Merchant Profiling**: Add DB models, profiling logic, and API endpoints.
4. **Model Registry & Rollback**: Implement model governance endpoints and state transitions.
5. **Data Quality & DLQ**: Implement pre-scoring schema validation and error counters.
6. **Delayed Ground Truth & Analyst Workflow**: Expand alert status lifecycle and ground-truth reconciliation.
7. **Explainability & Observability**: Implement TreeSHAP explainability, `correlation_id` propagation, and end-to-end latency tracking.
8. **React Command Center Expansion**: Upgrade the dashboard to support multi-view navigation (Overview, Live Feed, Alerts Triage, Customers, Merchants, Models, System Health).
9. **Baseline Comparison & Automated Testing**: Add Logistic Regression and Random Forest comparisons, automated failure tests, and performance benchmark runs.
10. **Documentation & Final Verification**: Add ADRs, architecture diagrams, `docs/final-report.md`, and updated README with verified metrics.

