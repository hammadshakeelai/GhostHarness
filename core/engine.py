import json
import httpx
import shutil
import subprocess
import asyncio
from pathlib import Path
from typing import AsyncGenerator, Dict, Any, List, Optional
from core.config import settings

class InferenceEngine:
    """
    Universal multi-backend client for local LLM engines:
    - Auto-detects LM Studio (1234), llama-server (8080), Ollama (11434)
    - Can spawn an embedded headless llama-server binary from the USB without admin rights
    """

    CANDIDATE_ENDPOINTS = [
        ("LM Studio", "http://127.0.0.1:1234/v1"),
        ("llama-server", "http://127.0.0.1:8080/v1"),
        ("Ollama", "http://127.0.0.1:11434/v1"),
    ]

    def __init__(self, api_base: Optional[str] = None, api_key: Optional[str] = None):
        self.api_base = (api_base or settings.models.api_base).rstrip("/")
        self.api_key = api_key or settings.models.api_key
        self.detected_backend: Optional[str] = None
        self._embedded_proc: Optional[subprocess.Popen] = None

    async def check_health(self) -> Dict[str, Any]:
        """Auto-probes endpoints to discover active local backend."""
        # Check current configured endpoint first
        async with httpx.AsyncClient(timeout=2.0) as client:
            try:
                resp = await client.get(f"{self.api_base}/models")
                if resp.status_code == 200:
                    data = resp.json()
                    models = [m.get("id") for m in data.get("data", [])]
                    return {
                        "online": True,
                        "backend": "Configured Server",
                        "endpoint": self.api_base,
                        "available_models": models,
                        "status": f"Connected to {self.api_base}"
                    }
            except Exception:
                pass

            # Auto-probe candidates
            for name, ep in self.CANDIDATE_ENDPOINTS:
                try:
                    resp = await client.get(f"{ep}/models")
                    if resp.status_code == 200:
                        self.api_base = ep
                        self.detected_backend = name
                        data = resp.json()
                        models = [m.get("id") for m in data.get("data", [])]
                        return {
                            "online": True,
                            "backend": name,
                            "endpoint": ep,
                            "available_models": models,
                            "status": f"Auto-detected active backend: {name}"
                        }
                except Exception:
                    continue

        return {
            "online": False,
            "backend": None,
            "endpoint": self.api_base,
            "available_models": [],
            "status": "No local LLM backend detected on ports 1234, 8080, or 11434"
        }

    def launch_embedded_llama_server(self, model_gguf_path: str, port: int = 8080) -> bool:
        """Launches a standalone llama-server binary in user-space with 6GB optimal parameters."""
        bin_paths = [
            Path("bin/llama-server"),
            Path("bin/llama-server.exe"),
            Path(shutil.which("llama-server") or "")
        ]
        chosen_bin = None
        for bp in bin_paths:
            if bp.is_file():
                chosen_bin = str(bp)
                break

        if not chosen_bin:
            return False

        # Optimized flags for 6GB VRAM (Flash Attention, 8k context, all layers offloaded for 7B)
        cmd = [
            chosen_bin,
            "-m", model_gguf_path,
            "-ngl", "33",
            "--ctx-size", "8192",
            "--flash-attn",
            "--port", str(port),
            "--host", "127.0.0.1"
        ]

        self._embedded_proc = subprocess.Popen(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        self.api_base = f"http://127.0.0.1:{port}/v1"
        return True

    async def get_effective_model(self, requested_model: str) -> str:
        """Intelligently maps requested model to the active backend model if needed."""
        health = await self.check_health()
        available = health.get("available_models", [])
        if not available:
            return requested_model
        if requested_model in available:
            return requested_model
        for m in available:
            if requested_model.lower() in m.lower() or m.lower() in requested_model.lower():
                return m
        # If single model loaded locally, use it
        if len(available) == 1:
            return available[0]
        return requested_model

    async def stream_chat(
        self,
        messages: List[Dict[str, Any]],
        model: str,
        tools: Optional[List[Dict[str, Any]]] = None,
        temperature: float = 0.2,
        max_tokens: int = 4096,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Stream chat completions token by token with OpenAI-compatible tool call support."""
        effective_model = await self.get_effective_model(model)
        payload: Dict[str, Any] = {
            "model": effective_model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": True,
        }
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = "auto"

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        async with httpx.AsyncClient(timeout=180.0) as client:
            try:
                async with client.stream(
                    "POST",
                    f"{self.api_base}/chat/completions",
                    json=payload,
                    headers=headers
                ) as response:
                    if response.status_code != 200:
                        err_text = await response.aread()
                        yield {"type": "error", "content": f"API Error {response.status_code}: {err_text.decode('utf-8', errors='ignore')}"}
                        return

                    async for line in response.aiter_lines():
                        if not line:
                            continue
                        if line.startswith("data: "):
                            data_str = line[6:].strip()
                            if data_str == "[DONE]":
                                break
                            try:
                                chunk = json.loads(data_str)
                                delta = chunk.get("choices", [{}])[0].get("delta", {})
                                if "content" in delta and delta["content"]:
                                    yield {"type": "content", "content": delta["content"]}
                                if "tool_calls" in delta and delta["tool_calls"]:
                                    yield {"type": "tool_calls", "tool_calls": delta["tool_calls"]}
                            except Exception:
                                continue
            except Exception as e:
                yield {"type": "error", "content": f"Connection failed to {self.api_base}: {str(e)}"}
