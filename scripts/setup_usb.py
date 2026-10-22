import os
import sys
import subprocess
import shutil
from pathlib import Path

def prepare_offline_usb(target_usb_dir: str):
    """Downloads wheels and sets up offline air-gapped directory structure on USB drive."""
    usb_path = Path(target_usb_dir).resolve()
    print("=" * 60)
    print(f" GhostHarness: USB Offline Packager")
    print(f" Target Directory: {usb_path}")
    print("=" * 60)

    wheel_dir = usb_path / "wheels"
    models_dir = usb_path / "models"
    dataset_dir = usb_path / "datasets"

    for d in [wheel_dir, models_dir, dataset_dir]:
        d.mkdir(parents=True, exist_ok=True)

    print("[1/3] Downloading pip dependency wheels for offline install...")
    req_file = Path(__file__).resolve().parent.parent / "requirements.txt"
    if req_file.is_file():
        subprocess.run([
            sys.executable, "-m", "pip", "download",
            "-r", str(req_file),
            "-d", str(wheel_dir)
        ], check=True)

    print("[2/3] Writing offline installation instructions...")
    offline_readme = usb_path / "OFFLINE_SETUP.txt"
    offline_readme.write_text(
        "To install GhostHarness on a lab computer without internet:\n\n"
        "1. Open terminal or command prompt in this directory\n"
        "2. Run:\n"
        "   python -m venv .venv\n"
        "   source .venv/bin/activate (or .venv\\Scripts\\activate on Windows)\n"
        "   pip install --no-index --find-links=wheels/ -r requirements.txt\n"
        "3. Launch:\n"
        "   ./scripts/launch.sh --gui  (or scripts\\launch.bat --gui on Windows)\n"
    )

    print(f"[3/3] Ready! Place your GGUF models in: {models_dir}")
    print(f"Recommended models:")
    print(f" - Qwen2.5-Coder-7B-Instruct-Abliterated-Q4_K_M.gguf (~4.3 GB, 100% in 6GB VRAM)")
    print(f" - Qwen2.5-Coder-14B-Instruct-Q4_K_M.gguf (~8.5 GB, split GPU+RAM offload)")
    print("[SUCCESS] USB Preparation complete.")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scripts/setup_usb.py <path_to_usb_drive_or_folder>")
        sys.exit(1)
    prepare_offline_usb(sys.argv[1])
