FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY streaming/ streaming/
COPY ml/ ml/

ENV PYTHONPATH=/app
ENV KAFKA_BOOTSTRAP_SERVERS=kafka:9092
ENV RATE=500
ENV FRAUD_RATIO=0.015

ENTRYPOINT ["python", "streaming/producer/producer.py"]
CMD ["--rate", "500", "--kafka-bootstrap", "kafka:9092"]
