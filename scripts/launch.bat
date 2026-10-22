@echo off
REM ================================================================
REM  GhostHarness: Zero-Admin Portable Windows Launcher
REM  Self-contained: forces all caches, models, and venvs into USB
REM ================================================================
title GhostHarness Sovereign Agent

cd /d "%~dp0\.."

REM Redirect all caches to stay 100% inside the USB/repo folder
set HF_HOME=%CD%\.cache\huggingface
set TORCH_HOME=%CD%\.cache\torch
set PYTHONPYCACHEPREFIX=%CD%\.cache\pycache
set PYTHONPATH=%CD%;%PYTHONPATH%

echo ================================================================
echo    ⚡ GhostHarness: Zero-Admin Sovereign Windows Launcher ⚡   
echo ================================================================

REM Locate user-space Python
python --version >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [!] Python is not in PATH. Please verify Python 3.10+ is available.
    pause
    exit /b 1
)

REM Create portable virtualenv in repo if missing or from Linux
if not exist ".venv\Scripts\activate.bat" (
    if exist ".venv" (
        echo [*] Detected Linux venv or incomplete virtualenv, preparing Windows venv...
        rmdir /s /q ".venv"
    )
    echo [*] Creating portable user-space virtualenv in .venv...
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

REM Check if a local LLM backend is already active on port 8080, 1234, or 11434
netstat -ano | findstr ":8080 :1234 :11434" >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    if exist "bin\llama-server.exe" (
        if exist "models\qwen2.5-coder-7b-instruct-abliterated-q4_k_m.gguf" (
            echo [*] No external LLM backend detected.
            echo [*] Starting bundled portable llama-server (RTX 5060 GPU mode)...
            start /b "" "bin\llama-server.exe" -m "models\qwen2.5-coder-7b-instruct-abliterated-q4_k_m.gguf" -ngl 99 --ctx-size 8192 --flash-attn --port 8080 --host 127.0.0.1
            timeout /t 3 /nobreak >nul 2>&1
        )
    )
)

REM Route launcher arguments
if "%1"=="--init" (
    python scripts\init_wizard.py
) else if "%1"=="--gui" (
    echo [*] Launching Visual Workspace Web GUI on http://127.0.0.1:8765...
    python -m core.cli --gui
) else if "%1"=="--test" (
    python tests\system_test.py
) else if "%1"=="--doctor" (
    python tests\system_test.py
) else if "%1"=="--audit" (
    python scripts\lab_acceptance_test.py
) else if "%1"=="--benchmark" (
    python scripts\lab_acceptance_test.py
) else if "%1"=="--stress" (
    python tests\intense_test_suite.py
) else if "%1"=="--kb" (
    python core\knowledge_base.py
) else if "%1"=="--eval" (
    python eval\benchmark.py
) else (
    REM Default to interactive Claude Code style terminal
    python -m core.cli %*
)

pause
