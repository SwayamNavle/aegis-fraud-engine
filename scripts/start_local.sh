#!/usr/bin/env bash
set -e

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )/.." && pwd )"
cd "$DIR"

# Export OpenMP path for XGBoost on macOS
if [[ "$OSTYPE" == "darwin"* ]]; then
    export DYLD_LIBRARY_PATH="$DIR/lib:$DYLD_LIBRARY_PATH"
fi

if [ -d ".venv" ]; then
    source .venv/bin/activate
fi

# Ensure model exists
if [ ! -f "ml/models/xgb_fraud_model.json" ]; then
    echo "[!] Model not found. Training model first..."
    bash scripts/train_model.sh
fi

echo "=========================================================="
echo "🛡️  AEGIS COMMAND CENTER — Starting Local Engine"
echo "=========================================================="
echo "API Endpoint:        http://localhost:8000"
echo "Command Center UI:   http://localhost:8000"
echo "Swagger API Docs:    http://localhost:8000/docs"
echo "Prometheus Metrics:  http://localhost:8000/metrics"
echo "WebSocket Stream:    ws://localhost:8000/ws/transactions"
echo "=========================================================="
echo "Press Ctrl+C to terminate."

export PORT=8000
export HOST="0.0.0.0"
export DATABASE_URL="sqlite+aiosqlite:///./data/aegis.db"
export FRAUD_THRESHOLD="0.85"

exec python3 -m uvicorn services.api.main:app --host "$HOST" --port "$PORT" --log-level info
