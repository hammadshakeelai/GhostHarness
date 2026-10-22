import base64
import httpx
from pathlib import Path
from typing import Dict, Any, Optional

class MultiModalSidecar:
    """
    Handles local Voice Dictation and Vision inspection within the 6GB VRAM budget.
    """

    def __init__(self, api_base: str = "http://127.0.0.1:1234/v1"):
        self.api_base = api_base

    async def inspect_image(self, image_path: str, question: str = "Analyze this image and identify code bugs or UI flaws:") -> Dict[str, Any]:
        """Sends an image to the local vision model via OpenAI-compatible vision format."""
        p = Path(image_path)
        if not p.is_file():
            return {"success": False, "error": f"Image file not found: {image_path}"}

        # Encode image to base64
        with open(p, "rb") as img_file:
            b64_data = base64.b64encode(img_file.read()).decode("utf-8")

        suffix = p.suffix.lower().replace(".", "")
        mime = f"image/{suffix}" if suffix in ["png", "jpeg", "jpg", "webp"] else "image/png"

        payload = {
            "model": "qwen2-vl-7b-instruct",  # or moondream2
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": question},
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:{mime};base64,{b64_data}"}
                        }
                    ]
                }
            ],
            "max_tokens": 1024
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            try:
                resp = await client.post(f"{self.api_base}/chat/completions", json=payload)
                if resp.status_code == 200:
                    data = resp.json()
                    analysis = data["choices"][0]["message"]["content"]
                    return {"success": True, "analysis": analysis}
                return {"success": False, "error": f"Vision API returned HTTP {resp.status_code}"}
            except Exception as e:
                return {"success": False, "error": f"Vision call failed: {str(e)}"}

    async def transcribe_audio_whisper(self, audio_bytes: bytes) -> Dict[str, Any]:
        """Transcribes dictation using local lightweight Whisper."""
        try:
            from faster_whisper import WhisperModel
            # Tiny/Base runs in ~150MB VRAM or pure CPU
            model = WhisperModel("base", device="cpu", compute_type="int8")
            segments, info = model.transcribe(audio_bytes, beam_size=5)
            transcript = " ".join([seg.text for seg in segments]).strip()
            return {"success": True, "transcript": transcript, "language": info.language}
        except ImportError:
            return {
                "success": False,
                "error": "faster-whisper not installed. Install with: pip install --user faster-whisper"
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

multimodal_sidecar = MultiModalSidecar()
