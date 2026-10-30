# Aegis Streaming Engine & Sliding-Window Feature Pipeline

## 1. Kafka Architecture & Topic Topologies

Aegis uses Apache Kafka (KRaft mode) as the central distributed message backbone. The pipeline divides processing into distinct decoupled topics with dedicated consumer groups.

```
+--------------------+        +-----------------------+        +--------------------------+
|  transactions.raw  |  --->  | transactions.features |  --->  | transactions.predictions |
+--------------------+        +-----------------------+        +--------------------------+
          |                                                                 |
    (malformed)                                                       (risk >= 0.85)
          v                                                                 v
+--------------------+                                         +--------------------------+
|    dead-letter     |                                         |   transactions.alerts    |
+--------------------+                                         +--------------------------+
```

### 1.1. Topic Definitions

1. **`transactions.raw`**:
   - Ingests incoming synthetic or production transactions.
   - **Partitions**: 6
   - **Replication Factor**: 1 (Local/Dev) or 3 (Production)
   - **Partition Key**: `account_id` (UTF-8 bytes)
2. **`transactions.features`**:
   - Stores enriched events containing the 16 engineered features.
   - **Partitions**: 6
   - **Partition Key**: `account_id`
3. **`transactions.predictions`**:
   - Stores inference results, calibrated probabilities, risk scores, and reason codes.
   - **Partitions**: 6
4. **`transactions.alerts`**:
   - High-priority topic filtering transactions with `risk_score >= 85.0` or `fraud_probability >= 0.85`.
5. **`dead-letter`**:
   - Captures malformed JSON, unparseable timestamps, or corrupted payloads.

---

## 2. Why Account-Based Partition Keying?

In a distributed streaming architecture, the choice of message key dictates how events are distributed across Kafka partitions.

$$\text{Partition} = \text{murmur2}(\text{account\_id}) \pmod{\text{Total Partitions}}$$

### The Challenge of Distributed Sliding Windows
Calculating features such as:
- Number of transactions in the last 1 minute (`transaction_count_1m`)
- Physical distance between successive transactions (`distance_from_previous_transaction`)
- Time elapsed since last activity (`time_since_previous_transaction`)

requires stateful tracking of an account's recent transaction history.

### The Solution
By using `account_id` as the message key:
1. **Strict Monotonic Ordering**: All transactions for a specific account are delivered to the exact same partition in the exact sequence they were published.
2. **Partition Local State**: Streaming consumers can maintain localized in-memory state windows for each account without having to coordinate across worker nodes.
3. **Elimination of Race Conditions**: Two concurrent transactions from the same account will never be processed out of order on separate consumer threads.

---

## 3. Horizontal Scaling with Consumer Groups

Aegis scales horizontally via Kafka consumer groups (`aegis-streaming-consumers`):

- **6 Partitions / 1 Consumer**: 1 consumer processes all 6 partitions.
- **6 Partitions / 2 Consumers**: Each consumer processes 3 partitions in parallel.
- **6 Partitions / 3 Consumers**: Each consumer processes 2 partitions in parallel.
- **6 Partitions / 6 Consumers**: Each consumer is dedicated to 1 partition, maximizing concurrency.

If consumer instances exceed partition count (e.g., 7 consumers for 6 partitions), the extra consumer remains on warm standby ready for instant failover if a peer crashes.

---

## 4. PySpark Structured Streaming Semantics

### 4.1. Event-Time vs. Processing-Time
Financial transactions are subject to network lag, mobile offline buffering, and clock skew. Aegis operates strictly on **Event-Time** (`timestamp` embedded in the transaction payload) rather than the wall-clock ingestion time at the Kafka broker.

### 4.2. Watermarking
To prevent unbounded state growth in the Spark state store, Aegis applies a **10-minute watermark**:

```python
stream_df = parsed_df \
    .withWatermark("event_time", "10 minutes")
```

- **Late-Arrival Semantics**: Events arriving with timestamp $T_{\text{event}} \ge T_{\text{watermark}} - 10\text{m}$ are incorporated into the window aggregations.
- **Drop Semantics**: Any anomalous transaction delayed by more than 10 minutes past the watermark is dropped from window state calculation and routed to the dead-letter monitor.

### 4.3. Sliding Windows
Aegis defines multi-scale sliding windows:

```python
windowed_features = stream_df \
    .groupBy(
        F.window("event_time", "5 minutes", "1 minute"),
        "account_id"
    ) \
    .agg(
        F.count("transaction_id").alias("transaction_count_5m"),
        F.sum("amount").alias("transaction_amount_sum_5m"),
        F.avg("amount").alias("transaction_amount_avg_5m"),
        F.stddev("amount").alias("transaction_amount_std_5m"),
        F.max("amount").alias("max_transaction_amount_5m")
    )
```

- **Window Duration**: 5 minutes of historical activity.
- **Slide Duration**: Evaluated every 1 minute.
- **Aggregations**: Computes running transaction volume, cumulative amount, mean spend, standard deviation, and maximum ticket size per account.

---

## 5. Checkpointing & Fault Recovery

PySpark Structured Streaming maintains transactional fault tolerance using a write-ahead log and state store checkpoint directory:

```
checkpoints/aegis/features/
├── commits/          # Completed micro-batch sequence IDs
├── offsets/          # Exact Kafka partition start and end offsets per batch
├── metadata          # Stream query UUID and schema validation
└── state/            # RocksDB / HDFS state store containing window aggregations
```

### What Happens on Worker Restart?
1. **Crash**: A Spark executor or driver pod terminates abruptly.
2. **Re-initialization**: The new Spark job initializes and reads `/checkpoints/aegis/features/`.
3. **State Rehydration**: Spark reloads the in-flight sliding window state from the `state/` directory.
4. **Offset Replay**: Spark checks the last entry in `commits/` and retrieves the uncommitted Kafka partition offsets from `offsets/`.
5. **No Data Loss / No Duplicate Features**: Exactly-once processing is maintained up to the Kafka output sink.
