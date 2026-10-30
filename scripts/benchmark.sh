#!/usr/bin/env bash
set -e

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )/.." && pwd )"
cd "$DIR"

export DYLD_LIBRARY_PATH="$DIR/lib:$DYLD_LIBRARY_PATH"
source .venv/bin/activate

echo "[Aegis] Launching Performance & Latency Benchmark..."
python3 scripts/benchmark.py
