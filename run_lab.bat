@echo off
REM ======================================================================
REM  GhostHarness: Master 1-Click Autonomous Lab Orchestrator (Windows)
REM  Self-contained: forces all caches, models, and venvs into USB
REM  Zero Admin Rights Required | Zero Host Storage Spill
REM ======================================================================
title GhostHarness Autonomous Lab Orchestrator

cd /d "%~dp0"

REM Redirect all caches and temporary data to stay 100% inside the USB repo folder
set HF_HOME=%CD%\.cache\huggingface
set TORCH_HOME=%CD%\.cache\torch
set PYTHONPYCACHEPREFIX=%CD%\.cache\pycache
set TMPDIR=%CD%\.cache\tmp
set PYTHONPATH=%CD%;%PYTHONPATH%

echo ======================================================================
echo    ⚡ GhostHarness: Zero-Admin Autonomous Lab Launcher (RTX 5060) ⚡
echo ======================================================================

REM Check for user-space Python
python --version >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [!] Python 3.10+ is required but not found in PATH.
    echo [!] Please install Python or add it to PATH.
    pause
    exit /b 1
)

REM Setup or activate portable Windows virtualenv
if not exist ".venv\Scripts\activate.bat" (
    if exist ".venv" (
        echo [*] Purging incompatible venv, creating fresh Windows environment...
        rmdir /s /q ".venv"
    )
    echo [*] Initializing portable virtualenv in .venv...
    python -m venv .venv
    call .venv\Scripts\activate.bat
    python -m pip install --upgrade pip --quiet
    if exist "requirements.txt" (
        if exist "wheels" (
            echo [*] Installing dependencies from offline wheels/ folder...
            python -m pip install --no-index --find-links=wheels -r requirements.txt --quiet
        ) else (
            echo [*] Installing dependencies from requirements.txt...
            python -m pip install -r requirements.txt --quiet
        )
    )
) else (
    call .venv\Scripts\activate.bat
)

REM Launch the Master Autonomous Orchestrator
python scripts\run_autonomous_lab.py %*

if %ERRORLEVEL% NEQ 0 (
    echo [!] Orchestrator exited with code %ERRORLEVEL%.
    pause
)
