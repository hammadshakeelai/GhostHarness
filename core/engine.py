import json
import httpx
from typing import AsyncGenerator, Dict, Any, List, Optional
from core.config import settings

class InferenceEngine:
    """Universal client for local LLM engines (LM Studio, llama.cpp, Ollama)."""

    def __init__(self, api_base: Optional[str] = None, api_key: Optional[str] = None):
        self.api_base = (api_base or settings.models.api_base).rstrip("/")
        self.api_key = api_key or settings.models.api_key

    async def check_health(self) -> Dict[str, Any]:
        """Verify local model server connectivity and list active models."""
        async with httpx.AsyncClient(timeout=3.0) as client:
            try:
                resp = await client.get(f"{self.api_base}/models")
                if resp.status_code == 200:
                    data = resp.json()
                    models = [m.get("id") for m in data.get("data", [])]
                    return {
                        "online": True,
                        "endpoint": self.api_base,
                        "available_models": models,
                        "status": "Connected to local server"
                    }
                return {
                    "online": False,
                    "endpoint": self.api_base,
                    "available_models": [],
                    "status": f"Server error HTTP {resp.status_code}"
                }
            except Exception as e:
                return {
                    "online": False,
                    "endpoint": self.api_base,
                    "available_models": [],
                    "status": f"Offline: {str(e)}"
                }

    async def stream_chat(
        self,
        messages: List[Dict[str, Any]],
        model: str,
        tools: Optional[List[Dict[str, Any]]] = None,
        temperature: float = 0.2,
        max_tokens: int = 4096,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Stream chat completions token by token with OpenAI-compatible tool call support."""
        payload: Dict[str, Any] = {
            "model": model,
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
