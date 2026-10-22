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

# Auto-start embedded llama-server if no external backend is active
if ! curl -s http://127.0.0.1:8080/v1/models >/dev/null 2>&1 && \
   ! curl -s http://127.0.0.1:1234/v1/models >/dev/null 2>&1 && \
   ! curl -s http://127.0.0.1:11434/v1/models >/dev/null 2>&1; then
    if [ -f "bin/llama-server" ] && [ -f "models/qwen2.5-coder-7b-instruct-abliterated-q4_k_m.gguf" ]; then
        echo "[*] No active LLM backend detected. Starting bundled llama-server..."
        bin/llama-server -m models/qwen2.5-coder-7b-instruct-abliterated-q4_k_m.gguf -ngl 99 --ctx-size 8192 --flash-attn --port 8080 --host 127.0.0.1 >/dev/null 2>&1 &
        sleep 2
    fi
fi

if [ "$1" == "--auto" ]; then
    echo "[*] Launching Master Autonomous Lab Orchestrator..."
    .venv/bin/python scripts/run_autonomous_lab.py
elif [ "$1" == "--gui" ]; then
    echo "[*] Launching Visual Workspace Web GUI..."
    .venv/bin/python -m core.cli --gui
elif [ "$1" == "--test" ] || [ "$1" == "--doctor" ]; then
    .venv/bin/python tests/system_test.py
elif [ "$1" == "--audit" ] || [ "$1" == "--benchmark" ]; then
    .venv/bin/python scripts/lab_acceptance_test.py
elif [ "$1" == "--stress" ]; then
    .venv/bin/python tests/intense_test_suite.py
elif [ "$1" == "--kb" ]; then
    .venv/bin/python core/knowledge_base.py
elif [ "$1" == "--eval" ]; then
    .venv/bin/python eval/benchmark.py
else
    .venv/bin/python -m core.cli "$@"
fi
