import os
import sqlite3
import ast
from pathlib import Path
from typing import List, Dict, Any, Optional

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = PROJECT_ROOT / ".ghost_knowledge.db"

class KnowledgeBase:
    """
    Sovereign, zero-dependency Full-Text Search (FTS5) code & documentation knowledge base.
    Runs locally via SQLite FTS5 with BM25 relevance scoring inside the USB repository.
    """

    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or DB_PATH
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            # Create FTS5 virtual table for lightning-fast sub-millisecond BM25 keyword search
            cursor.execute("""
                CREATE VIRTUAL TABLE IF NOT EXISTS knowledge_fts USING fts5(
                    title,
                    category,
                    filepath,
                    content,
                    tokenize = 'porter unicode61'
                );
            """)
            conn.commit()

    def index_document(self, title: str, category: str, filepath: str, content: str) -> None:
        """Indexes or updates a document in the FTS5 catalog."""
        if not content.strip():
            return

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            # Clean existing entry for same filepath/title
            cursor.execute("DELETE FROM knowledge_fts WHERE filepath = ? AND title = ?", (filepath, title))
            cursor.execute("""
                INSERT INTO knowledge_fts (title, category, filepath, content)
                VALUES (?, ?, ?, ?)
            """, (title, category, filepath, content))
            conn.commit()

    def index_markdown_files(self, root_dir: Optional[Path] = None) -> int:
        """Indexes all project documentation and specification files."""
        root = root_dir or PROJECT_ROOT
        indexed = 0

        for md_file in root.glob("*.md"):
            try:
                text = md_file.read_text(encoding="utf-8", errors="ignore")
                rel_path = str(md_file.relative_to(root))
                self.index_document(
                    title=f"Doc: {md_file.stem.upper()}",
                    category="documentation",
                    filepath=rel_path,
                    content=text
                )
                indexed += 1
            except Exception:
                continue

        return indexed

    def index_python_codebase(self, root_dir: Optional[Path] = None) -> int:
        """Extracts AST docstrings, classes, and function signatures into the knowledge base."""
        root = root_dir or PROJECT_ROOT
        indexed = 0

        for py_file in root.rglob("*.py"):
            if any(ign in py_file.parts for ign in [".venv", "__pycache__", ".git", "wheels"]):
                continue

            try:
                code = py_file.read_text(encoding="utf-8", errors="ignore")
                rel_path = str(py_file.relative_to(root))
                tree = ast.parse(code)

                # Extract module docstring
                mod_doc = ast.get_docstring(tree) or ""
                if mod_doc:
                    self.index_document(
                        title=f"Module: {py_file.name}",
                        category="module_doc",
                        filepath=rel_path,
                        content=mod_doc
                    )
                    indexed += 1

                # Extract classes and methods
                for node in ast.walk(tree):
                    if isinstance(node, ast.ClassDef):
                        doc = ast.get_docstring(node) or "Class definition"
                        methods = [n.name for n in node.body if isinstance(n, ast.FunctionDef)]
                        body_summary = f"Class {node.name}\nMethods: {', '.join(methods)}\nDocstring: {doc}"
                        self.index_document(
                            title=f"Class: {node.name} ({py_file.name})",
                            category="class_spec",
                            filepath=rel_path,
                            content=body_summary
                        )
                        indexed += 1
                    elif isinstance(node, ast.FunctionDef) and not node.name.startswith("_"):
                        doc = ast.get_docstring(node) or "Function signature"
                        args = [a.arg for a in node.args.args]
                        sig = f"def {node.name}({', '.join(args)}):\n{doc}"
                        self.index_document(
                            title=f"Function: {node.name} ({py_file.name})",
                            category="function_spec",
                            filepath=rel_path,
                            content=sig
                        )
                        indexed += 1

            except Exception:
                continue

        return indexed

    def search(self, query: str, max_results: int = 5) -> List[Dict[str, Any]]:
        """
        Executes a BM25 ranked full-text query across all indexed code, specs, and docs.
        """
        cleaned_query = "".join(c if c.isalnum() or c in (" ", "_", "-") else " " for c in query).strip()
        if not cleaned_query:
            return []

        # Convert words into prefix matching terms for natural developer lookups
        terms = [f'"{w}"*' for w in cleaned_query.split() if len(w) > 1]
        if not terms:
            return []
        fts_query = " OR ".join(terms)

        results = []
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            try:
                cursor.execute("""
                    SELECT 
                        title, 
                        category, 
                        filepath, 
                        snippet(knowledge_fts, 3, '>>>', '<<<', '...', 20),
                        rank
                    FROM knowledge_fts 
                    WHERE knowledge_fts MATCH ? 
                    ORDER BY rank 
                    LIMIT ?
                """, (fts_query, max_results))

                for row in cursor.fetchall():
                    results.append({
                        "title": row[0],
                        "category": row[1],
                        "filepath": row[2],
                        "snippet": row[3],
                        "score": round(row[4], 3)
                    })
            except sqlite3.OperationalError:
                # Fallback to plain substring search if syntax matches special FTS keywords
                cursor.execute("""
                    SELECT title, category, filepath, substr(content, 1, 150), 0.0
                    FROM knowledge_fts
                    WHERE content LIKE ?
                    LIMIT ?
                """, (f"%{cleaned_query}%", max_results))
                for row in cursor.fetchall():
                    results.append({
                        "title": row[0],
                        "category": row[1],
                        "filepath": row[2],
                        "snippet": row[3],
                        "score": 0.0
                    })

        return results

    def clear(self):
        """Clears all knowledge records."""
        with sqlite3.connect(self.db_path) as conn:
            conn.cursor().execute("DELETE FROM knowledge_fts")
            conn.commit()

# Global Singleton
knowledge_base = KnowledgeBase()

if __name__ == "__main__":
    print("[*] Warming up Knowledge Base...")
    docs_count = knowledge_base.index_markdown_files()
    code_count = knowledge_base.index_python_codebase()
    print(f"[✔] Indexed {docs_count} docs and {code_count} code symbols into {DB_PATH.name}")
    
    test_q = "zero-spill VRAM 5400"
    matches = knowledge_base.search(test_q)
    print(f"\n[Test Search] Query: '{test_q}' -> {len(matches)} matches:")
    for m in matches:
        print(f"  - [{m['category']}] {m['title']} ({m['filepath']})")
