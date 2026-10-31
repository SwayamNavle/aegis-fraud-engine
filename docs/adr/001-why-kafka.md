# ADR 001: Selection of Apache Kafka for Ingestion & Event-Driven Streaming

## Context & Problem Statement
Aegis requires an enterprise-grade, distributed message broker capable of handling high-velocity financial payment streams (thousands of events per second) with guaranteed partition ordering, consumer group horizontal scaling, and strict replayability upon worker failure.

## Decision
We selected **Apache Kafka** deployed in modern **KRaft (Kafka Raft Metadata) mode** without ZooKeeper dependencies.

## Key Technical Rationale
1. **Account-Based Key Partitioning**:
   By using `account_id` as the message key, Kafka deterministically hashes every transaction for a specific user to the exact same partition (`hash(account_id) % num_partitions`). This guarantees total ordering for that account's transaction stream, preventing race conditions during kinematic velocity calculations (e.g. impossible travel, burst frequencies).
2. **Horizontal Scaling via Consumer Groups**:
   Topics partitioned across $N$ partitions can be concurrently consumed by up to $N$ independent consumer workers in the `aegis-streaming-consumers` group. Adding workers automatically triggers rebalancing without data loss.
3. **Offset-Based Replayability**:
   Kafka retains raw messages for a configurable retention window (e.g., 7 days). If downstream stream consumers (PySpark, scoring pods) crash or require backfilling historical features, consumer offsets can be reset to reprocess past events without re-generating data.
4. **Dead-Letter Routing (DLQ)**:
   Malformed or schema-violating events are diverted to `transactions.dlq`, isolating poison pills from the main processing pipeline.

## Tradeoffs & Considered Alternatives
- **RabbitMQ / AMQP**: Excellent for complex task routing, but lacks high-throughput sequential partition log semantics, multi-gigabyte historical replayability, and tight PySpark Structured Streaming integration.
- **AWS Kinesis / GCP Pub/Sub**: Cloud-proprietary; Kafka provides multi-cloud and local containerized parity.

