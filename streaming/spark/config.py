"""
Aegis Spark Streaming Configuration
Defines parameters for Kafka broker connectivity, watermarks, sliding windows, and checkpoints.
"""

import os
from pydantic_settings import BaseSettings


class SparkStreamingConfig(BaseSettings):
    # Kafka Connection
    kafka_bootstrap_servers: str = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
    kafka_topic_raw: str = os.getenv("KAFKA_TOPIC_RAW", "transactions.raw")
    kafka_topic_features: str = os.getenv("KAFKA_TOPIC_FEATURES", "transactions.features")
    kafka_topic_dead_letter: str = os.getenv("KAFKA_TOPIC_DEAD_LETTER", "transactions.dead_letter")
    kafka_consumer_group: str = os.getenv("KAFKA_CONSUMER_GROUP", "aegis-spark-streaming-group")

    # Spark Engine Settings
    spark_app_name: str = "Aegis-PySpark-Streaming-Engine"
    spark_master: str = os.getenv("SPARK_MASTER", "local[*]")
    checkpoint_location: str = os.getenv("SPARK_CHECKPOINT_DIR", "data/checkpoints/spark")
    
    # Event-Time Semantics & Sliding Windows
    watermark_delay: str = "10 minutes"
    window_duration: str = "5 minutes"
    slide_duration: str = "1 minute"
    micro_batch_interval: str = "2 seconds"
    
    # Model Scoring Service URL
    scoring_service_url: str = os.getenv("SCORING_SERVICE_URL", "http://localhost:8001/predict")

    class Config:
        env_file = ".env"
        extra = "ignore"


config = SparkStreamingConfig()
