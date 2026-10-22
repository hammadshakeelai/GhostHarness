@echo off
REM GhostHarness Zero-Admin Portable Launcher (Windows)
title GhostHarness Sovereign Agent

cd /d "%~dp0\.."

echo ==================================================
echo    GhostHarness: Zero-Admin Sovereign Launcher    
echo ==================================================

REM Locate user-space Python
python --version >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [!] Python is not in PATH. Please verify Python 3.10+ is accessible.
    pause
    exit /b 1
)

REM Create user-space portable venv if not present
if not exist ".venv" (
    echo [*] Creating portable user-space virtualenv in .venv...
    python -m venv .venv
    call .venv\Scripts\activate.bat
    python -m pip install --upgrade pip --quiet
    if exist "requirements.txt" (
        echo [*] Installing dependencies from requirements.txt...
        python -m pip install -r requirements.txt --quiet
    )
) else (
    call .venv\Scripts\activate.bat
)

set PYTHONPATH=%CD%;%PYTHONPATH%

if "%1"=="--gui" (
    echo [*] Launching Visual Workspace Web GUI...
    python -m core.cli --gui
) else (
    python -m core.cli %*
)

pause
