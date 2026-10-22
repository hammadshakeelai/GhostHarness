import json
import asyncio
from pathlib import Path
from typing import Dict, Any, List
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, StreamingResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from core.config import settings
from core.memory_manager import memory_manager
from core.agent import Agent
from core.engine import InferenceEngine

app = FastAPI(title="GhostHarness Visual Workspace")

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
STATIC_DIR.mkdir(parents=True, exist_ok=True)

# Mount static files
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# Dynamic UI Plugin Registry (Extensible Dashboard)
DYNAMIC_PLUGINS: List[Dict[str, Any]] = [
    {
        "id": "vram_monitor",
        "title": "GPU VRAM & Hardware",
        "icon": "cpu",
        "description": "Zero-spill 6GB VRAM budget guard & telemetry meter."
    },
    {
        "id": "diff_viewer",
        "title": "Code Diff Reviewer",
        "icon": "git-pull-request",
        "description": "Interactive side-by-side syntax diff before disk write."
    },
    {
        "id": "repo_explorer",
        "title": "Repo & AST Map",
        "icon": "folder-tree",
        "description": "Semantic codebase navigator and symbol browser."
    }
]

agent_instance = Agent()
inference_engine = InferenceEngine()

class ChatRequest(BaseModel):
    prompt: str
    workspace_root: str | None = None

class DynamicPluginRegister(BaseModel):
    id: str
    title: str
    icon: str
    description: str
    html_template: str

@app.get("/", response_class=HTMLResponse)
async def serve_index():
    index_file = STATIC_DIR / "index.html"
    if index_file.is_file():
        return index_file.read_text(encoding="utf-8")
    return "<h1>GhostHarness UI Initializing...</h1>"

@app.get("/api/telemetry")
async def get_telemetry():
    """Live hardware stats for gauges."""
    return memory_manager.get_hardware_telemetry()

@app.get("/api/health")
async def get_backend_health():
    """Check LM Studio / llama-server connectivity."""
    return await inference_engine.check_health()

@app.get("/api/plugins")
async def get_plugins():
    """Returns active UI modules."""
    return DYNAMIC_PLUGINS

@app.post("/api/plugins/register")
async def register_plugin(plugin: DynamicPluginRegister):
    """Allows the AI agent to inject new UI dashboard widgets live!"""
    for idx, p in enumerate(DYNAMIC_PLUGINS):
        if p["id"] == plugin.id:
            DYNAMIC_PLUGINS[idx] = plugin.dict()
            return {"success": True, "message": f"Plugin '{plugin.title}' updated"}
    DYNAMIC_PLUGINS.append(plugin.dict())
    return {"success": True, "message": f"Plugin '{plugin.title}' registered"}

@app.post("/api/chat")
async def chat_stream(req: ChatRequest):
    """Streams agent execution, thoughts, and tool actions via SSE."""
    async def event_generator():
        try:
            async for event in agent_instance.process_user_turn(req.prompt):
                yield f"data: {json.dumps(event)}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'content': str(e)})}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")

def start_server(host: str = "127.0.0.1", port: int = 8765):
    import uvicorn
    uvicorn.run(app, host=host, port=port, log_level="info")

if __name__ == "__main__":
    start_server()
