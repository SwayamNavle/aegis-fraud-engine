# ADR 006: End-to-End Idempotency & Deduplication Strategy

## Context & Problem Statement
In distributed payment streaming architectures, network partitions, TCP retransmissions, Kafka consumer rebalances, and client retries inevitably cause duplicate event delivery ("at-least-once" semantics). Without strict idempotency, duplicate events would inflate account velocity features (triggering false positive fraud alerts), produce duplicate database records, and cause inaccurate financial exposure calculations.

## Decision
We implemented a **multi-tiered idempotency strategy** combining header-level idempotency tokens, atomic database constraints, and Kafka transaction producer semantics.

## Architecture & Enforcement Layers

```text
Incoming Request / Kafka Event
               │
               ▼
   [Layer 1: Memory / Cache Check]
      Check Redis / In-Memory Set
      Key: aegis:idempotency:{key}
      (TTL: 3600 seconds)
               │
      ┌────────┴────────┐
      ▼ (Exists)        ▼ (New)
 Return Cached     [Layer 2: Database Atomic Insert]
 Response (200)    INSERT INTO idempotency_keys
                   ON CONFLICT DO NOTHING;
                        │
               ┌────────┴────────┐
               ▼ (Duplicate)     ▼ (Inserted)
          Skip Scoring       Execute Risk Engine
          Return 200/409     & Record Prediction
```

### 1. Ingestion Layer (FastAPI & Kafka Producer)
- Every transaction includes a canonical `transaction_id` (UUIDv4) and an optional `Idempotency-Key` HTTP header.
- If an HTTP client submits a duplicate `Idempotency-Key` within 1 hour:
  - Aegis inspects the idempotency table.
  - If a prior execution completed, the exact prior response payload is returned immediately with `X-Idempotent-Replay: true`, bypassing re-scoring.
  - If a prior execution is still in-flight, a `409 Conflict` (Concurrent Request in Flight) is returned.

### 2. Stream Consumer Layer (Kafka)
- Kafka producers use `enable.idempotence=true` and `acks=all`, ensuring broker-level deduplication across producer retries.
- Consumer workers track processed `transaction_id`s in a sliding window LRU cache (`OrderedDict` or Redis `SETNX`) before executing feature extraction and model scoring.
- When duplicates arrive (e.g. during a consumer group rebalance after worker crash), the worker drops the duplicate and increments the `aegis_duplicate_transactions_total` Prometheus counter.

### 3. Database Layer (PostgreSQL)
- The `transactions` table enforces `PRIMARY KEY (transaction_id)`.
- The `predictions` table enforces `UNIQUE (transaction_id)`.
- The `idempotency_keys` table enforces `PRIMARY KEY (key)`.
- Inserts use explicit conflict clauses:
  ```sql
  INSERT INTO transactions (transaction_id, account_id, amount, timestamp, ...)
  VALUES (...)
  ON CONFLICT (transaction_id) DO NOTHING;
  ```
- This guarantees that even if concurrent race conditions bypass memory caches, the database engine guarantees absolute ledger uniqueness.

## Verification & Recovery
- Unit and integration tests in `tests/integration/test_failure_scenarios.py` (`test_idempotent_duplicate_processing`) assert that sending the exact same transaction payload 5 consecutive times produces exactly 1 database record, exactly 1 prediction entry, zero duplicate alerts, and increments the duplicate Prometheus metric.

