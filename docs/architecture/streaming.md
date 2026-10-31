# PySpark & Real-Time Streaming Architecture

This document illustrates the streaming data pipeline, event-time watermarking, and sliding window state aggregations.

```mermaid
flowchart LR
    subgraph KAFKA_IN["Kafka Input Stream"]
        KS["kafka:9092 (topic: transactions)"]
    end

    subgraph STREAMING_ENGINE["PySpark Structured Streaming Pipeline"]
        direction TB
        READ["readStream(format='kafka')"]
        PARSE["from_json(value, TransactionSchema)"]
        WM["withWatermark('timestamp', '10 minutes')"]
        
        subgraph WINDOWS["Sliding Window Aggregations"]
            W1["Window(1 min, slide 10s) -> count_1m"]
            W5["Window(5 min, slide 30s) -> count_5m, sum_5m, mean_5m, std_5m"]
            W10["Window(10 min, slide 1 min) -> count_10m"]
            W30["Window(30 min, slide 5 min) -> count_30m, unique_merchants_30m"]
        end
        
        JOIN["Join Window Metrics by account_id"]
        SINK["writeStream.foreachBatch(process_microbatch)"]
    end

    subgraph CHECKPOINTING["Fault Tolerant State Store"]
        CP_DIR["Checkpoint Directory (/tmp/aegis_checkpoints)"]
        HDFS[("Durable State Store / S3 / PVC")]
    end

    subgraph DOWNSTREAM["Scoring & Serving"]
        PRED["Inference & Decision Engine"]
        PG[("PostgreSQL Ledger")]
    end

    KS --> READ
    READ --> PARSE
    PARSE --> WM
    WM --> W1
    WM --> W5
    WM --> W10
    WM --> W30
    W1 --> JOIN
    W5 --> JOIN
    W10 --> JOIN
    W30 --> JOIN
    JOIN --> SINK
    
    SINK <--> CHECKPOINTING
    SINK --> PRED
    PRED --> PG
```

## Watermarking & Out-of-Order Execution
- **Watermark Threshold**: 10 minutes past maximum observed event time.
- **State Bounding**: PySpark purges window state records once the trailing edge of the watermark exceeds the window's `end_time`, preventing unbounded heap memory growth.
- **Late Arrivals**: Transactions arriving after the watermark threshold are discarded or routed to the Dead Letter Queue.

