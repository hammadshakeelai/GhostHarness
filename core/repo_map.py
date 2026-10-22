import ast
import os
from pathlib import Path
from typing import Dict, List, Any, Optional

class RepoMap:
    """
    Builds a compressed semantic AST map of the entire codebase.
    Inspired by Aider's repo map: fits the repository's symbol hierarchy
    (classes, methods, functions, docstrings) into a tight token budget (~500-1000 tokens),
    allowing 7B models to understand multi-file architectures without reading entire files.
    """

    def __init__(self, root_dir: str = ".", max_tokens: int = 1500):
        self.root_dir = Path(root_dir).resolve()
        self.max_tokens = max_tokens
        self.ignore_dirs = {
            ".git", "__pycache__", "node_modules", ".venv", "venv",
            "dist", "build", ".idea", ".vscode", "wheels", "models"
        }

    def generate_map(self) -> str:
        """Parses all Python and code files to produce a hierarchical symbol outline."""
        symbol_tree: Dict[str, List[str]] = {}

        for root, dirs, files in os.walk(self.root_dir):
            dirs[:] = [d for d in dirs if d not in self.ignore_dirs]
            for file in sorted(files):
                if not file.endswith(".py"):
                    continue
                file_path = Path(root) / file
                rel_path = file_path.relative_to(self.root_dir)
                symbols = self._extract_python_symbols(file_path)
                if symbols:
                    symbol_tree[str(rel_path)] = symbols

        # Format into clean condensed outline
        lines = ["# Codebase Semantic Symbol Map:"]
        for file_path, symbols in sorted(symbol_tree.items()):
            lines.append(f"\n{file_path}:")
            for sym in symbols:
                lines.append(f"  {sym}")

        result = "\n".join(lines)
        return self._truncate_to_budget(result)

    def _extract_python_symbols(self, file_path: Path) -> List[str]:
        symbols: List[str] = []
        try:
            content = file_path.read_text(encoding="utf-8", errors="ignore")
            tree = ast.parse(content)
        except Exception:
            return []

        for node in tree.body:
            if isinstance(node, ast.ClassDef):
                base_names = [self._get_name(b) for b in node.bases if self._get_name(b)]
                base_str = f"({', '.join(base_names)})" if base_names else ""
                symbols.append(f"class {node.name}{base_str}:")
                for item in node.body:
                    if isinstance(item, ast.FunctionDef) or isinstance(item, ast.AsyncFunctionDef):
                        args = self._format_args(item.args)
                        async_prefix = "async " if isinstance(item, ast.AsyncFunctionDef) else ""
                        symbols.append(f"    {async_prefix}def {item.name}({args})")
            elif isinstance(node, ast.FunctionDef) or isinstance(node, ast.AsyncFunctionDef):
                args = self._format_args(node.args)
                async_prefix = "async " if isinstance(node, ast.AsyncFunctionDef) else ""
                symbols.append(f"def {async_prefix}{node.name}({args})")

        return symbols

    def _get_name(self, node: ast.AST) -> Optional[str]:
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            return f"{self._get_name(node.value)}.{node.attr}"
        return None

    def _format_args(self, args: ast.arguments) -> str:
        arg_names = [a.arg for a in args.args if a.arg != "self"]
        if len(arg_names) > 4:
            return f"{', '.join(arg_names[:3])}, ..."
        return ", ".join(arg_names)

    def _truncate_to_budget(self, text: str) -> str:
        # Approximate 1 token ~= 4 chars
        char_limit = self.max_tokens * 4
        if len(text) > char_limit:
            return text[:char_limit] + "\n... [Remaining symbols truncated to preserve context budget]"
        return text
