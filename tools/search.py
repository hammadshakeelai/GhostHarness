import os
import re
from pathlib import Path
from typing import Dict, Any, List

async def grep_search(pattern: str, path: str = ".", max_results: int = 50, root: str = ".") -> Dict[str, Any]:
    """Search for regex or keyword pattern across all files in workspace."""
    try:
        base_dir = Path(root) / path
        regex = re.compile(pattern, re.IGNORECASE)
        results = []

        ignore_dirs = {".git", "__pycache__", "node_modules", ".venv", "venv", ".idea", ".vscode", "dist", "build"}

        for root_dir, dirs, files in os.walk(base_dir):
            dirs[:] = [d for d in dirs if d not in ignore_dirs]
            for file in files:
                file_path = Path(root_dir) / file
                if file_path.suffix in {".pyc", ".png", ".jpg", ".jpeg", ".pth", ".bin", ".gguf", ".zip", ".tar", ".gz"}:
                    continue
                try:
                    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                        for idx, line in enumerate(f, 1):
                            if regex.search(line):
                                rel = file_path.relative_to(Path(root))
                                results.append({
                                    "file": str(rel),
                                    "line": idx,
                                    "text": line.strip()
                                })
                                if len(results) >= max_results:
                                    return {"success": True, "count": len(results), "matches": results, "truncated": True}
                except Exception:
                    continue

        return {"success": True, "count": len(results), "matches": results, "truncated": False}
    except Exception as e:
        return {"success": False, "error": str(e)}

async def find_files(name_pattern: str, path: str = ".", root: str = ".") -> Dict[str, Any]:
    """Find files by glob or regex name pattern."""
    try:
        base_dir = Path(root) / path
        matched = []
        pattern = re.compile(name_pattern.replace("*", ".*"), re.IGNORECASE)

        ignore_dirs = {".git", "__pycache__", "node_modules", ".venv", "venv"}

        for root_dir, dirs, files in os.walk(base_dir):
            dirs[:] = [d for d in dirs if d not in ignore_dirs]
            for file in files:
                if pattern.search(file):
                    full = Path(root_dir) / file
                    matched.append(str(full.relative_to(Path(root))))
                    if len(matched) >= 100:
                        break

        return {"success": True, "count": len(matched), "files": matched}
    except Exception as e:
        return {"success": False, "error": str(e)}
