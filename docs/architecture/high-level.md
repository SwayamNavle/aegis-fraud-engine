# High-Level System Architecture

This document describes the end-to-end architecture of **Aegis — Distributed Event-Streaming & Real-Time Fraud Engine**.

```mermaid
flowchart TD
    subgraph INGESTION["1. Ingestion Layer"]
        TG["Transaction Generator / Client"] -->|"HTTP POST / Idempotency-Key"| API["FastAPI Ingestion Gateway"]
        API -->|"Validate Schema & Invariants"| DQ["Data Quality Filter"]
        DQ -->|"Malformed / Corrupt"| DLQ["Dead Letter Queue (transactions.dlq)"]
        DQ -->|"Valid Payload"| KP["Kafka Producer (acks=all)"]
    end

    subgraph BROKER["2. Distributed Event Backbone"]
        KP -->|"Partition by account_id"| KT["Kafka Topic: transactions"]
        KT -->|"Consumer Group"| SPARK["PySpark Structured Streaming"]
        KT -->|"Consumer Group"| WORKER["Streaming Consumer Workers"]
    end

    subgraph FEATURES["3. Unified Feature Store"]
        SPARK -->|"1m, 5m, 10m, 30m Windows"| WF["Sliding Window State Store"]
        WORKER -->|"Point-in-Time & Kinematics"| KIN["Haversine & Geo-Velocity Engine"]
        WF --> FS["Online Feature Vector (20 Features)"]
        KIN --> FS
        REDIS[("Redis Hot Feature Cache")] <-->|"Sub-ms Feature Lookup"| FS
    end

    subgraph RISK_ENGINE["4. Risk Decision Engine"]
        FS -->|"20 Feature Array"| XGB["XGBoost Booster (C++ Runtime)"]
        XGB -->|"Fraud Probability (0.0 - 1.0)"| RDE["Multi-Factor Decision Engine"]
        
        FS -->|"Event Metadata"| RE["Deterministic Rule Engine (8 Rules)"]
        RE -->|"Rule Violations & Severity"| RDE
        
        CP[("Customer Behavioral Profiles")] -->|"Normal Spend & Baselines"| RDE
        MP[("Merchant Profiles")] -->|"Chargeback Ratio & Risk"| RDE
        
        RDE -->|"0 - 100 Risk Score"| DECISION["Business Decision: APPROVE / REVIEW / DECLINE"]
        XGB -.->|"Shapley Contributions"| SHAP["TreeSHAP Explainability"]
    end

    subgraph STORAGE_MONITORING["5. Persistence & Observability"]
        DECISION -->|"Audit Ledger"| PG[("PostgreSQL 16")]
        SHAP -->|"Explanation Vector"| PG
        DECISION -->|"Alert Event (REVIEW / DECLINE)"| WS["WebSocket Hub (/ws/alerts)"]
        DECISION -->|"Live Feed"| WS_TXN["WebSocket Hub (/ws/transactions)"]
        
        API -.->|"Export /metrics"| PROM["Prometheus"]
        PROM --> GRAF["Grafana Dashboards"]
    end

    subgraph PRESENTATION["6. Operator & Analyst UI"]
        WS --> UI["React 18 / TypeScript Dashboard"]
        WS_TXN --> UI
        PG <-->|"REST API Queries"| UI
    end
```

## Data Lifecycle Summary
1. **Generation & Verification**: Transactions are validated against banking invariants (bounds, coordinates, currencies). Invalid transactions route to the Dead-Letter Queue (DLQ).
2. **Log Partitioning**: Valid transactions are written to Kafka partitioned by `account_id`, guaranteeing chronological ordering per customer.
3. **Stateful Feature Extraction**: Streaming consumers calculate sliding temporal aggregations (1m, 5m, 10m, 30m) and kinematic distance metrics (Haversine speed in km/h).
4. **Scoring & Explainability**: The XGBoost booster computes the statistical probability of fraud ($p_{\text{fraud}}$), while the Rule Engine evaluates 8 deterministic security rules.
5. **Multi-Factor Decisioning**: The Risk Decision Engine blends ML probability, rule penalties, customer behavioral profiles, and merchant risk into a calibrated 0–100 risk score and business action (`APPROVE`, `REVIEW`, `DECLINE`).
6. **Audit & Triage**: Predictions, features, and TreeSHAP attributions are persisted to PostgreSQL and broadcast via WebSockets to the SOC triage dashboard.

