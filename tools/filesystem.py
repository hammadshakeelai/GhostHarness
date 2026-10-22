import os
import difflib
from pathlib import Path
from typing import Dict, Any, Optional

def _resolve_safe_path(rel_or_abs: str, root: str) -> Path:
    target = Path(rel_or_abs)
    if not target.is_absolute():
        target = Path(root) / target
    return target.resolve()

async def read_file(path: str, start_line: Optional[int] = None, end_line: Optional[int] = None, root: str = ".") -> Dict[str, Any]:
    """Read contents of a file with optional line bounds."""
    try:
        p = _resolve_safe_path(path, root)
        if not p.is_file():
            return {"success": False, "error": f"File not found: {path}"}

        with open(p, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()

        total = len(lines)
        s = (start_line - 1) if (start_line and start_line > 0) else 0
        e = end_line if (end_line and end_line > 0) else total

        selected = lines[s:e]
        return {
            "success": True,
            "path": str(p),
            "total_lines": total,
            "start_line": s + 1,
            "end_line": min(e, total),
            "content": "".join(selected)
        }
    except Exception as e:
        return {"success": False, "error": str(e)}

async def write_file(path: str, content: str, root: str = ".") -> Dict[str, Any]:
    """Write or overwrite content to a file."""
    try:
        p = _resolve_safe_path(path, root)
        p.parent.mkdir(parents=True, exist_ok=True)
        with open(p, "w", encoding="utf-8") as f:
            f.write(content)
        return {"success": True, "path": str(p), "bytes_written": len(content)}
    except Exception as e:
        return {"success": False, "error": str(e)}

async def edit_file(path: str, target: str, replacement: str, root: str = ".") -> Dict[str, Any]:
    """Perform surgical replacement in a file and generate a unified diff preview."""
    try:
        p = _resolve_safe_path(path, root)
        if not p.is_file():
            return {"success": False, "error": f"File not found: {path}"}

        with open(p, "r", encoding="utf-8") as f:
            original = f.read()

        if target not in original:
            return {
                "success": False,
                "error": "Target block not found in file. Ensure exact matching whitespace and indentation."
            }

        count = original.count(target)
        updated = original.replace(target, replacement, 1)

        diff = list(difflib.unified_diff(
            original.splitlines(keepends=True),
            updated.splitlines(keepends=True),
            fromfile=f"a/{path}",
            tofile=f"b/{path}",
            n=3
        ))
        diff_text = "".join(diff)

        with open(p, "w", encoding="utf-8") as f:
            f.write(updated)

        return {
            "success": True,
            "path": str(p),
            "occurrences_found": count,
            "diff": diff_text,
            "message": f"Successfully replaced target block ({len(diff)} diff lines generated)."
        }
    except Exception as e:
        return {"success": False, "error": str(e)}

async def list_directory(path: str = ".", root: str = ".") -> Dict[str, Any]:
    """List directory entries with file types and sizes."""
    try:
        p = _resolve_safe_path(path, root)
        if not p.is_dir():
            return {"success": False, "error": f"Not a directory: {path}"}

        entries = []
        for item in sorted(p.iterdir()):
            if item.name.startswith(".git") or item.name == "__pycache__":
                continue
            is_dir = item.is_dir()
            size = item.stat().st_size if not is_dir else 0
            entries.append({
                "name": item.name,
                "is_dir": is_dir,
                "size_bytes": size,
            })
        return {"success": True, "path": str(p), "entries": entries}
    except Exception as e:
        return {"success": False, "error": str(e)}
