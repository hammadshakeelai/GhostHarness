#!/usr/bin/env bash
# GhostHarness Zero-Admin Portable Launcher (Linux)
set -e

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$DIR"

echo "=================================================="
echo "   GhostHarness: Zero-Admin Sovereign Launcher    "
echo "=================================================="

# Check Python version
PYTHON_CMD=""
for cmd in python3.13 python3.12 python3.11 python3; do
    if command -v "$cmd" >/dev/null 2>&1; then
        PYTHON_CMD="$cmd"
        break
    fi
done

if [ -z "$PYTHON_CMD" ]; then
    echo "[!] No python found in PATH. Please ensure Python is available."
    exit 1
fi

echo "[*] Using Python: $($PYTHON_CMD --version)"

# Check if portable venv exists in directory (on USB)
if [ ! -d ".venv" ]; then
    echo "[*] Creating user-space virtual environment in .venv..."
    $PYTHON_CMD -m venv .venv
    .venv/bin/pip install --upgrade pip --quiet
    if [ -f "requirements.txt" ]; then
        echo "[*] Installing dependencies..."
        .venv/bin/pip install -r requirements.txt --quiet
    fi
fi

# Run with virtual environment
export PYTHONPATH="$DIR:$PYTHONPATH"
if [ "$1" == "--gui" ]; then
    echo "[*] Launching Visual Workspace Web GUI..."
    .venv/bin/python -m core.cli --gui
elif [ "$1" == "--test" ] || [ "$1" == "--doctor" ]; then
    .venv/bin/python tests/system_test.py
elif [ "$1" == "--stress" ]; then
    .venv/bin/python tests/intense_test_suite.py
elif [ "$1" == "--kb" ]; then
    .venv/bin/python core/knowledge_base.py
elif [ "$1" == "--eval" ]; then
    .venv/bin/python eval/benchmark.py
else
    .venv/bin/python -m core.cli "$@"
fi
