import sys
import os
import time
import subprocess
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
MODELS_DIR = PROJECT_ROOT / "models"
MODELS_DIR.mkdir(parents=True, exist_ok=True)

MODEL_URLS = {
    "7b-abliterated": {
        "name": "Qwen 2.5 Coder 7B Abliterated (Q4_K_M)",
        "url": "https://huggingface.co/mradermacher/Qwen2.5-Coder-7B-Instruct-abliterated-GGUF/resolve/main/Qwen2.5-Coder-7B-Instruct-abliterated.Q4_K_M.gguf",
        "filename": "qwen2.5-coder-7b-instruct-abliterated-q4_k_m.gguf",
        "size_gb": 4.68,
        "vram_req": "~4.5 GB (100% in 6GB VRAM)"
    },
    "1.5b-fast": {
        "name": "Qwen 2.5 Coder 1.5B Instruct (Q4_K_M)",
        "url": "https://huggingface.co/Qwen/Qwen2.5-Coder-1.5B-Instruct-GGUF/resolve/main/qwen2.5-coder-1.5b-instruct-q4_k_m.gguf",
        "filename": "qwen2.5-coder-1.5b-instruct-q4_k_m.gguf",
        "size_gb": 1.11,
        "vram_req": "~1.5 GB (Ultra-light, works on any PC/VM)"
    }
}

def download_with_auto_resume(model_key: str = "7b-abliterated", max_retries: int = 30):
    spec = MODEL_URLS.get(model_key, MODEL_URLS["7b-abliterated"])
    dest_path = MODELS_DIR / spec["filename"]

    print("=" * 65)
    print(f" GhostHarness Resilient Model Downloader")
    print(f" Target Model : {spec['name']}")
    print(f" Expected Size: {spec['size_gb']} GB")
    print(f" Destination  : {dest_path}")
    print("=" * 65)

    retries = 0
    while retries < max_retries:
        retries += 1
        current_size = dest_path.stat().st_size if dest_path.is_file() else 0
        current_gb = current_size / (1024**3)
        print(f"\n[Attempt {retries}/{max_retries}] Resuming from {current_gb:.2f} GB / {spec['size_gb']} GB...")

        cmd = [
            "curl",
            "-L",
            "-C", "-",
            "--retry", "15",
            "--retry-delay", "3",
            "--retry-connrefused",
            "--retry-max-time", "120",
            spec["url"],
            "-o", str(dest_path)
        ]

        res = subprocess.run(cmd)
        if res.returncode == 0:
            print(f"\n[SUCCESS] Download completed for {spec['name']}!")
            return True
        else:
            print(f"\n[!] Connection interrupted (code {res.returncode}). Reconnecting in 3 seconds...")
            time.sleep(3)

    print(f"\n[ERROR] Maximum retries ({max_retries}) exceeded.")
    return False

if __name__ == "__main__":
    choice = sys.argv[1] if len(sys.argv) > 1 else "7b-abliterated"
    download_with_auto_resume(choice)
