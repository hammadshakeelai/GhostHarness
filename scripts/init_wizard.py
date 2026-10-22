#!/usr/bin/env python3
"""
GhostHarness Interactive Onboarding Wizard
Guides the user through first-run initialization on a new computer or VM without needing admin rights.
"""

import sys
import os
import subprocess
import shutil
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

def clr(txt: str, c: str) -> str:
    codes = {
        "cyan": "\033[96m",
        "green": "\033[92m",
        "yellow": "\033[93m",
        "red": "\033[91m",
        "bold": "\033[1m",
        "dim": "\033[2m",
        "reset": "\033[0m"
    }
    return f"{codes.get(c, '')}{txt}{codes['reset']}"

def print_wizard_banner():
    banner = r"""
   ________                  __  __                                
  / ____/ /_  ____  _____/ /_/ / /___ _____  ____  ___  __________
 / / __/ __ \/ __ \/ ___/ __/ /_/ / __ `/ __ \/ __ \/ _ \/ ___/ ___/
/ /_/ / / / / /_/ (__  ) /_/ __  / /_/ / / / / / / /  __/ /  (__  ) 
\____/_/ /_/\____/____/\__/_/ /_/\__,_/_/ /_/_/ /_/\___/_/  /____/  
   ================================================================
          INITIALIZATION & FIRST-RUN ONBOARDING WIZARD
   ================================================================
    """
    print(clr(banner, "cyan"))

def run_wizard():
    print_wizard_banner()
    print(clr("Welcome to GhostHarness!", "bold"))
    print("This wizard will configure your sovereign agent environment for this machine.\n")

    # Step 1: Detect Hardware
    print(clr("[Step 1/5] Detecting Hardware Profile...", "bold"))
    try:
        from core.memory_manager import memory_manager
        telemetry = memory_manager.get_hardware_telemetry()
        gpu_name = telemetry["gpu_name"]
        vram_gb = telemetry["vram_total_mb"] / 1024
        ram_gb = telemetry["ram_total_mb"] / 1024
        print(f"  • GPU Detected : {clr(gpu_name, 'green')} ({vram_gb:.1f} GB VRAM)")
        print(f"  • System RAM   : {clr(f'{ram_gb:.1f} GB', 'green')}")
        print(f"  • Headroom     : {clr(telemetry['status_message'], 'cyan')}")
    except Exception as e:
        print(f"  • Telemetry fallback: {e}")

    # Step 2: Virtual Environment Status
    print(clr("\n[Step 2/5] Checking Python User-Space Environment...", "bold"))
    venv_dir = PROJECT_ROOT / ".venv"
    if venv_dir.is_dir():
        print(clr("  ✔ Portable virtualenv (.venv) already present and active.", "green"))
    else:
        print("  • No .venv detected. Creating user-space virtualenv...")
        subprocess.run([sys.executable, "-m", "venv", str(venv_dir)], check=True)
        pip_path = venv_dir / "bin" / "pip"
        if not pip_path.is_file():
            pip_path = venv_dir / "Scripts" / "pip.exe"
        if pip_path.is_file() and (PROJECT_ROOT / "requirements.txt").is_file():
            print("  • Installing dependencies in user-space...")
            subprocess.run([str(pip_path), "install", "-r", str(PROJECT_ROOT / "requirements.txt"), "--quiet"])
            print(clr("  ✔ Environment successfully initialized.", "green"))

    # Step 3: LLM Inference Backend Detection
    print(clr("\n[Step 3/5] Probing Local Model Inference Backends...", "bold"))
    try:
        from core.engine import InferenceEngine
        import asyncio
        engine = InferenceEngine()
        health = asyncio.run(engine.check_health())
        if health.get("online"):
            print(clr(f"  ✔ Connected to {health.get('backend')} at {health.get('endpoint')}", "green"))
            print(f"    Available models: {', '.join(health.get('available_models', [])[:3])}")
        else:
            print(clr("  ⚠ No active LLM server found on ports 1234 (LM Studio), 8080 (llama-server), or 11434 (Ollama).", "yellow"))
            print("    Options to start:")
            print("    1) Open LM Studio and start local server on port 1234.")
            print("    2) Place a GGUF model in models/ and run embedded llama-server.")
    except Exception as e:
        print(f"  Backend check: {e}")

    # Step 4: Check GGUF Models
    print(clr("\n[Step 4/5] Checking Local Model Storage (models/)...", "bold"))
    models_dir = PROJECT_ROOT / "models"
    models_dir.mkdir(parents=True, exist_ok=True)
    gguf_files = list(models_dir.glob("*.gguf"))
    if gguf_files:
        print(clr(f"  ✔ Found {len(gguf_files)} GGUF model(s):", "green"))
        for g in gguf_files:
            sz_gb = g.stat().st_size / (1024**3)
            print(f"    - {g.name} ({sz_gb:.2f} GB)")
    else:
        print(clr("  • No GGUF models in models/ folder.", "yellow"))
        print("    Download script available at: python scripts/download_model.py")

    # Step 5: System Verification Test
    print(clr("\n[Step 5/5] Running Self-Test Diagnostic Suite...", "bold"))
    from tests.system_test import SystemDiagnosticSuite
    suite = SystemDiagnosticSuite()
    suite.run_all()

    # Step 6: Choose Interface
    print(clr("================================================================", "cyan"))
    print(clr("Initialization Complete! How would you like to launch?", "bold"))
    print("  1) Launch Modern Visual Workspace Web GUI (http://127.0.0.1:8765)")
    print("  2) Launch Claude Code style Terminal TUI")
    print("  3) Exit back to shell")

    try:
        choice = input("\nEnter choice [1-3] (Default: 1): ").strip()
    except (KeyboardInterrupt, EOFError):
        choice = "3"

    if choice == "2":
        from core.cli import main
        main()
    elif choice == "3":
        print("Exiting onboarding wizard. Run ./scripts/launch.sh anytime to launch.")
    else:
        from web.server import start_server
        start_server(port=8765)

if __name__ == "__main__":
    run_wizard()
