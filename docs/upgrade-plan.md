# Aegis Upgrade Plan: Production-Grade Fintech Fraud Platform

**Version:** 2.0.0-PROD  
**Target:** In-Place Upgrade of Aegis Event-Streaming & Real-Time Fraud Engine  
**Guiding Principle:** **Extend and enhance existing working components without destructive rewrites or breaking working APIs.**

---

## 1. Target Architecture & Component Mapping

```text
                                     AEGIS PRODUCTION ARCHITECTURE
                                                  │
                                         Payment Transaction
                                                  │
                                                  ▼
                                       Apache Kafka Broker
                                    (transactions.raw / DLQ)
                                                  │
                                                  ▼
                                     PySpark Structured Streaming
                                                  │
                                  ┌───────────────┴───────────────┐
                                  │                               │
                                  ▼                               ▼
                           Online Features                 Event Validation
                     (sliding windows / profiles)         (schema / range checks)
                                  │                               │
                                  ▼                               ▼
                            XGBoost Model                 Dead-Letter Topic
                        (fraud_probability)               (transactions.dlq)
                                  │
                                  ▼
                          Fraud Rule Engine
                     (8 configurable heuristics)
                                  │
                                  ▼
                         Risk Decision Engine
                    (ML + Rules + Customer/Merchant)
                                  │
                           ┌──────┼──────┐
                           ▼      ▼      ▼
                        APPROVE REVIEW DECLINE
                                  │
                                  ▼
                        PostgreSQL 16 Storage
                   (Idempotent ACID Persistence)
                                  │
                   ┌──────────────┴──────────────┐
                   ▼                             ▼
            FastAPI Gateway             Monitoring Mesh
         (REST + /ws/alerts)          (Prometheus / Grafana)
                   │                             │
                   ▼                             ▼
       React Aegis Command Center        Operational Metrics
     (Triage / Profiles / Models)      (Drift / Latency / SLA)
```

### Component Traceability Matrix

| Component | Current State | Target State | Upgrade Action |
| :--- | :--- | :--- | :--- |
| **Transaction Schema** | Pydantic event schema with 20 fields | Added `correlation_id`, currency validation, validation invariants | Extend schema with backward compatibility |
| **Event Validation & DLQ** | Basic schema check in Spark | Explicit data quality validation layer routing bad events to `transactions.dlq` | Add `data_quality.py` validator and metrics |
| **Feature Store** | `ml/training/feature_engineering.py` | Dedicated `features/` module (`feature_definitions.py`, `offline_features.py`, `online_features.py`) | Modularize feature definitions for exact train-serve parity |
| **XGBoost Scoring** | Outputs `LEGITIMATE`, `SUSPICIOUS`, `FRAUD` | Outputs pure `fraud_probability` and feature contributions | Retain model; decouple business decision to Risk Engine |
| **Fraud Rule Engine** | Heuristic reason codes in `predictor.py` | Configurable Rule Engine returning structured violation objects | Create `risk_engine/rule_engine.py` |
| **Risk Decision Engine** | Model threshold cutoff | Multi-factor Risk Engine: ML Score + Rules + Customer + Merchant -> `APPROVE`, `REVIEW`, `DECLINE` | Create `risk_engine/decision_engine.py` |
| **Customer Profiling** | In-memory amount history per account | DB & in-memory customer profile (mean, std, known devices, known countries, risk score) | Add `CustomerProfile` model, store, and APIs |
| **Merchant Profiling** | Static merchant risk weight dictionary | Dynamic merchant profile (volume, fraud count, fraud rate, risk score) | Add `MerchantProfile` model, store, and APIs |
| **Model Registry** | `model_versions` table with single model | Lifecycle statuses (`CANDIDATE`, `STAGING`, `PRODUCTION`, `ARCHIVED`) and rollback API | Add `/models` endpoints and promotion/rollback |
| **Alerts & Investigation** | Basic alert listing & status patch | Full analyst investigation workflow (`NEW`, `UNDER_REVIEW`, `CONFIRMED_FRAUD`, `FALSE_POSITIVE`) with delayed ground truth | Expand `fraud_alerts` and add reconciliation |
| **Explainability** | Weight-magnitude heuristic | TreeSHAP integration for feature attribution on flagged transactions | Add `services/scoring/explainability.py` with SHAP |
| **Real-Time WebSocket** | `/ws/transactions` | Added `/ws/alerts` for immediate critical alert broadcasting | Add dedicated alerts broadcast channel |
| **Dashboard UI** | Live feed + KPIs + 4 charts + Modal | Multi-view Command Center (Overview, Transactions, Alerts, Customers, Merchants, Models, Health) | Expand React UI with tabbed views & triage actions |
| **Security & RBAC** | Public API | API Key / JWT header verification with `ADMIN`, `ANALYST`, and `VIEWER` roles | Add lightweight auth middleware |
| **Model Baselines** | XGBoost Baseline vs Weighted vs SMOTE | Added Logistic Regression and Random Forest comparisons | Update training pipeline with baseline comparison |
| **Documentation & ADRs** | General Markdown guides | Formal ADRs (`001` - `007`), comprehensive architecture docs, and `docs/final-report.md` | Create `docs/adr/` and complete reports |

---

## 2. Step-by-Step Implementation Roadmap

### Phase 3: Rule Engine & Decision Architecture
- Implement `risk_engine/rule_engine.py` with 8 configurable deterministic fraud rules:
  1. `HIGH_TRANSACTION_VELOCITY`: Excessive count in 1m / 5m.
  2. `UNUSUAL_AMOUNT`: Amount exceeds customer baseline by >3 standard deviations.
  3. `IMPOSSIBLE_TRAVEL`: Geo-velocity > 600 km/h between successive transactions.
  4. `NEW_DEVICE`: Unrecognized device identifier for established user.
  5. `NEW_COUNTRY`: Unrecognized country for domestic user.
  6. `UNUSUAL_MERCHANT`: High-risk merchant category (crypto, gambling, offshore, wire remittance).
  7. `INTERNATIONAL_SPIKE`: Sudden burst of foreign transactions.
  8. `MULTIPLE_RAPID_TRANSACTIONS`: Inter-transaction interval < 10 seconds.
- Each rule returns a structured evaluation: `{ rule_id, triggered, severity, message, weight }`.

### Phase 4: Risk Decision Engine
- Implement `risk_engine/decision_engine.py`:
  - Combines:
    - XGBoost `fraud_probability` (0.0 – 1.0)
    - Triggered rule weights & severities
    - Customer historical risk score
    - Merchant risk score
    - Transaction monetary value
  - Calculates:
    - `risk_score`: 0 – 100 (Calibrated)
    - `risk_level`: `LOW` (0-30), `MEDIUM` (31-60), `HIGH` (61-80), `CRITICAL` (81-100)
    - `decision`: `APPROVE`, `REVIEW`, `DECLINE`
    - Preserves backward compatibility by mapping `APPROVE -> LEGITIMATE`, `REVIEW -> SUSPICIOUS`, `DECLINE -> FRAUD` where required by existing tests.

### Phase 5: Customer & Merchant Risk Profiling
- Define SQLAlchemy models & database tables:
  - `customer_profiles`: `user_id`, `account_id`, `avg_amount`, `max_amount`, `std_amount`, `txn_count`, `fraud_count`, `known_devices` (JSON), `known_countries` (JSON), `risk_score`.
  - `merchant_profiles`: `merchant_id`, `merchant_name`, `category`, `total_volume`, `txn_count`, `fraud_count`, `fraud_rate`, `risk_score`.
- Expose REST API endpoints:
  - `GET /customers`, `GET /customers/{account_id}`
  - `GET /merchants`, `GET /merchants/{merchant_id}`

### Phase 6: Unified Feature Store
- Create `features/`:
  - `feature_definitions.py`: Single source of truth for the 20 feature names, types, descriptions, and scaling constants.
  - `offline_features.py`: Batch vectorization for training and offline validation.
  - `online_features.py`: Low-latency stateful window extractor for streaming and real-time scoring.
- Ensure `ml/training/train.py`, `streaming/spark/features.py`, and `services/scoring/` all reference this common module.

### Phase 7: Model Registry & Rollback Engine
- Extend `model_versions` table with `status`: `CANDIDATE`, `STAGING`, `PRODUCTION`, `ARCHIVED`.
- Implement model promotion and rollback endpoints:
  - `GET /models`: List all registered model versions.
  - `GET /models/{version}`: Inspect specific version metrics, PR-AUC, threshold, and artifact location.
  - `POST /models/{version}/promote`: Promote candidate/staging model to `PRODUCTION` (atomic demotion of active model to `ARCHIVED`).
  - `POST /models/{version}/rollback`: Roll back production model to a previous verified version.

### Phase 8: Data Quality Layer & Dead-Letter Handling
- Create `services/api/data_quality.py`:
  - Validates missing fields, range bounds, non-negative amounts, ISO-8601 timestamps, valid coordinate boxes (-90..90 lat, -180..180 lon), and non-empty IDs.
  - Tracks Prometheus counters:
    - `aegis_data_quality_errors_total`
    - `aegis_invalid_transactions_total`
    - `aegis_duplicate_transactions_total`
  - Routes failed payloads to Dead-Letter Topic (`transactions.dlq`).

### Phase 9: Delayed Ground Truth & Investigation Workflow
- Enhance `fraud_alerts` with full analyst lifecycle:
  - Statuses: `NEW`, `UNDER_REVIEW`, `CONFIRMED_FRAUD`, `FALSE_POSITIVE`.
  - Record analyst fields: `reviewer_id`, `notes`, `review_timestamp`, `final_ground_truth`.
- Add delayed ground truth reconciliation endpoint:
  - `POST /alerts/{alert_id}/investigate`: Analyst marks investigation outcome.
  - `POST /transactions/{transaction_id}/reconcile`: Binds delayed ground truth label to earlier prediction for live PR-AUC / Precision / Recall tracking.

### Phase 10: Explainability (TreeSHAP) & Correlation Tracking
- Implement `services/scoring/explainability.py`:
  - Uses SHAP `TreeExplainer` on XGBoost model to compute true Shapley values for flagged transactions.
  - Returns signed contributions: e.g., `amount_deviation: +0.42`, `velocity: +0.31`.
- Add `correlation_id` across event schemas:
  - Propagate correlation headers through Kafka, feature store, scoring, and DB.
  - Measure sub-millisecond latencies across pipeline stages: `t_ingest`, `t_features`, `t_model`, `t_db`, `t_e2e`.

### Phase 11: Dedicated Alert WebSocket (`/ws/alerts`)
- Implement `/ws/alerts` for instant broadcast of high-priority and critical fraud alerts.

### Phase 12: React Aegis Command Center Expansion
- Upgrade `frontend/src/` to provide a full multi-view experience:
  1. **Overview View**: Real-time KPI deck, mesh status, throughput timeline, live risk stream.
  2. **Live Feed View**: Real-time transactions table with filter controls and deep inspection modal.
  3. **Alerts & Investigation View**: Analyst triage board with status transitions (`NEW` -> `UNDER_REVIEW` -> `CONFIRMED_FRAUD` / `FALSE_POSITIVE`) and analyst notes.
  4. **Customer Intelligence View**: Customer behavioral dossiers, historical spend curves, and known device matrices.
  5. **Merchant Risk View**: Merchant transaction volume, fraud rate rankings, and risk distribution.
  6. **Model Governance View**: Model registry table, active version status, metrics comparison, and one-click rollback.
  7. **System Health View**: Detailed node telemetry for Kafka, Spark, PostgreSQL, Scoring, API, Prometheus.

### Phase 13: Baseline Model Comparison & Failure Testing
- Expand ML evaluation to train and benchmark:
  1. Logistic Regression (Linear baseline)
  2. Random Forest (Bagging ensemble baseline)
  3. XGBoost (Gradient boosting champion)
- Implement automated failure tests in `tests/integration/test_failure_scenarios.py`:
  - Kafka consumer failure recovery
  - Spark checkpoint restart verification
  - Duplicate event deduplication
  - Malformed payload DLQ diversion
  - Database reconnect resiliency
  - Scoring pod failure recovery

### Phase 14: Documentation, ADRs & Final Report
- Create `docs/adr/001-why-kafka.md` through `docs/adr/007-feature-window-design.md`.
- Create comprehensive architecture guides under `docs/architecture/`.
- Compile `docs/final-report.md` covering all 21 production evaluation dimensions.
- Update `README.md` with verified benchmark results and role-targeted resume bullets.

---

## 3. Backward Compatibility Verification
To ensure zero regressions:
1. `PredictionResult` maintains all existing fields (`transaction_id`, `fraud_probability`, `risk_score`, `decision`, `latency_ms`, `reason_codes`, `feature_contributions`) while adding `business_decision`, `rule_violations`, and `correlation_id`.
2. Existing tests in `tests/` must pass without modification.
3. Database migrations must support both existing PostgreSQL and SQLite test environments.

