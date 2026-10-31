# ADR 004: Selection of PostgreSQL for Transaction Ledger & Ground Truth Audit Trail

## Context & Problem Statement
A production fraud engine requires a persistent storage system for transactions, predictions, investigator alert triage workflows, and delayed ground-truth labels. The storage layer must provide strict ACID guarantees for state transitions (e.g. alert status changes, model promotions), enforce unique constraints to prevent double-charging or duplicate alerts, support multi-index analytical queries for analyst dashboards, and integrate cleanly with existing enterprise reporting tools.

## Decision
We selected **PostgreSQL 16+** as the primary relational database and audit store.

## Key Technical Rationale
1. **ACID Guarantees & Transaction Isolation**:
   Financial ledger operations and fraud adjudication require strict consistency. When an analyst claims an alert or records delayed ground truth (`CONFIRMED_FRAUD` vs `FALSE_POSITIVE`), read-committed and serializable transaction isolation prevents race conditions between parallel analysts.
2. **Deterministic Idempotency Enforcement**:
   PostgreSQL enforces relational uniqueness via unique constraints and primary keys:
   - `transactions(transaction_id)` PRIMARY KEY
   - `idempotency_keys(key)` PRIMARY KEY with TTL expiration
   - `predictions(prediction_id, transaction_id)` UNIQUE
   Any re-delivered Kafka event or retried API request triggers `ON CONFLICT DO NOTHING`, guaranteeing idempotency at the database engine level.
3. **Relational Join Capabilities for Investigation Triage**:
   Analyst workflows require multi-table joins between transactions, historical customer behavior profiles, merchant fraud risk aggregates, model scoring predictions, and analyst annotations. Relational SQL queries provide sub-10ms response times for operational views.
4. **JSONB Support for Semi-Structured Rule Violations**:
   The Risk Decision Engine outputs dynamic lists of triggered rule violations, severity weights, and Shapley explanation dictionaries. PostgreSQL's native `JSONB` data type allows indexed storage of these unstructured payloads within structured transaction rows without schema bloat.
5. **Universal Tooling & Local Parity**:
   PostgreSQL is universally supported in enterprise infrastructure (AWS RDS, GCP Cloud SQL, Kubernetes Helm/Operator). In local developer environments, Aegis uses SQLite as an automated zero-config fallback with automatic column migration.

## Tradeoffs & Considered Alternatives
- **MongoDB / NoSQL Document Stores**: Provide flexible schemas, but lack strict multi-document ACID transactions across audit tables, require custom deduplication locks, and perform poorly on complex analytical joins between profiles and ground-truth metrics.
- **Cassandra / ScyllaDB**: Excellent write scalability for massive event logs, but severely limited secondary indexing and absence of relational joins make analyst triage querying complex and expensive.

