# ADR 002: Selection of PySpark Structured Streaming for Windowed State Aggregations

## Context & Problem Statement
Detecting financial fraud requires evaluating temporal aggregation features across multiple time horizons (e.g. 1-minute velocity, 5-minute transaction count, 10-minute expenditure sum, 30-minute standard deviation). Processing these features over high-throughput event streams requires an engine capable of handling out-of-order events, maintaining state across tumbling/sliding windows, and providing fault-tolerant exactly-once state management.

## Decision
We adopted **PySpark Structured Streaming** for distributed micro-batch aggregation and stateful stream processing over event time.

## Key Technical Rationale
1. **Event-Time Processing & Watermarking**:
   Unlike processing-time systems that corrupt sliding window metrics when network latency occurs, PySpark Structured Streaming natively operates on transaction `timestamp` fields. By defining watermarks (`withWatermark("timestamp", "10 minutes")`), Aegis automatically handles late-arriving events while bounding state memory by dropping data that arrives later than the watermark threshold.
2. **Deterministic Sliding Windows**:
   Structured Streaming provides native sliding window operators:
   `groupBy(col("account_id"), window(col("timestamp"), "5 minutes", "1 minute"))`
   This allows calculating rollups across 1-minute, 5-minute, 10-minute, and 30-minute horizons with mathematical consistency.
3. **State Store Fault Tolerance via Checkpointing**:
   PySpark checkpoints streaming state and consumer offsets to durable storage (e.g., local disk, HDFS, or S3/GCS). Upon worker node failure or pod termination, streaming queries resume from the last committed checkpoint with zero state loss and exactly-once micro-batch semantics.
4. **Code Unification Between Batch and Streaming**:
   PySpark uses the same Catalyst optimizer and DataFrame API for both batch training (offline feature backfilling) and real-time streaming, preventing logic divergence between development and production.

## Tradeoffs & Considered Alternatives
- **Apache Flink**: Offers true per-event streaming and lower tail latency, but requires heavy Java/Scala operational maintenance, complex deployment topologies, and steeper developer ramp-up compared to Python/PySpark ecosystems.
- **In-Memory Redis Rolling Windows**: Lightweight and low latency, but lacks out-of-the-box support for distributed joins, complex event-time watermarking, and resilient distributed checkpointing when scaling to millions of concurrent accounts. Aegis uses Redis as a warm read-through cache for online serving, while streaming state aggregation architecture is anchored by Spark semantics.

