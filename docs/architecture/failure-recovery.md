# Fault Tolerance, Self-Healing & Disaster Recovery

This document describes the failure modes, automated recovery behaviors, and data resilience guarantees across all Aegis subsystems.

```mermaid
sequenceDiagram
    autonumber
    participant Client as Payment Client
    participant Ingress as FastAPI Gateway
    participant DLQ as Dead Letter Queue
    participant Kafka as Kafka Broker (KRaft)
    participant Worker as Stream Scoring Pod
    participant Redis as Redis Cache
    participant DB as PostgreSQL
    participant SOC as SOC Analyst / Alerts

    Note over Client, DB: Failure Mode 1: Malformed Invariant / Poison Pill
    Client->>Ingress: POST /api/v1/transactions (negative amount, invalid lat/lon)
    Ingress->>Ingress: Data Quality Validation Fails
    Ingress->>DLQ: Route to transactions.dlq (with error payload)
    Ingress-->>Client: 422 Unprocessable Entity (with invariant failure details)
    Note over DLQ: Poison pill isolated; main pipeline unaffected

    Note over Client, DB: Failure Mode 2: Stream Worker Crash
    Worker->>Kafka: Poll micro-batch (Partition 2)
    Worker->>Worker: Unhandled exception / Node Out-of-Memory
    Note over Worker: Worker Pod crashes & restarts via K8s Liveness Probe
    Kafka->>Kafka: Detect heartbeat loss; trigger CooperativeStickyAssignor
    Kafka->>Worker: Reassign Partition 2 to surviving Worker Pod
    Worker->>Kafka: Read from last uncommitted offset
    Note over Worker: No events lost; at-least-once processing resumed

    Note over Client, DB: Failure Mode 3: Redis Cache Outage
    Worker->>Redis: GET sliding_window:acc_1001
    Redis-->>Worker: Connection Timeout / ECONNREFUSED
    Note over Worker: Circuit Breaker Trips to Degraded Mode
    Worker->>DB: Fallback query: recent account transactions
    Worker->>Worker: Compute sliding window & proceed with scoring
    Note over Worker: Ingestion continues with fallback latency (~5ms)

    Note over Client, DB: Failure Mode 4: Network Replay / Duplicate Transaction
    Client->>Ingress: Retry POST with identical Idempotency-Key
    Ingress->>DB: Check idempotency_keys table
    DB-->>Ingress: Existing completed record found
    Ingress-->>Client: 200 OK (X-Idempotent-Replay: true, cached decision)
    Note over DB: No duplicate ledger row, no distorted velocity
```

## Failure Recovery Matrix

| Component | Failure Trigger | Recovery Mechanism | Data Loss Window | User Impact |
|:---|:---|:---|:---|:---|
| **FastAPI Pod** | OOM or Kernel Panic | Kubernetes restarts pod; Ingress redirects traffic to peer pods | **Zero** | None (instant failover) |
| **Kafka Broker** | Broker hardware failure | KRaft leader election promotes in-sync replica partition | **Zero** ($acks=all$) | Transient ~100ms producer retry |
| **Scoring Worker** | Worker crash during batch | Cooperative consumer rebalance; uncommitted offset re-polled | **Zero** (Idempotent DB writes) | < 1 sec consumer lag blip |
| **Redis Cache** | Process crash / eviction | Transparent fallback to PostgreSQL window queries | **Zero** | Latency increases from 0.5ms to 5ms |
| **PostgreSQL** | Primary node failover | StatefulSet PVC remounts or streaming replica promoted | **Zero** (WAL durability) | Brief write pause (~5s) |
| **Poison Pill Payload** | Corrupted JSON / schema breach | Intercepted by Data Quality filter and dumped to DLQ | **Zero** | Immediate 422 HTTP response to client |

