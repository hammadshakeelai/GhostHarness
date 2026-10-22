import os
import sys
import time
import shutil
from pathlib import Path

SOURCE_DIR = Path("/home/hammad/Downloads/GhostHarness")
TARGET_DIR = Path("/run/media/hammad/Ventoy/GhostHarness")

EXCLUDE_DIRS = {".venv", "__pycache__", ".pytest_cache"}
EXCLUDE_EXTS = {".pyc", ".pyo"}

def copy_with_progress():
    print("=" * 65)
    print(" ⚡ GhostHarness Safe USB Transfer Utility ⚡")
    print(f" Source      : {SOURCE_DIR}")
    print(f" Destination : {TARGET_DIR}")
    print("=" * 65)

    if not SOURCE_DIR.exists():
        print(f"[ERROR] Source directory does not exist: {SOURCE_DIR}")
        sys.exit(1)

    TARGET_DIR.mkdir(parents=True, exist_ok=True)

    # Collect list of files to copy
    files_to_copy = []
    total_bytes = 0

    for root, dirs, files in os.walk(SOURCE_DIR):
        # Exclude directories in-place
        dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]
        
        rel_root = Path(root).relative_to(SOURCE_DIR)
        
        for file in files:
            if any(file.endswith(ext) for ext in EXCLUDE_EXTS):
                continue
            src_file = Path(root) / file
            dst_file = TARGET_DIR / rel_root / file
            size = src_file.stat().st_size
            files_to_copy.append((src_file, dst_file, size))
            total_bytes += size

    print(f"[*] Found {len(files_to_copy)} files to copy ({total_bytes / (1024**3):.2f} GB total)")

    copied_bytes = 0
    start_time = time.time()

    for idx, (src_file, dst_file, size) in enumerate(files_to_copy, 1):
        dst_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Display progress for large files or every 50 files
        is_large = size > 50 * 1024 * 1024
        if is_large:
            print(f"[{idx}/{len(files_to_copy)}] Copying large file: {src_file.name} ({size / (1024**3):.2f} GB)...")
        elif idx % 50 == 0 or idx == len(files_to_copy):
            pct = (copied_bytes / max(1, total_bytes)) * 100
            print(f"[{idx}/{len(files_to_copy)}] Progress: {pct:.1f}% ({copied_bytes / (1024**2):.1f} MB copied)")

        # Copy file content
        with open(src_file, "rb") as fsrc, open(dst_file, "wb") as fdst:
            chunk_size = 16 * 1024 * 1024 # 16MB buffer
            while True:
                buf = fsrc.read(chunk_size)
                if not buf:
                    break
                fdst.write(buf)
                copied_bytes += len(buf)

        # Preserve metadata
        shutil.copystat(src_file, dst_file)

    print("\n[*] Flushing filesystem write buffers to USB (running sync)...")
    os.sync()

    elapsed = time.time() - start_time
    print(f"[✔] Copy completed in {elapsed:.1f}s ({total_bytes / (1024**2 * elapsed):.2f} MB/s)")

    # Integrity verification
    print("\n[*] Verifying file sizes and transfer integrity...")
    mismatches = []
    verified_count = 0

    for src_file, dst_file, expected_size in files_to_copy:
        if not dst_file.exists():
            mismatches.append(f"Missing: {dst_file}")
            continue
        actual_size = dst_file.stat().st_size
        if actual_size != expected_size:
            mismatches.append(f"Size mismatch {dst_file.name}: expected {expected_size}, got {actual_size}")
        else:
            verified_count += 1

    if mismatches:
        print(f"[!] Warning: Found {len(mismatches)} errors:")
        for m in mismatches[:10]:
            print(f"    - {m}")
        sys.exit(1)
    else:
        print(f"[✔] Integrity Check PASSED: All {verified_count} files verified byte-for-byte!")
        print(f"Destination ready on USB: {TARGET_DIR}")

if __name__ == "__main__":
    copy_with_progress()
