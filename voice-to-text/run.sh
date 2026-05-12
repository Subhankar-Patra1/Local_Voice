#!/bin/bash
# Run Voice-to-Text on Linux / macOS

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Detect virtual environment location
if [ -d "$SCRIPT_DIR/venv/bin" ]; then
    PYTHON="$SCRIPT_DIR/venv/bin/python"
elif [ -d "$SCRIPT_DIR/.venv/bin" ]; then
    PYTHON="$SCRIPT_DIR/.venv/bin/python"
else
    PYTHON="python3"
fi

echo "Starting Voice-to-Text..."
echo "Python: $PYTHON"
echo ""

cd "$SCRIPT_DIR"
"$PYTHON" main.py
