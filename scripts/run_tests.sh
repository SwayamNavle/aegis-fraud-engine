#!/usr/bin/env bash
set -e

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )/.." && pwd )"
cd "$DIR"

# Export OpenMP path for macOS
if [[ "$OSTYPE" == "darwin"* ]]; then
    export DYLD_LIBRARY_PATH="$DIR/lib:$DYLD_LIBRARY_PATH"
fi

if [ -d ".venv" ]; then
    source .venv/bin/activate
fi

echo "=========================================================="
echo "🛡️  AEGIS - Running Automated Test Suite"
echo "=========================================================="
python3 -m pytest tests/ -v
