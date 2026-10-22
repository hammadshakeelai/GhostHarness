import json
from typing import Dict, Any, List, AsyncGenerator, Optional
from core.config import settings
from core.engine import InferenceEngine
from core.dynamic_router import model_router
from core.memory_manager import memory_manager
from tools.base import Tool
from tools.filesystem import read_file, write_file, edit_file, list_directory
from tools.terminal import run_terminal
from tools.search import grep_search, find_files
from tools.researcher import analyze_repo_structure, fetch_web_doc

SYSTEM_PROMPT = """You are GhostHarness, an elite, sovereign autonomous coding agent running locally.
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
        self.tools: Dict[str, Tool] = self._register_tools()
        self.history: List[Dict[str, Any]] = [
            {"role": "system", "content": SYSTEM_PROMPT}
        ]

    def _register_tools(self) -> Dict[str, Tool]:
        root = self.workspace_root
        return {
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
                description="Surgically replace an exact target block with replacement text in a file.",
                parameters={
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "Relative file path"},
                        "target": {"type": "string", "description": "Exact text to find and replace"},
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
            )
        }

    def get_tool_schemas(self) -> List[Dict[str, Any]]:
        return [tool.to_openai_dict() for tool in self.tools.values()]

    async def execute_tool(self, name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        if name not in self.tools:
            return {"success": False, "error": f"Tool '{name}' not found."}
        return await self.tools[name].execute(**arguments)

    async def process_user_turn(self, user_prompt: str) -> AsyncGenerator[Dict[str, Any], None]:
        """Main agentic loop: Dynamic Routing -> Stream -> Tool Executions -> Loop."""
        # 1. Hardware check
        telemetry = memory_manager.get_hardware_telemetry()
        yield {"type": "telemetry", "data": telemetry}

        # 2. Dynamic model routing
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

            # Save assistant message to history
            asst_msg: Dict[str, Any] = {"role": "assistant"}
            if accumulated_content:
                asst_msg["content"] = accumulated_content
            if accumulated_tool_calls:
                asst_msg["tool_calls"] = list(accumulated_tool_calls.values())
            self.history.append(asst_msg)

            # If no tool calls were made, the turn is complete!
            if not accumulated_tool_calls:
                break

            # Process tool calls
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

                # Execute tool
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
