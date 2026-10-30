#!/usr/bin/env bash
set -e

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )/.." && pwd )"
cd "$DIR"

export DYLD_LIBRARY_PATH="$DIR/lib:$DYLD_LIBRARY_PATH"
source .venv/bin/activate

echo "[Aegis] Starting Model Training Pipeline..."
python3 ml/training/train.py
