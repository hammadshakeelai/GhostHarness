import json
from typing import Dict, Any, List, AsyncGenerator, Optional
from core.config import settings
from core.engine import InferenceEngine
from core.dynamic_router import model_router
from core.memory_manager import memory_manager
from core.repo_map import RepoMap
from core.checkpoint import checkpoint_manager
from core.multimodal import multimodal_sidecar
from core.knowledge_base import knowledge_base
from core.hooks import hook_manager
from tools.base import Tool
from tools.filesystem import read_file, write_file, edit_file, list_directory
from tools.terminal import run_terminal
from tools.search import grep_search, find_files
from tools.researcher import analyze_repo_structure, fetch_web_doc

BASE_SYSTEM_PROMPT = """You are GhostHarness, an elite sovereign autonomous coding agent running locally.
You are powered by an abliterated Qwen model with zero refusals and direct access to system tools.
You are executing on a computer with constrained 6GB VRAM + 32GB RAM.

Your operating principles:
1. Always analyze before executing destructive changes.
2. When modifying files, prefer 'edit_file' with exact string targets rather than rewriting entire files.
3. Keep answers concise, technical, and tool-driven.
4. Run commands safely in user-space without assuming root or sudo privileges.
5. If an error occurs, inspect the error message, formulate a hypothesis, and test the fix.
"""

class Agent:
    def __init__(self, workspace_root: Optional[str] = None):
        self.workspace_root = workspace_root or settings.agent.workspace_root
        self.engine = InferenceEngine()
        self.repo_map = RepoMap(root_dir=self.workspace_root)
        self.tools: Dict[str, Tool] = self._register_tools()
        self.history: List[Dict[str, Any]] = []
        self._init_history()

    def _init_history(self):
        # Generate initial semantic repo map
        rmap = self.repo_map.generate_map()
        sys_content = f"{BASE_SYSTEM_PROMPT}\n\n{rmap}"
        self.history = [{"role": "system", "content": sys_content}]

    def _register_tools(self) -> Dict[str, Tool]:
        root = self.workspace_root
        tools = {
            "read_file": Tool(
                name="read_file",
                description="Read lines or full content of a file.",
                parameters={
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "Relative file path"},
                        "start_line": {"type": "integer", "description": "1-based starting line number"},
                        "end_line": {"type": "integer", "description": "1-based ending line number"}
                    },
                    "required": ["path"]
                },
                func=lambda path, start_line=None, end_line=None: read_file(path, start_line, end_line, root=root)
            ),
            "write_file": Tool(
                name="write_file",
                description="Create or overwrite a file with full content.",
                parameters={
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "Relative file path"},
                        "content": {"type": "string", "description": "File text content"}
                    },
                    "required": ["path", "content"]
                },
                func=lambda path, content: write_file(path, content, root=root)
            ),
            "edit_file": Tool(
                name="edit_file",
                description="Surgically replace a target block with replacement text with fuzzy-matching fallback.",
                parameters={
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "Relative file path"},
                        "target": {"type": "string", "description": "Exact or near-exact text to replace"},
                        "replacement": {"type": "string", "description": "New replacement text"}
                    },
                    "required": ["path", "target", "replacement"]
                },
                func=lambda path, target, replacement: edit_file(path, target, replacement, root=root)
            ),
            "list_directory": Tool(
                name="list_directory",
                description="List contents of a directory with file sizes.",
                parameters={
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "Directory path", "default": "."}
                    }
                },
                func=lambda path=".": list_directory(path, root=root)
            ),
            "run_terminal": Tool(
                name="run_terminal",
                description="Run shell command in user-space without sudo.",
                parameters={
                    "type": "object",
                    "properties": {
                        "command": {"type": "string", "description": "Shell command line to execute"},
                        "cwd": {"type": "string", "description": "Working directory", "default": "."}
                    },
                    "required": ["command"]
                },
                func=lambda command, cwd=".": run_terminal(command, cwd=cwd)
            ),
            "grep_search": Tool(
                name="grep_search",
                description="Search for regex or keyword across all code files.",
                parameters={
                    "type": "object",
                    "properties": {
                        "pattern": {"type": "string", "description": "Regex or keyword to search for"},
                        "path": {"type": "string", "description": "Subdirectory to search in", "default": "."}
                    },
                    "required": ["pattern"]
                },
                func=lambda pattern, path=".": grep_search(pattern, path, root=root)
            ),
            "find_files": Tool(
                name="find_files",
                description="Find files by name or glob pattern.",
                parameters={
                    "type": "object",
                    "properties": {
                        "name_pattern": {"type": "string", "description": "Glob or regex pattern (e.g. *.py, test_*)"},
                        "path": {"type": "string", "description": "Directory to search", "default": "."}
                    },
                    "required": ["name_pattern"]
                },
                func=lambda name_pattern, path=".": find_files(name_pattern, path, root=root)
            ),
            "analyze_repo_structure": Tool(
                name="analyze_repo_structure",
                description="Analyze codebase AST classes, functions, and dependencies.",
                parameters={
                    "type": "object",
                    "properties": {
                        "repo_path": {"type": "string", "description": "Subdirectory path", "default": "."}
                    }
                },
                func=lambda repo_path=".": analyze_repo_structure(repo_path, root=root)
            ),
            "fetch_web_doc": Tool(
                name="fetch_web_doc",
                description="Fetch external web documentation or GitHub raw file.",
                parameters={
                    "type": "object",
                    "properties": {
                        "url": {"type": "string", "description": "HTTP/HTTPS URL"}
                    },
                    "required": ["url"]
                },
                func=lambda url: fetch_web_doc(url)
            ),
            "rollback_checkpoint": Tool(
                name="rollback_checkpoint",
                description="Revert the most recent file modification checkpoint (undo changes).",
                parameters={
                    "type": "object",
                    "properties": {}
                },
                func=lambda: checkpoint_manager.rollback_latest()
            ),
            "inspect_image": Tool(
                name="inspect_image",
                description="Analyze a local image or screenshot via vision model.",
                parameters={
                    "type": "object",
                    "properties": {
                        "image_path": {"type": "string", "description": "Path to PNG/JPG image"},
                        "question": {"type": "string", "description": "Question or instruction for vision model"}
                    },
                    "required": ["image_path"]
                },
                func=lambda image_path, question="Analyze this image": multimodal_sidecar.inspect_image(image_path, question)
            ),
            "search_knowledge_base": Tool(
                name="search_knowledge_base",
                description="Query local architecture specifications, documentation, and codebase symbols via BM25 search.",
                parameters={
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Keywords to search in documentation and codebase specs"},
                        "max_results": {"type": "integer", "description": "Maximum number of results to return", "default": 5}
                    },
                    "required": ["query"]
                },
                func=lambda query, max_results=5: {"success": True, "matches": knowledge_base.search(query, max_results)}
            )
        }
        return tools

    def get_tool_schemas(self) -> List[Dict[str, Any]]:
        return [tool.to_openai_dict() for tool in self.tools.values()]

    async def execute_tool(self, name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        if name not in self.tools:
            return {"success": False, "error": f"Tool '{name}' not found."}

        # Lifecycle Hook: Pre-tool call (Security & Checkpointing)
        try:
            await hook_manager.trigger("pre_tool_call", tool_name=name, arguments=arguments)
        except PermissionError as pe:
            return {"success": False, "error": str(pe)}

        res = await self.tools[name].execute(**arguments)

        # Lifecycle Hook: Post-tool call (AST verification & Diff recording)
        await hook_manager.trigger("post_tool_call", tool_name=name, arguments=arguments, result=res)
        return res

    def compact_history_if_needed(self):
        """Compacts conversation history when token estimate exceeds 70% of context window."""
        total_chars = sum(len(str(m.get("content", ""))) for m in self.history)
        # Approximate 1 token ~= 4 chars (8192 tokens ~= 32000 chars)
        if total_chars > 24000 and len(self.history) > 6:
            # Preserve system prompt and latest 4 messages; compact middle turns
            system_msg = self.history[0]
            recent_turns = self.history[-4:]
            compacted_summary = {
                "role": "user",
                "content": "[Context Compacted: Earlier steps executed file edits and research successfully. Continuing task.]"
            }
            self.history = [system_msg, compacted_summary] + recent_turns

    async def process_user_turn(self, user_prompt: str) -> AsyncGenerator[Dict[str, Any], None]:
        """Main agentic loop: Telemetry -> Dynamic Routing -> Stream -> Tool Calls -> Compaction."""
        # Check for undo command
        if user_prompt.strip().lower() in ["/undo", "undo"]:
            undo_res = checkpoint_manager.rollback_latest()
            yield {"type": "token", "content": f"Rollback status: {json.dumps(undo_res, indent=2)}"}
            yield {"type": "done", "iterations": 1}
            return

        self.compact_history_if_needed()

        # Lifecycle Hook: Pre-user turn
        await hook_manager.trigger("pre_user_turn", prompt=user_prompt, history=self.history)

        telemetry = memory_manager.get_hardware_telemetry()
        yield {"type": "telemetry", "data": telemetry}

        route_decision = model_router.select_model(user_prompt, self.history)
        yield {
            "type": "routing",
            "model": route_decision["model"],
            "tier": route_decision["tier"],
            "reason": route_decision["reason"]
        }

        self.history.append({"role": "user", "content": user_prompt})

        iteration = 0
        max_iter = settings.agent.max_tool_iterations

        while iteration < max_iter:
            iteration += 1
            tools_spec = self.get_tool_schemas()

            accumulated_content = ""
            accumulated_tool_calls: Dict[int, Dict[str, Any]] = {}

            async for chunk in self.engine.stream_chat(
                messages=self.history,
                model=route_decision["model"],
                tools=tools_spec,
                temperature=settings.models.temperature
            ):
                c_type = chunk.get("type")
                if c_type == "content":
                    accumulated_content += chunk["content"]
                    yield {"type": "token", "content": chunk["content"]}
                elif c_type == "tool_calls":
                    for tc in chunk["tool_calls"]:
                        idx = tc.get("index", 0)
                        if idx not in accumulated_tool_calls:
                            accumulated_tool_calls[idx] = {
                                "id": tc.get("id", f"call_{idx}"),
                                "type": "function",
                                "function": {"name": "", "arguments": ""}
                            }
                        if "function" in tc:
                            if "name" in tc["function"] and tc["function"]["name"]:
                                accumulated_tool_calls[idx]["function"]["name"] += tc["function"]["name"]
                            if "arguments" in tc["function"] and tc["function"]["arguments"]:
                                accumulated_tool_calls[idx]["function"]["arguments"] += tc["function"]["arguments"]

            asst_msg: Dict[str, Any] = {"role": "assistant"}
            if accumulated_content:
                asst_msg["content"] = accumulated_content
            if accumulated_tool_calls:
                asst_msg["tool_calls"] = list(accumulated_tool_calls.values())
            self.history.append(asst_msg)

            if not accumulated_tool_calls:
                break

            for idx, tc in accumulated_tool_calls.items():
                fn_name = tc["function"]["name"]
                raw_args = tc["function"]["arguments"]
                try:
                    args = json.loads(raw_args) if raw_args else {}
                except Exception:
                    args = {}

                yield {
                    "type": "tool_start",
                    "id": tc["id"],
                    "tool": fn_name,
                    "arguments": args
                }

                result = await self.execute_tool(fn_name, args)

                yield {
                    "type": "tool_end",
                    "id": tc["id"],
                    "tool": fn_name,
                    "result": result
                }

                self.history.append({
                    "role": "tool",
                    "tool_call_id": tc["id"],
                    "name": fn_name,
                    "content": json.dumps(result)
                })

        yield {"type": "done", "iterations": iteration}
