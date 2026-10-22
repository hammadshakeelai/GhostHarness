import os
import difflib
from pathlib import Path
from typing import Dict, Any, Optional, List
from core.checkpoint import checkpoint_manager

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
    """Write or overwrite content to a file with automatic checkpointing."""
    try:
        p = _resolve_safe_path(path, root)
        rel_str = str(p.relative_to(Path(root).resolve())) if Path(root).resolve() in p.parents else path

        # Create checkpoint if file exists
        if p.is_file():
            checkpoint_manager.create_checkpoint(f"Before write to {rel_str}", [rel_str])

        p.parent.mkdir(parents=True, exist_ok=True)
        with open(p, "w", encoding="utf-8") as f:
            f.write(content)

        return {"success": True, "path": str(p), "bytes_written": len(content)}
    except Exception as e:
        return {"success": False, "error": str(e)}

async def edit_file(path: str, target: str, replacement: str, root: str = ".") -> Dict[str, Any]:
    """
    Surgical file editing with fuzzy matching fallback.
    If exact string match fails due to minor whitespace or indentation discrepancies
    from the 7B model, fuzzy locator locates the closest matching block.
    """
    try:
        p = _resolve_safe_path(path, root)
        if not p.is_file():
            return {"success": False, "error": f"File not found: {path}"}

        rel_str = str(p.relative_to(Path(root).resolve())) if Path(root).resolve() in p.parents else path

        with open(p, "r", encoding="utf-8") as f:
            original = f.read()

        match_found = False
        updated = original

        # 1. Exact match attempt
        if target in original:
            match_found = True
            updated = original.replace(target, replacement, 1)
        else:
            # 2. Indentation-normalized search
            target_lines = [line.strip() for line in target.strip().splitlines() if line.strip()]
            orig_lines = original.splitlines(keepends=True)
            orig_stripped = [line.strip() for line in orig_lines]

            # Slide window to find candidate block
            win_size = len(target_lines)
            best_ratio = 0.0
            best_idx = -1

            for i in range(len(orig_lines) - win_size + 1):
                window = [orig_stripped[j] for j in range(i, i + win_size) if orig_stripped[j]]
                ratio = difflib.SequenceMatcher(None, target_lines, window).ratio()
                if ratio > best_ratio:
                    best_ratio = ratio
                    best_idx = i

            # If similarity is >= 85%, accept fuzzy match
            if best_ratio >= 0.85 and best_idx != -1:
                match_found = True
                matched_block = "".join(orig_lines[best_idx : best_idx + win_size])
                updated = original.replace(matched_block, replacement, 1)

        if not match_found:
            return {
                "success": False,
                "error": "Target block not found in file (neither exact nor fuzzy match above 85% similarity)."
            }

        # Create checkpoint before committing modification
        checkpoint_manager.create_checkpoint(f"Before edit_file on {rel_str}", [rel_str])

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
            "diff": diff_text,
            "message": f"Successfully applied edit ({len(diff)} diff lines generated)."
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
            if item.name.startswith(".git") or item.name in {"__pycache__", ".ghost_checkpoints"}:
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
