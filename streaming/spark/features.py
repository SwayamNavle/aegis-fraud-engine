"""
PySpark Structured Streaming Feature Expressions & Schemas
Defines Spark SQL schemas, event-time watermarking, and sliding window transformations.
"""

from pyspark.sql.types import (
    StructType, StructField, StringType, DoubleType, BooleanType, LongType, TimestampType
)
from pyspark.sql.functions import (
    col, from_json, to_json, struct, window, count, sum as _sum, avg, stddev, max as _max,
    min as _min, expr, coalesce, lit, when, udf
)
import math

# Transaction Schema for PySpark JSON parsing
TRANSACTION_SPARK_SCHEMA = StructType([
    StructField("transaction_id", StringType(), False),
    StructField("timestamp", StringType(), False),
    StructField("user_id", StringType(), False),
    StructField("account_id", StringType(), False),
    StructField("merchant_id", StringType(), False),
    StructField("merchant_category", StringType(), False),
    StructField("amount", DoubleType(), False),
    StructField("currency", StringType(), True),
    StructField("country", StringType(), False),
    StructField("city", StringType(), True),
    StructField("latitude", DoubleType(), False),
    StructField("longitude", DoubleType(), False),
    StructField("device_id", StringType(), False),
    StructField("device_type", StringType(), False),
    StructField("ip_address", StringType(), True),
    StructField("payment_method", StringType(), True),
    StructField("card_present", BooleanType(), True),
    StructField("is_international", BooleanType(), True),
    StructField("previous_transaction_timestamp", StringType(), True)
])


@udf(returnType=DoubleType())
def spark_haversine_udf(lat1, lon1, lat2, lon2):
    """Haversine distance UDF in kilometers for geospatial velocity."""
    if lat1 is None or lon1 is None or lat2 is None or lon2 is None:
        return 0.0
    r = 6371.0
    phi1 = math.radians(float(lat1))
    phi2 = math.radians(float(lat2))
    dphi = math.radians(float(lat2) - float(lat1))
    dlambda = math.radians(float(lon2) - float(lon1))
    a = (math.sin(dphi / 2.0)**2 +
         math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2.0)**2)
    return float(r * 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a)))


def build_windowed_aggregations(df, watermark_delay="10 minutes", window_duration="5 minutes", slide_duration="1 minute"):
    """
    Applies event-time watermarking and sliding window aggregations on transactions.
    
    Window Semantics:
    - watermark_delay: Allows out-of-order events up to 10 minutes late based on 'event_time'.
    - window_duration: 5 minutes aggregation window.
    - slide_duration: Evaluated every 1 minute slide.
    - group: account_id, window
    """
    watermarked_df = df.withWatermark("event_time", watermark_delay)

    windowed = watermarked_df.groupBy(
        col("account_id"),
        window(col("event_time"), window_duration, slide_duration)
    ).agg(
        count("transaction_id").alias("transaction_count_5m"),
        _sum("amount").alias("transaction_amount_sum_5m"),
        avg("amount").alias("transaction_amount_avg_5m"),
        coalesce(stddev("amount"), lit(0.0)).alias("transaction_amount_std_5m"),
        _max("amount").alias("max_transaction_amount_5m"),
        _min("amount").alias("min_transaction_amount_5m")
    )
    return windowed
