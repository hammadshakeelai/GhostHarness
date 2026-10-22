#!/usr/bin/env bash
# GhostHarness Zero-USB Bootstrap Installer
# Usage: curl -sSL https://raw.githubusercontent.com/<username>/GhostHarness/main/scripts/bootstrap.sh | bash
set -e

echo "================================================================"
echo "      ⚡ GhostHarness Zero-USB Sovereign Setup Installer ⚡      "
echo "================================================================"

INSTALL_DIR="${HOME}/GhostHarness"

if [ -d "$INSTALL_DIR" ]; then
    echo "[*] Existing installation found at $INSTALL_DIR. Updating..."
    cd "$INSTALL_DIR"
    git pull origin main || true
else
    echo "[*] Cloning GhostHarness to $INSTALL_DIR..."
    git clone https://github.com/hammadshakeel/GhostHarness.git "$INSTALL_DIR" || {
        echo "[!] Git clone failed. Creating local folder..."
        mkdir -p "$INSTALL_DIR"
    }
    cd "$INSTALL_DIR"
fi

# Locate user-space Python 3.10+
PYTHON_CMD=""
for cmd in python3.14 python3.13 python3.12 python3.11 python3; do
    if command -v "$cmd" >/dev/null 2>&1; then
        PYTHON_CMD="$cmd"
        break
    fi
done

if [ -z "$PYTHON_CMD" ]; then
    echo "[!] Python 3.10+ is required but not found in PATH."
    exit 1
fi

echo "[*] Using Python: $($PYTHON_CMD --version)"

# Create virtual environment in user-space
if [ ! -d ".venv" ]; then
    echo "[*] Creating user-space virtual environment in .venv..."
    $PYTHON_CMD -m venv .venv
    .venv/bin/pip install --upgrade pip --quiet
    if [ -f "requirements.txt" ]; then
        echo "[*] Installing Python dependencies..."
        .venv/bin/pip install -r requirements.txt --quiet
    fi
fi

# Launch Interactive Onboarding Wizard
echo "[*] Launching GhostHarness Onboarding Wizard..."
.venv/bin/python scripts/init_wizard.py
