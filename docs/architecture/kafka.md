# Kafka Event Streaming Architecture

This document details the Kafka topic topology, partition hashing strategy, consumer groups, and fault-tolerant dead-letter queues.

```mermaid
flowchart TD
    subgraph PRODUCER["Kafka Producers"]
        P1["Payment Gateway Pod 1"]
        P2["Payment Gateway Pod 2"]
        P3["Batch Ingestion Script"]
    end

    subgraph TOPIC_MAIN["Topic: transactions (6 Partitions, RF=1/3)"]
        direction TB
        PART0["Partition 0 (hash(account_id) % 6 == 0)"]
        PART1["Partition 1 (hash(account_id) % 6 == 1)"]
        PART2["Partition 2 (hash(account_id) % 6 == 2)"]
        PART3["Partition 3 (hash(account_id) % 6 == 3)"]
        PART4["Partition 4 (hash(account_id) % 6 == 4)"]
        PART5["Partition 5 (hash(account_id) % 6 == 5)"]
    end

    subgraph CONSUMER_GROUP["Consumer Group: aegis-streaming-consumers"]
        W1["Worker Pod 1 (Assigned: P0, P1)"]
        W2["Worker Pod 2 (Assigned: P2, P3)"]
        W3["Worker Pod 3 (Assigned: P4, P5)"]
    end

    subgraph TOPIC_DLQ["Topic: transactions.dlq (Dead Letter Queue)"]
        DLQ0["Partition 0 (Poison Pills & Malformed JSON)"]
    end

    subgraph DLQ_CONSUMER["DLQ Monitoring Service"]
        DLQ_WORKER["DLQ Auditor & Sentry Alerting"]
    end

    P1 -->|"Key: account_id"| TOPIC_MAIN
    P2 -->|"Key: account_id"| TOPIC_MAIN
    P3 -->|"Key: account_id"| TOPIC_MAIN

    PART0 --> W1
    PART1 --> W1
    PART2 --> W2
    PART3 --> W2
    PART4 --> W3
    PART5 --> W3

    P1 -.->|"Malformed Invariant / Corrupt Schema"| DLQ0
    W1 -.->|"Deserialization / Runtime Panic"| DLQ0
    DLQ0 --> DLQ_WORKER
```

## Partition Hashing Guarantee
- **Partition Key**: Every event published to `transactions` specifies `account_id` as the message key.
- **Strict Ordering**: Because Kafka routes identical keys to the same partition, all transactions for `acc_12345` are sequentially processed in order of publication.
- **Race Condition Prevention**: Prevents concurrent workers from simultaneously evaluating consecutive transactions for the same user, which would otherwise distort time-delta and velocity calculations.

## Consumer Rebalance Protocol
- When an Aegis consumer worker crashes, Kafka's group coordinator triggers a cooperative rebalance (`CooperativeStickyAssignor`).
- Active partitions are redistributed among surviving pods without halting consumption on unrelated partitions.
- Offset commits occur only after successful database persistence and feature caching, ensuring at-least-once durability backed by idempotent writes.

