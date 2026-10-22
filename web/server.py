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
from core.checkpoint import checkpoint_manager
from core.dynamic_router import model_router
from core.repo_map import RepoMap

app = FastAPI(title="GhostHarness Visual Workspace")

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
STATIC_DIR.mkdir(parents=True, exist_ok=True)

# Mount static files
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# Dynamic UI Plugin Registry (Extensible Dashboard)
DYNAMIC_PLUGINS: List[Dict[str, Any]] = [
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
    },
    {
        "id": "vram_monitor",
        "title": "Hardware Budget",
        "icon": "cpu",
        "description": "Zero-spill 6GB VRAM budget guard & telemetry meter."
    },
    {
        "id": "checkpoints",
        "title": "Checkpoints & Rollbacks",
        "icon": "history",
        "description": "Snapshot history with one-click undo capability."
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

class ModelOverrideRequest(BaseModel):
    model: str | None = None

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

@app.get("/api/repomap")
async def get_repo_map():
    """Returns AST symbol outline of the codebase."""
    rmap = RepoMap(root_dir=agent_instance.workspace_root)
    return {"map": rmap.generate_map()}

@app.get("/api/checkpoints")
async def get_checkpoints():
    """Returns list of snapshot checkpoints."""
    return {"checkpoints": checkpoint_manager.list_checkpoints()}

@app.post("/api/undo")
async def trigger_undo():
    """Rolls back the latest code modification checkpoint."""
    res = checkpoint_manager.rollback_latest()
    return res

@app.post("/api/model/override")
async def set_model_override(req: ModelOverrideRequest):
    """Set manual model override (7B, 14B, or None for auto)."""
    model_router.set_override(req.model)
    return {"success": True, "active_override": req.model}

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

@app.get("/api/mission")
async def get_mission_status():
    """Returns autonomous fine-tuning, acceptance audit, and evaluation reports."""
    rep_dir = BASE_DIR.parent / "eval" / "reports"
    adapter_dir = BASE_DIR.parent / "finetune" / "adapters" / "lab_tuned_adapter"
    summary_file = rep_dir / "mission_summary.json"
    report_file = rep_dir / "lab_mission_report.md"
    adapter_file = adapter_dir / "adapter_model.safetensors"

    summary_data = {}
    if summary_file.is_file():
        try:
            summary_data = json.loads(summary_file.read_text(encoding="utf-8"))
        except Exception:
            pass

    report_markdown = ""
    if report_file.is_file():
        report_markdown = report_file.read_text(encoding="utf-8")

    return {
        "adapter_present": adapter_file.is_file(),
        "adapter_name": "lab_tuned_adapter" if adapter_file.is_file() else None,
        "adapter_size_mb": round(adapter_file.stat().st_size / (1024 * 1024), 2) if adapter_file.is_file() else 0,
        "summary": summary_data,
        "report_markdown": report_markdown
    }

def start_server(host: str = "127.0.0.1", port: int = 8765):
    import uvicorn
    uvicorn.run(app, host=host, port=port, log_level="info")

if __name__ == "__main__":
    start_server()
