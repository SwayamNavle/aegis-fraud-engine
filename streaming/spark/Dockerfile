FROM bitnami/spark:3.5.0

USER root
WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl python3-pip \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt

COPY streaming/ streaming/
COPY ml/ ml/

ENV PYTHONPATH=/app
ENV SPARK_MASTER=local[*]
ENV KAFKA_BOOTSTRAP_SERVERS=kafka:9092

USER 1001
CMD ["python3", "streaming/spark/streaming_job.py", "--mode", "spark"]
