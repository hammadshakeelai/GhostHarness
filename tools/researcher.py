import ast
import httpx
from pathlib import Path
from typing import Dict, Any, List

async def analyze_repo_structure(repo_path: str = ".", root: str = ".") -> Dict[str, Any]:
    """Inspects a codebase and generates a semantic architecture summary (AST classes, functions, files)."""
    try:
        base = Path(root) / repo_path
        if not base.is_dir():
            return {"success": False, "error": f"Invalid directory: {repo_path}"}

        summary: Dict[str, Any] = {
            "root": str(base),
            "files": [],
            "python_symbols": {},
            "dependencies": []
        }

        # Check for dependency manifests
        for dep_file in ["requirements.txt", "pyproject.toml", "package.json", "Cargo.toml", "go.mod"]:
            df = base / dep_file
            if df.is_file():
                try:
                    summary["dependencies"].append({
                        "file": dep_file,
                        "snippet": df.read_text(encoding="utf-8", errors="ignore")[:500]
                    })
                except Exception:
                    pass

        # Parse Python files via AST
        for p in base.rglob("*.py"):
            if any(part in {".git", ".venv", "venv", "__pycache__"} for part in p.parts):
                continue
            rel = str(p.relative_to(base))
            summary["files"].append(rel)
            try:
                content = p.read_text(encoding="utf-8", errors="ignore")
                tree = ast.parse(content)
                classes = [n.name for n in ast.walk(tree) if isinstance(n, ast.ClassDef)]
                functions = [n.name for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]
                if classes or functions:
                    summary["python_symbols"][rel] = {
                        "classes": classes,
                        "functions": functions
                    }
            except Exception:
                continue

        return {"success": True, "analysis": summary}
    except Exception as e:
        return {"success": False, "error": str(e)}

async def fetch_web_doc(url: str) -> Dict[str, Any]:
    """Fetches web documentation or raw GitHub readme for studying new technologies."""
    try:
        headers = {"User-Agent": "GhostHarness-Researcher/1.0"}
        async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
            resp = await client.get(url, headers=headers)
            if resp.status_code == 200:
                text = resp.text
                return {
                    "success": True,
                    "url": url,
                    "status_code": resp.status_code,
                    "content": text[:15000],  # truncated to preserve context budget
                    "length": len(text)
                }
            return {"success": False, "error": f"HTTP {resp.status_code}"}
    except Exception as e:
        return {"success": False, "error": str(e)}
