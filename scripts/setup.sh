#!/usr/bin/env bash
set -e

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )/.." && pwd )"
cd "$DIR"

echo "=========================================================="
echo "🛡️  AEGIS - Environment Setup"
echo "=========================================================="

# Create directories
mkdir -p data/raw data/processed ml/models ml/artifacts checkpoints/aegis/features frontend/dist/assets

# Python Virtualenv
if [ ! -d ".venv" ]; then
    echo "[+] Creating virtual environment (.venv)..."
    python3 -m venv .venv
fi

echo "[+] Activating virtual environment..."
source .venv/bin/activate

# Upgrade pip and install requirements
echo "[+] Installing project dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# macOS OpenMP check for XGBoost
if [[ "$OSTYPE" == "darwin"* ]]; then
    export DYLD_LIBRARY_PATH="$DIR/lib:$DYLD_LIBRARY_PATH"
    echo "[+] Configured DYLD_LIBRARY_PATH for macOS OpenMP support."
fi

# Generate demo dataset if not present
if [ ! -f "data/raw/train_transactions.csv" ]; then
    echo "[+] Generating 50,000 synthetic transactions for ML training..."
    python3 scripts/generate_demo_data.py --count 50000 --output data/raw/train_transactions.csv
fi

# Train model if not present
if [ ! -f "ml/models/xgb_fraud_model.json" ]; then
    echo "[+] Training XGBoost fraud detection model..."
    bash scripts/train_model.sh
fi

echo "=========================================================="
echo "✅ Aegis Environment Setup Complete!"
echo "   Run 'make run' or 'bash scripts/start_local.sh' to start."
echo "=========================================================="
