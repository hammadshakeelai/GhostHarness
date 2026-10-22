import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATASETS_DIR = PROJECT_ROOT / "datasets"
DATASETS_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_FILE = DATASETS_DIR / "distilled_agent_dataset.jsonl"

FRONTIER_TRACES = [
    {
        "messages": [
            {
                "role": "system",
                "content": "You are GhostHarness, an elite autonomous software engineering agent running locally with direct tool access."
            },
            {
                "role": "user",
                "content": "In `core/memory_manager.py`, the GPU VRAM threshold is hardcoded to 5400 MB. Please make it configurable via the constructor while preserving 5400 as the default, and update the spill evaluation logic accordingly."
            },
            {
                "role": "assistant",
                "content": "I will inspect `core/memory_manager.py` to see how `max_vram_mb` is initialized and used. I will use `read_file` to examine the constructor and `_evaluate_headroom` method.\n\n```json\n{\n  \"tool\": \"read_file\",\n  \"arguments\": {\n    \"path\": \"core/memory_manager.py\",\n    \"start_line\": 1,\n    \"end_line\": 30\n  }\n}\n```"
            },
            {
                "role": "tool",
                "content": "{\"success\": true, \"path\": \"core/memory_manager.py\", \"start_line\": 1, \"end_line\": 30, \"content\": \"import os\\nimport psutil\\nfrom typing import Dict, Any\\n\\nclass MemoryManager:\\n    def __init__(self, max_vram_mb: int = 5400, max_ram_mb: int = 26000):\\n        self.max_vram_mb = max_vram_mb\\n        self.max_ram_mb = max_ram_mb\"}"
            },
            {
                "role": "assistant",
                "content": "The constructor already accepts `max_vram_mb`. Now let's examine `_evaluate_headroom` around line 80 to verify how threshold warnings are formatted.\n\n```json\n{\n  \"tool\": \"read_file\",\n  \"arguments\": {\n    \"path\": \"core/memory_manager.py\",\n    \"start_line\": 75,\n    \"end_line\": 100\n  }\n}\n```"
            },
            {
                "role": "tool",
                "content": "{\"success\": true, \"path\": \"core/memory_manager.py\", \"start_line\": 75, \"end_line\": 95, \"content\": \"    def _evaluate_headroom(self, vram_used: float, ram_pct: float) -> str:\\n        if vram_used >= self.max_vram_mb:\\n            return \\\"CRITICAL: VRAM threshold exceeded. Spill risk into system RAM! Auto-throttling KV cache.\\\"\\n        elif vram_used >= (self.max_vram_mb - 500):\\n            return \\\"WARNING: Approaching 6GB VRAM limit. Safe operating ceiling near.\\\"\\n        return \\\"OPTIMAL: Zero GPU memory spill. Operating at peak VRAM speed.\\\"\"}"
            },
            {
                "role": "assistant",
                "content": "In `_evaluate_headroom`, the warning message hardcodes 'Approaching 6GB VRAM limit' instead of referencing `self.max_vram_mb`. I will use `edit_file` to dynamically format the ceiling based on `self.max_vram_mb / 1024`.\n\n```json\n{\n  \"tool\": \"edit_file\",\n  \"arguments\": {\n    \"path\": \"core/memory_manager.py\",\n    \"target\": \"        elif vram_used >= (self.max_vram_mb - 500):\\n            return \\\"WARNING: Approaching 6GB VRAM limit. Safe operating ceiling near.\\\"\",\n    \"replacement\": \"        elif vram_used >= (self.max_vram_mb - 500):\\n            limit_gb = self.max_vram_mb / 1024\\n            return f\\\"WARNING: Approaching {limit_gb:.1f}GB VRAM threshold. Headroom critical.\\\"\"\n  }\n}\n```"
            },
            {
                "role": "tool",
                "content": "{\"success\": true, \"path\": \"core/memory_manager.py\", \"diff\": \"--- a/core/memory_manager.py\\n+++ b/core/memory_manager.py\\n@@ -80,2 +80,3 @@\\n-        elif vram_used >= (self.max_vram_mb - 500):\\n-            return \\\"WARNING: Approaching 6GB VRAM limit. Safe operating ceiling near.\\\"\\n+        elif vram_used >= (self.max_vram_mb - 500):\\n+            limit_gb = self.max_vram_mb / 1024\\n+            return f\\\"WARNING: Approaching {limit_gb:.1f}GB VRAM threshold. Headroom critical.\\\"\"}"
            },
            {
                "role": "assistant",
                "content": "The VRAM evaluation logic in `core/memory_manager.py` has been updated. The warning message now dynamically interpolates `self.max_vram_mb / 1024` rather than assuming a static 6GB string, ensuring accurate telemetry reports across different GPU configurations."
            }
        ]
    },
    {
        "messages": [
            {
                "role": "system",
                "content": "You are GhostHarness, an elite autonomous software engineering agent running locally with direct tool access."
            },
            {
                "role": "user",
                "content": "Running tests produced an uncaught `ZeroDivisionError` when calculating token velocity in `core/cli.py` during idle sessions. Fix it surgically."
            },
            {
                "role": "assistant",
                "content": "Let me search for where velocity or duration division occurs in `core/cli.py` using `grep_search`.\n\n```json\n{\n  \"tool\": \"grep_search\",\n  \"arguments\": {\n    \"pattern\": \"tokens?_per_sec|elapsed\",\n    \"path\": \"core/cli.py\"\n  }\n}\n```"
            },
            {
                "role": "tool",
                "content": "{\"success\": true, \"matches\": [{\"file\": \"core/cli.py\", \"line\": 82, \"text\": \"tok_speed = total_tokens / elapsed_time\"}]}"
            },
            {
                "role": "assistant",
                "content": "Line 82 has `tok_speed = total_tokens / elapsed_time` without guarding against `elapsed_time == 0` or negligible duration. I will read lines 75-90 of `core/cli.py` to see the context.\n\n```json\n{\n  \"tool\": \"read_file\",\n  \"arguments\": {\n    \"path\": \"core/cli.py\",\n    \"start_line\": 75,\n    \"end_line\": 90\n  }\n}\n```"
            },
            {
                "role": "tool",
                "content": "{\"success\": true, \"content\": \"            elapsed_time = end_t - start_t\\n            tok_speed = total_tokens / elapsed_time\\n            console.print(f\\\"Speed: {tok_speed:.1f} t/s\\\")\"}"
            },
            {
                "role": "assistant",
                "content": "I will apply a surgical edit to prevent `ZeroDivisionError` by checking `if elapsed_time > 0.001` before dividing.\n\n```json\n{\n  \"tool\": \"edit_file\",\n  \"arguments\": {\n    \"path\": \"core/cli.py\",\n    \"target\": \"            elapsed_time = end_t - start_t\\n            tok_speed = total_tokens / elapsed_time\",\n    \"replacement\": \"            elapsed_time = end_t - start_t\\n            tok_speed = (total_tokens / elapsed_time) if elapsed_time > 0.001 else 0.0\"\n  }\n}\n```"
            },
            {
                "role": "tool",
                "content": "{\"success\": true, \"diff\": \"--- a/core/cli.py\\n+++ b/core/cli.py\\n@@ -76,2 +76,2 @@\\n             elapsed_time = end_t - start_t\\n-            tok_speed = total_tokens / elapsed_time\\n+            tok_speed = (total_tokens / elapsed_time) if elapsed_time > 0.001 else 0.0\"}"
            },
            {
                "role": "assistant",
                "content": "I have patched line 82 in `core/cli.py`. Token velocity calculation now guards against division by zero using a ternary check (`elapsed_time > 0.001`), completely eliminating the crash during instantaneous or idle turns."
            }
        ]
    },
    {
        "messages": [
            {
                "role": "system",
                "content": "You are GhostHarness, an elite autonomous software engineering agent running locally with direct tool access."
            },
            {
                "role": "user",
                "content": "Check if our Windows launcher `scripts/launch.bat` properly redirects Hugging Face and PyTorch cache directories so they do not write to the student's C:\\ drive."
            },
            {
                "role": "assistant",
                "content": "I will read `scripts/launch.bat` to verify how environment variables for cache directories (`HF_HOME`, `TORCH_HOME`) are declared.\n\n```json\n{\n  \"tool\": \"read_file\",\n  \"arguments\": {\n    \"path\": \"scripts/launch.bat\",\n    \"start_line\": 1,\n    \"end_line\": 25\n  }\n}\n```"
            },
            {
                "role": "tool",
                "content": "{\"success\": true, \"content\": \"@echo off\\nset HF_HOME=%CD%\\\\.cache\\\\huggingface\\nset TORCH_HOME=%CD%\\\\.cache\\\\torch\\nset PYTHONPYCACHEPREFIX=%CD%\\\\.cache\\\\pycache\\nset PYTHONPATH=%CD%;%PYTHONPATH%\"}"
            },
            {
                "role": "assistant",
                "content": "`scripts/launch.bat` correctly isolates all caches to the local USB/repo directory:\n1. `HF_HOME=%CD%\\.cache\\huggingface`: Forces Hugging Face transformers/datasets to download into the USB folder instead of `%USERPROFILE%\\.cache\\huggingface`.\n2. `TORCH_HOME=%CD%\\.cache\\torch`: Isolates PyTorch hub and model checkpoint weights.\n3. `PYTHONPYCACHEPREFIX=%CD%\\.cache\\pycache`: Redirects bytecode `.pyc` files away from system directories.\n\nEverything operates in user-space without touching `C:\\Users\\...\\AppData`, ensuring complete self-containment."
            }
        ]
    },
    {
        "messages": [
            {
                "role": "system",
                "content": "You are GhostHarness, an elite autonomous software engineering agent running locally with direct tool access."
            },
            {
                "role": "user",
                "content": "We need an AST-based helper function in `tools/search.py` that lists all async functions in a Python file. Add `find_async_functions(file_path: str)`."
            },
            {
                "role": "assistant",
                "content": "I will inspect `tools/search.py` to see existing imports and AST search patterns.\n\n```json\n{\n  \"tool\": \"read_file\",\n  \"arguments\": {\n    \"path\": \"tools/search.py\",\n    \"start_line\": 1,\n    \"end_line\": 30\n  }\n}\n```"
            },
            {
                "role": "tool",
                "content": "{\"success\": true, \"content\": \"import os\\nimport re\\nfrom pathlib import Path\\nfrom typing import Dict, Any, List\"}"
            },
            {
                "role": "assistant",
                "content": "I will import `ast` and append the new `find_async_functions` function at the bottom of `tools/search.py`.\n\n```json\n{\n  \"tool\": \"edit_file\",\n  \"arguments\": {\n    \"path\": \"tools/search.py\",\n    \"target\": \"import re\",\n    \"replacement\": \"import re\\nimport ast\"\n  }\n}\n```"
            },
            {
                "role": "tool",
                "content": "{\"success\": true, \"diff\": \"--- a/tools/search.py\\n+++ b/tools/search.py\\n@@ -2,1 +2,2 @@\\n import re\\n+import ast\"}"
            },
            {
                "role": "assistant",
                "content": "Now I will append the implementation of `find_async_functions` using `ast.walk` to identify `ast.AsyncFunctionDef` nodes.\n\n```json\n{\n  \"tool\": \"read_file\",\n  \"arguments\": {\n    \"path\": \"tools/search.py\",\n    \"start_line\": 50,\n    \"end_line\": 70\n  }\n}\n```"
            },
            {
                "role": "tool",
                "content": "{\"success\": true, \"content\": \"        return {\\\"success\\\": True, \\\"count\\\": len(matched), \\\"files\\\": matched}\\n    except Exception as e:\\n        return {\\\"success\\\": False, \\\"error\\\": str(e)}\"}"
            },
            {
                "role": "assistant",
                "content": "I will use `edit_file` to attach `find_async_functions` after the last function.\n\n```json\n{\n  \"tool\": \"edit_file\",\n  \"arguments\": {\n    \"path\": \"tools/search.py\",\n    \"target\": \"        return {\\\"success\\\": False, \\\"error\\\": str(e)}\",\n    \"replacement\": \"        return {\\\"success\\\": False, \\\"error\\\": str(e)}\\n\\nasync def find_async_functions(file_path: str, root: str = \\\".\\\") -> Dict[str, Any]:\\n    \\\"\\\"\\\"Extracts names of all async functions defined in a Python module.\\\"\\\"\\\"\\n    try:\\n        p = Path(root) / file_path\\n        tree = ast.parse(p.read_text(encoding=\\\"utf-8\\\", errors=\\\"ignore\\\"))\\n        async_funcs = [node.name for node in ast.walk(tree) if isinstance(node, ast.AsyncFunctionDef)]\\n        return {\\\"success\\\": True, \\\"file\\\": file_path, \\\"async_functions\\\": async_funcs}\\n    except Exception as e:\\n        return {\\\"success\\\": False, \\\"error\\\": str(e)}\"\n  }\n}\n```"
            },
            {
                "role": "tool",
                "content": "{\"success\": true, \"diff\": \"--- a/tools/search.py\\n+++ b/tools/search.py\\n@@ -65,1 +65,11 @@\\n         return {\\\"success\\\": False, \\\"error\\\": str(e)}\\n+\\n+async def find_async_functions(file_path: str, root: str = \\\".\\\") -> Dict[str, Any]:\\n+    \\\"\\\"\\\"Extracts names of all async functions defined in a Python module.\\\"\\\"\\\"\\n+    try:\\n+        p = Path(root) / file_path\\n+        tree = ast.parse(p.read_text(encoding=\\\"utf-8\\\", errors=\\\"ignore\\\"))\\n+        async_funcs = [node.name for node in ast.walk(tree) if isinstance(node, ast.AsyncFunctionDef)]\\n+        return {\\\"success\\\": True, \\\"file\\\": file_path, \\\"async_functions\\\": async_funcs}\\n+    except Exception as e:\\n+        return {\\\"success\\\": False, \\\"error\\\": str(e)}\"}"
            },
            {
                "role": "assistant",
                "content": "Added `find_async_functions(file_path, root)` to `tools/search.py`. It reads the module, generates an AST syntax tree, and inspects all `ast.AsyncFunctionDef` nodes to return a list of asynchronous function names safely without executing module-level code."
            }
        ]
    },
    {
        "messages": [
            {
                "role": "system",
                "content": "You are GhostHarness, an elite autonomous software engineering agent running locally with direct tool access."
            },
            {
                "role": "user",
                "content": "We noticed that when running on 6GB VRAM GPUs, Qwen 2.5 Coder 14B offloads too many layers to GPU by default, risking out-of-memory. How do we tune layer offload count in `llama-server`?"
            },
            {
                "role": "assistant",
                "content": "I will inspect `core/engine.py` to see where `llama-server` arguments are specified.\n\n```json\n{\n  \"tool\": \"grep_search\",\n  \"arguments\": {\n    \"pattern\": \"-ngl\",\n    \"path\": \"core/engine.py\"\n  }\n}\n```"
            },
            {
                "role": "tool",
                "content": "{\"success\": true, \"matches\": [{\"file\": \"core/engine.py\", \"line\": 92, \"text\": \"            \\\"-ngl\\\", \\\"33\\\",\"}]}"
            },
            {
                "role": "assistant",
                "content": "In `core/engine.py`, `-ngl 33` offloads all 33 layers of a 7B model. For a 14B model (which has 48 layers and ~9GB unquantized weights), offloading all layers will exceed 6GB VRAM. To fit within 5.2GB usable VRAM with an 8k KV cache, exactly 24–26 layers should be offloaded to the discrete GPU (`-ngl 26`), while the remaining 22 layers stay in the 32GB system RAM.\n\nTo configure this dynamically, `-ngl` can be adjusted based on model size or set via configuration."
            }
        ]
    },
    {
        "messages": [
            {
                "role": "system",
                "content": "You are GhostHarness, an elite autonomous software engineering agent running locally with direct tool access."
            },
            {
                "role": "user",
                "content": "A student accidentally executed a destructive file modification. How can they revert it using GhostHarness?"
            },
            {
                "role": "assistant",
                "content": "GhostHarness automatically takes an atomic pre-modification snapshot in `.ghost_checkpoints/` before every `write_file` or `edit_file` execution.\n\nTo undo the modification, the student can:\n1. In the Web Visual Workspace: Click the **`↺ Undo`** button in the header.\n2. In the Terminal TUI: Type **`/undo`**.\n3. Programmatically or via agent: Call the tool `rollback_checkpoint()`.\n\nLet me demonstrate by invoking `rollback_checkpoint`.\n\n```json\n{\n  \"tool\": \"rollback_checkpoint\",\n  \"arguments\": {}\n}\n```"
            },
            {
                "role": "tool",
                "content": "{\"success\": true, \"id\": \"chk_1729642010\", \"description\": \"Before edit_file on config.py\", \"restored_files\": [\"config.py\"], \"remaining_checkpoints\": 4}"
            },
            {
                "role": "assistant",
                "content": "The rollback succeeded. Snapshot `chk_1729642010` was restored, reverting `config.py` back to its pre-modification state. All backup files are stored locally on the USB in `.ghost_checkpoints/` and can be reverted sequentially across up to 15 historical states."
            }
        ]
    }
]

def append_frontier_traces():
    count = 0
    with open(OUTPUT_FILE, "a", encoding="utf-8") as f:
        for t in FRONTIER_TRACES:
            f.write(json.dumps(t) + "\n")
            count += 1
    print(f"[✔] Appended {count} curated frontier agent traces to {OUTPUT_FILE}")

if __name__ == "__main__":
    append_frontier_traces()
