#!/usr/bin/env bash
# ======================================================================
#  GhostHarness: Master 1-Click Autonomous Lab Orchestrator (Linux/Unix)
#  Self-contained: forces all caches, models, and venvs into USB/repo
#  Zero Admin Rights Required | Zero Host Storage Spill
# ======================================================================
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

export HF_HOME="$SCRIPT_DIR/.cache/huggingface"
export TORCH_HOME="$SCRIPT_DIR/.cache/torch"
export PYTHONPYCACHEPREFIX="$SCRIPT_DIR/.cache/pycache"
export TMPDIR="$SCRIPT_DIR/.cache/tmp"
export PYTHONPATH="$SCRIPT_DIR:$PYTHONPATH"

mkdir -p "$SCRIPT_DIR/.cache/huggingface" "$SCRIPT_DIR/.cache/torch" "$SCRIPT_DIR/.cache/pycache" "$SCRIPT_DIR/.cache/tmp"

if [ -f ".venv/bin/activate" ]; then
    source .venv/bin/activate
elif command -v python3 >/dev/null 2>&1; then
    if [ ! -d ".venv" ]; then
        echo "[*] Initializing portable virtualenv in .venv..."
        python3 -m venv .venv
        source .venv/bin/activate
        pip install --upgrade pip --quiet
        if [ -f "requirements.txt" ]; then
            pip install -r requirements.txt --quiet
        fi
    fi
fi

python3 scripts/run_autonomous_lab.py "$@"
