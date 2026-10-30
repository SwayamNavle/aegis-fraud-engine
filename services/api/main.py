"""
Aegis Core FastAPI Application
Unified backend gateway for real-time fraud detection, analytics, and WebSockets.
"""

import os
import sys
import time
from typing import Dict, Any
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST

# Ensure project root is in python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from services.api.database.connection import init_db
from services.api.routes import transactions, alerts, stats, monitoring, websocket

app = FastAPI(
    title="Aegis Fraud Detection Engine API",
    description="Distributed Event-Streaming & Real-Time Fraud Detection Engine",
    version="1.0.0"
)

# CORS Configuration
allowed_origins = os.getenv("CORS_ORIGINS", "*").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if "*" in allowed_origins else allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Prometheus Telemetry (Idempotent registration for test suites)
from prometheus_client import REGISTRY

if "aegis_http_requests_total" in REGISTRY._names_to_collectors:
    HTTP_REQUESTS_TOTAL = REGISTRY._names_to_collectors["aegis_http_requests_total"]
else:
    HTTP_REQUESTS_TOTAL = Counter(
        "aegis_http_requests_total",
        "Total HTTP requests handled by endpoint",
        ["method", "endpoint", "status_code"]
    )

if "aegis_http_request_duration_seconds" in REGISTRY._names_to_collectors:
    HTTP_REQUEST_DURATION = REGISTRY._names_to_collectors["aegis_http_request_duration_seconds"]
else:
    HTTP_REQUEST_DURATION = Histogram(
        "aegis_http_request_duration_seconds",
        "HTTP request latency in seconds",
        ["endpoint"]
    )


@app.middleware("http")
async def prometheus_telemetry_middleware(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    duration = time.time() - start_time
    
    endpoint = request.url.path
    status_code = str(response.status_code)
    HTTP_REQUESTS_TOTAL.labels(method=request.method, endpoint=endpoint, status_code=status_code).inc()
    HTTP_REQUEST_DURATION.labels(endpoint=endpoint).observe(duration)
    return response


@app.on_event("startup")
async def on_startup():
    print("[Aegis API] Initializing database schema...")
    await init_db()
    print("[Aegis API] System ready to receive streaming traffic.")


# Mount API Routers
app.include_router(transactions.router)
app.include_router(alerts.router)
app.include_router(stats.router)
app.include_router(monitoring.router)
app.include_router(websocket.router)


@app.get("/health")
def health():
    return {
        "status": "ONLINE",
        "service": "aegis-api-gateway",
        "timestamp": time.time()
    }


@app.get("/model/info")
def model_info():
    """Returns model metadata, active version, hyperparameters, and feature schema."""
    from services.api.routes.transactions import get_predictor
    predictor = get_predictor()
    return predictor.registry.get_info()


@app.post("/predict")
def predict_transaction(payload: Dict[str, Any]):
    """Inline transaction scoring endpoint."""
    from services.api.routes.transactions import get_predictor
    predictor = get_predictor()
    if "transaction_count_5m" in payload and "amount_z_score" in payload:
        from streaming.schemas.transaction_schema import FeatureVector
        fv = FeatureVector(**payload)
        return predictor.predict(feature_vector=fv)
    return predictor.predict(raw_txn=payload)


@app.get("/metrics")
def metrics():
    """Prometheus metric scrape target."""
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


# Mount frontend dist static files if built
frontend_dist = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "frontend", "dist")
if os.path.exists(frontend_dist):
    app.mount("/assets", StaticFiles(directory=os.path.join(frontend_dist, "assets")), name="assets")

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        file_path = os.path.join(frontend_dist, full_path)
        if os.path.exists(file_path) and os.path.isfile(file_path):
            return FileResponse(file_path)
        return FileResponse(os.path.join(frontend_dist, "index.html"))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("services.api.main:app", host="0.0.0.0", port=8000, reload=False)
