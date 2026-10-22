import asyncio
import json
import os
from typing import Dict, Any, List, Optional
from tools.base import Tool

class MCPStdioClient:
    """
    Production-ready JSON-RPC 2.0 Model Context Protocol (MCP) stdio client.
    Spawns external MCP server subprocesses (e.g. Git MCP, Filesystem MCP, Postgres MCP)
    and exposes their tools natively to GhostHarness.
    """

    def __init__(self, command: str, args: Optional[List[str]] = None, env: Optional[Dict[str, str]] = None):
        self.command = command
        self.args = args or []
        self.env = env or os.environ.copy()
        self.process: Optional[asyncio.subprocess.Process] = None
        self._msg_id = 0
        self._pending_requests: Dict[int, asyncio.Future] = {}
        self._reader_task: Optional[asyncio.Task] = None
        self.tools: List[Dict[str, Any]] = []

    async def start(self) -> bool:
        """Starts the MCP server subprocess and performs initialization handshake."""
        try:
            self.process = await asyncio.create_subprocess_exec(
                self.command,
                *self.args,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=self.env
            )
            self._reader_task = asyncio.create_task(self._read_loop())

            # 1. MCP initialize handshake
            init_res = await self._send_request("initialize", {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "GhostHarness", "version": "0.1.0"}
            })

            # 2. Initialized notification
            await self._send_notification("notifications/initialized", {})

            # 3. Discover published tools
            tools_res = await self._send_request("tools/list", {})
            self.tools = tools_res.get("tools", [])
            return True
        except Exception as e:
            print(f"[MCP] Failed to initialize server {self.command}: {e}")
            return False

    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Dispatches a tool call to the MCP server."""
        try:
            res = await self._send_request("tools/call", {
                "name": tool_name,
                "arguments": arguments
            })
            return {"success": True, "result": res}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _send_request(self, method: str, params: Dict[str, Any], timeout: float = 30.0) -> Dict[str, Any]:
        self._msg_id += 1
        req_id = self._msg_id
        fut = asyncio.get_event_loop().create_future()
        self._pending_requests[req_id] = fut

        payload = {
            "jsonrpc": "2.0",
            "id": req_id,
            "method": method,
            "params": params
        }
        msg_bytes = json.dumps(payload).encode("utf-8") + b"\n"
        if self.process and self.process.stdin:
            self.process.stdin.write(msg_bytes)
            await self.process.stdin.drain()

        return await asyncio.wait_for(fut, timeout=timeout)

    async def _send_notification(self, method: str, params: Dict[str, Any]):
        payload = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params
        }
        msg_bytes = json.dumps(payload).encode("utf-8") + b"\n"
        if self.process and self.process.stdin:
            self.process.stdin.write(msg_bytes)
            await self.process.stdin.drain()

    async def _read_loop(self):
        if not self.process or not self.process.stdout:
            return
        while True:
            line = await self.process.stdout.readline()
            if not line:
                break
            try:
                msg = json.loads(line.decode("utf-8").strip())
                if "id" in msg and msg["id"] in self._pending_requests:
                    fut = self._pending_requests.pop(msg["id"])
                    if "result" in msg:
                        fut.set_result(msg["result"])
                    elif "error" in msg:
                        fut.set_exception(Exception(msg["error"].get("message", "MCP Error")))
            except Exception:
                continue

    async def close(self):
        if self._reader_task:
            self._reader_task.cancel()
        if self.process:
            try:
                self.process.terminate()
                await self.process.wait()
            except Exception:
                pass

class MCPManager:
    """Manages active MCP servers and converts their definitions into Agent Tools."""

    def __init__(self):
        self.servers: Dict[str, MCPStdioClient] = {}

    async def connect_server(self, name: str, command: str, args: Optional[List[str]] = None) -> List[Tool]:
        client = MCPStdioClient(command, args)
        success = await client.start()
        if not success:
            return []

        self.servers[name] = client
        adapted_tools: List[Tool] = []

        for t_spec in client.tools:
            t_name = f"{name}_{t_spec['name']}"
            tool = Tool(
                name=t_name,
                description=t_spec.get("description", ""),
                parameters=t_spec.get("inputSchema", {}),
                func=lambda **kwargs: client.call_tool(t_spec['name'], kwargs)
            )
            adapted_tools.append(tool)

        return adapted_tools

mcp_manager = MCPManager()
