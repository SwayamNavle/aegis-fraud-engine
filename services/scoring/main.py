"""
Aegis Fraud Scoring Microservice
Provides high-throughput HTTP endpoints for real-time model scoring and Prometheus telemetry.
"""

import os
import sys
import time
from typing import Dict, Any, Union
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST

# Ensure project root is in python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from services.scoring.predictor import FraudPredictor
from services.scoring.model_loader import ModelRegistry
from streaming.schemas.transaction_schema import FeatureVector, PredictionResult

app = FastAPI(
    title="Aegis Real-Time Scoring Microservice",
    description="Low-latency XGBoost inference service for streaming fraud detection",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Prometheus Telemetry Metrics (Idempotent registration for test suites)
from prometheus_client import REGISTRY

PREDICTIONS_TOTAL = REGISTRY._names_to_collectors.get("aegis_scoring_predictions_total") or Counter(
    "aegis_scoring_predictions_total",
    "Total fraud predictions evaluated",
    ["decision", "model_version"]
)
FRAUD_DETECTED_TOTAL = REGISTRY._names_to_collectors.get("aegis_scoring_fraud_detected_total") or Counter(
    "aegis_scoring_fraud_detected_total",
    "Total fraudulent transactions identified"
)
SCORING_LATENCY = REGISTRY._names_to_collectors.get("aegis_scoring_latency_seconds") or Histogram(
    "aegis_scoring_latency_seconds",
    "Inference latency in seconds",
    buckets=[0.0005, 0.001, 0.002, 0.005, 0.010, 0.025, 0.050, 0.100]
)
RISK_SCORE_HISTOGRAM = REGISTRY._names_to_collectors.get("aegis_scoring_risk_score") or Histogram(
    "aegis_scoring_risk_score",
    "Distribution of calibrated risk scores [0 - 100]",
    buckets=[10, 25, 40, 50, 60, 70, 80, 90, 100]
)

# Global Predictor Instance
predictor: FraudPredictor = None


@app.on_event("startup")
def startup_event():
    global predictor
    print("[Aegis Scoring API] Initializing ModelRegistry and FraudPredictor...")
    predictor = FraudPredictor()
    print("[Aegis Scoring API] Model loaded successfully. Ready for inference.")


@app.get("/health")
def health_check():
    return {
        "status": "ONLINE",
        "service": "aegis-scoring",
        "model_loaded": predictor is not None,
        "model_version": predictor.model_version if predictor else None
    }


@app.get("/model/info")
def model_info():
    if not predictor:
        raise HTTPException(status_code=503, detail="Predictor not initialized")
    return predictor.registry.get_info()


@app.post("/predict", response_model=PredictionResult)
def predict_transaction(payload: Dict[str, Any]):
    """
    Score incoming event.
    Payload can be raw transaction dictionary or pre-computed FeatureVector.
    """
    if not predictor:
        raise HTTPException(status_code=503, detail="Predictor service warming up")

    t0 = time.time()
    try:
        if "transaction_count_5m" in payload and "amount_z_score" in payload:
            fv = FeatureVector(**payload)
            result = predictor.predict(feature_vector=fv)
        else:
            result = predictor.predict(raw_txn=payload)

        # Record Prometheus metrics
        PREDICTIONS_TOTAL.labels(decision=result.decision, model_version=result.model_version).inc()
        RISK_SCORE_HISTOGRAM.observe(result.risk_score)
        SCORING_LATENCY.observe(time.time() - t0)
        
        if result.decision == "FRAUD":
            FRAUD_DETECTED_TOTAL.inc()

        return result

    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Inference error: {str(e)}")


@app.get("/metrics")
def metrics():
    """Prometheus metrics scrape target."""
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("services.scoring.main:app", host="0.0.0.0", port=8001, reload=False)
