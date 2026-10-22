# GhostHarness Windows Zero-USB Bootstrap Installer
# Usage in Windows PowerShell:
# irm https://raw.githubusercontent.com/hammadshakeel/GhostHarness/main/scripts/bootstrap.ps1 | iex

Write-Host "================================================================" -ForegroundColor Cyan
Write-Host "      ⚡ GhostHarness Windows Sovereign Setup Installer ⚡      " -ForegroundColor Cyan
Write-Host "================================================================" -ForegroundColor Cyan

$InstallDir = "$HOME\GhostHarness"

if (Test-Path $InstallDir) {
    Write-Host "[*] Existing installation found at $InstallDir. Updating..." -ForegroundColor Yellow
    Set-Location $InstallDir
    git pull origin main
} else {
    Write-Host "[*] Cloning GhostHarness to $InstallDir..." -ForegroundColor Green
    git clone https://github.com/hammadshakeel/GhostHarness.git $InstallDir
    Set-Location $InstallDir
}

# Redirect all caches into the project folder so nothing is written to C:\Users\...\AppData
$env:HF_HOME = "$InstallDir\.cache\huggingface"
$env:TORCH_HOME = "$InstallDir\.cache\torch"
$env:PYTHONPYCACHEPREFIX = "$InstallDir\.cache\pycache"
$env:PYTHONPATH = "$InstallDir;$env:PYTHONPATH"

# Locate Python 3.10+
$pythonCmd = (Get-Command python -ErrorAction SilentlyContinue).Source
if (-not $pythonCmd) {
    Write-Host "[!] Python 3.10+ is required in PATH." -ForegroundColor Red
    Exit 1
}

Write-Host "[*] Detected Python: $(python --version)" -ForegroundColor Green

# Setup user-space virtual environment inside repo
if (-not (Test-Path ".venv")) {
    Write-Host "[*] Creating user-space virtual environment in .venv..." -ForegroundColor Yellow
    python -m venv .venv
    .\.venv\Scripts\python.exe -m pip install --upgrade pip --quiet
    if (Test-Path "requirements.txt") {
        Write-Host "[*] Installing Python dependencies into user-space..." -ForegroundColor Yellow
        .\.venv\Scripts\pip.exe install -r requirements.txt --quiet
    }
}

Write-Host "[*] Launching GhostHarness Onboarding Wizard..." -ForegroundColor Cyan
.\.venv\Scripts\python.exe scripts\init_wizard.py
