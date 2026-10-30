FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl libgomp1 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY ml/ ml/
COPY streaming/ streaming/
COPY services/scoring/ services/scoring/

ENV PYTHONPATH=/app
ENV FRAUD_THRESHOLD=0.70
ENV MEDIUM_RISK_THRESHOLD=0.40

EXPOSE 8001

CMD ["uvicorn", "services.scoring.main:app", "--host", "0.0.0.0", "--port", "8001"]
