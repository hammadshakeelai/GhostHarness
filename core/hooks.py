"""
GhostHarness Lifecycle Hooks Engine
Provides deterministic interception points across the agent execution lifecycle:
- on_session_start: Hardware telemetry & knowledge base warmup
- pre_user_turn: VRAM headroom evaluation & auto-compaction
- pre_tool_call: Security validation & automated snapshot checkpointing
- post_tool_call: AST syntax verification & diff tracking
- post_user_turn: Telemetry logging & state persistence
"""

import sys
import ast
import time
import inspect
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from typing import Dict, Any, List, Callable, Optional
from core.checkpoint import checkpoint_manager
from core.memory_manager import memory_manager

class HookManager:
    def __init__(self):
        self._hooks: Dict[str, List[Callable]] = {
            "on_session_start": [],
            "pre_user_turn": [],
            "pre_tool_call": [],
            "post_tool_call": [],
            "post_user_turn": [],
            "on_error": []
        }
        self._install_default_hooks()

    def register(self, event_name: str):
        """Decorator to register a custom lifecycle hook."""
        def decorator(func: Callable):
            if event_name in self._hooks:
                self._hooks[event_name].append(func)
            return func
        return decorator

    def add_hook(self, event_name: str, func: Callable):
        """Adds a hook programmatically."""
        if event_name in self._hooks:
            self._hooks[event_name].append(func)

    async def trigger(self, event_name: str, **kwargs) -> Dict[str, Any]:
        """Dispatches an event across all registered hook handlers."""
        results = {}
        if event_name not in self._hooks:
            return results

        for hook in self._hooks[event_name]:
            try:
                if inspect.iscoroutinefunction(hook):
                    res = await hook(**kwargs)
                else:
                    res = hook(**kwargs)
                results[hook.__name__] = res
            except PermissionError as pe:
                # Re-raise security violations so pipeline halts immediately
                raise pe
            except Exception as e:
                results[hook.__name__] = {"hook_error": str(e)}

        return results

    def _install_default_hooks(self):
        """Installs core security, snapshot, and syntax verification guards."""

        # 1. Pre-tool: Automatic Checkpoint creation before mutating filesystem tools
        @self.register("pre_tool_call")
        def auto_checkpoint_guard(tool_name: str, arguments: Dict[str, Any], **kwargs):
            if tool_name in ("edit_file", "write_file"):
                target_file = arguments.get("path")
                if target_file:
                    chk_id = checkpoint_manager.create_checkpoint(
                        description=f"Auto-snapshot before {tool_name} on {target_file}",
                        files=[target_file]
                    )
                    return {"checkpoint_created": chk_id}
            return {"status": "skipped"}

        # 2. Pre-tool: Destructive command sanitization
        @self.register("pre_tool_call")
        def security_sanitizer(tool_name: str, arguments: Dict[str, Any], **kwargs):
            if tool_name == "run_terminal":
                cmd = arguments.get("command", "").lower()
                forbidden = [
                    "rm -rf /", ":(){ :|:& };:", "mkfs", "dd if=",
                    "rd /s /q c:", "format c:", "diskpart",
                    "remove-item -recurse -force c:", "del -recurse -force c:"
                ]
                for p in forbidden:
                    if p in cmd:
                        raise PermissionError(f"Rejected by GhostHarness Security Hook: Malicious command pattern ('{p}')")
            return {"status": "verified"}

        # 3. Post-tool: AST Python Syntax Validation
        @self.register("post_tool_call")
        def ast_syntax_verifier(tool_name: str, arguments: Dict[str, Any], result: Dict[str, Any], **kwargs):
            if tool_name in ("edit_file", "write_file") and result.get("success"):
                filepath = arguments.get("path", "")
                if filepath.endswith(".py"):
                    try:
                        p = Path(filepath)
                        if p.is_file():
                            code = p.read_text(encoding="utf-8", errors="ignore")
                            ast.parse(code)
                            result["ast_syntax_valid"] = True
                    except SyntaxError as e:
                        result["ast_syntax_valid"] = False
                        result["syntax_warning"] = f"CRITICAL: Syntax error introduced on line {e.lineno}: {e.msg}"
            return {"ast_check": result.get("ast_syntax_valid", None)}

        # 4. Pre-turn: Hardware Telemetry and Zero-Spill evaluation
        @self.register("pre_user_turn")
        def vram_telemetry_guard(**kwargs):
            t = memory_manager.get_hardware_telemetry()
            return {
                "vram_headroom_mb": 5400 - t["vram_used_mb"],
                "zero_spill": t["vram_percent"] < 90
            }

hook_manager = HookManager()

if __name__ == "__main__":
    import asyncio
    print("[*] Testing Hook Engine...")

    async def test_pipeline():
        # Test 1: pre_user_turn
        t_res = await hook_manager.trigger("pre_user_turn")
        print("  [Hook: pre_user_turn] Result:", t_res)

        # Test 2: pre_tool_call security guard
        sec_res = await hook_manager.trigger("pre_tool_call", tool_name="run_terminal", arguments={"command": "ls -la"})
        print("  [Hook: pre_tool_call (safe)] Result:", sec_res)

        try:
            await hook_manager.trigger("pre_tool_call", tool_name="run_terminal", arguments={"command": "rm -rf /"})
            print("  [!] Failed security check")
        except PermissionError as e:
            print("  [Hook: pre_tool_call (blocked attack)] Correctly intercepted:", e)

    asyncio.run(test_pipeline())
