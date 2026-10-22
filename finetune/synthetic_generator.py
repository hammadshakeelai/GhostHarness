import os
import sys
import json
import asyncio
import httpx
from pathlib import Path
from typing import List, Dict, Any, Optional

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATASETS_DIR = PROJECT_ROOT / "datasets"
DATASETS_DIR.mkdir(parents=True, exist_ok=True)

def load_env_file():
    env_file = PROJECT_ROOT / ".env"
    if env_file.is_file():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())

load_env_file()

PROMPT_TEMPLATE = """You are an expert AI dataset synthesizer for training autonomous coding agents.
Analyze the following source code snippet and generate {num_samples} realistic, high-quality, multi-turn agent interaction samples.

Source Code Context:
```{language}
{code_snippet}
```

Each sample must represent a real-world coding agent interaction matching this exact ChatML schema:
{{
  "messages": [
    {{
      "role": "system",
      "content": "You are GhostHarness, an elite autonomous software engineering agent running locally with direct tool access."
    }},
    {{
      "role": "user",
      "content": "<Detailed user request or bug report based on the code>"
    }},
    {{
      "role": "assistant",
      "content": "<Thought process and explanation of intended action>\\n\\n```json\\n{{\\"tool\\": \\"edit_file\\", \\"arguments\\": {{\\"path\\": \\"{filename}\\", \\"target\\": \\"<exact target block>\\", \\"replacement\\": \\"<improved replacement>\\"}}}}```"
    }},
    {{
      "role": "tool",
      "content": "{{\\"success\\": true, \\"message\\": \\"Successfully applied surgical edit.\\"}}"
    }},
    {{
      "role": "assistant",
      "content": "<Confirmation of fix and verification conclusion>"
    }}
  ]
}}

Generate an array of JSON objects matching this format. Output ONLY valid JSON:
[
  ...
]
"""

class SyntheticAgentDatasetGenerator:
    """
    Distills agentic coding traces from teacher models via OpenRouter or Google Gemini
    into high-quality training pairs formatted specifically for Qwen 7B 4-bit QLoRA.
    """

    def __init__(
        self,
        provider: Optional[str] = None,
        api_key: Optional[str] = None,
        api_base: Optional[str] = None,
        model: Optional[str] = None,
        output_file: Optional[str] = None
    ):
        openrouter_key = os.environ.get("OPENROUTER_API_KEY", "").strip()
        gemini_key = os.environ.get("GEMINI_API_KEY", "").strip()

        # Auto-detect or honor requested provider
        if provider == "openrouter" or (not provider and openrouter_key):
            self.provider = "openrouter"
            self.api_key = api_key or openrouter_key
            self.api_base = "https://openrouter.ai/api/v1"
            self.model = model or os.environ.get("OPENROUTER_MODEL", "anthropic/claude-3.5-sonnet")
        elif provider == "gemini" or (not provider and gemini_key):
            self.provider = "gemini"
            self.api_key = api_key or gemini_key
            self.api_base = "https://generativelanguage.googleapis.com/v1beta/openai"
            self.model = model or os.environ.get("GEMINI_MODEL", "gemini-2.0-flash")
        else:
            self.provider = "custom"
            self.api_key = api_key or os.environ.get("OPENAI_API_KEY", "").strip()
            self.api_base = (api_base or "https://api.openai.com/v1").rstrip("/")
            self.model = model or "gpt-4o"

        self.output_file = Path(output_file or (DATASETS_DIR / "distilled_agent_dataset.jsonl"))

    def get_headers(self) -> Dict[str, str]:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        if self.provider == "openrouter":
            headers["HTTP-Referer"] = "https://github.com/hammadshakeel/GhostHarness"
            headers["X-Title"] = "GhostHarness Sovereign Agent"
        return headers

    async def generate_from_file(self, file_path: str, num_samples: int = 3) -> int:
        if not self.api_key:
            print("[!] Error: No API key found. Please add OPENROUTER_API_KEY or GEMINI_API_KEY to your .env file.")
            return 0

        p = Path(file_path)
        if not p.is_file():
            print(f"[!] File not found: {file_path}")
            return 0

        code = p.read_text(encoding="utf-8", errors="ignore")
        if len(code.strip()) < 50:
            return 0

        snippet = code[:3500]
        suffix = p.suffix.lstrip(".") or "python"

        prompt = PROMPT_TEMPLATE.format(
            num_samples=num_samples,
            language=suffix,
            code_snippet=snippet,
            filename=p.name
        )

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": "You are a specialized JSON data synthesizer. Output strictly raw JSON."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.3
        }

        print(f"[*] Querying {self.provider.upper()} teacher ({self.model}) for `{p.name}`...")

        async with httpx.AsyncClient(timeout=120.0) as client:
            try:
                resp = await client.post(
                    f"{self.api_base}/chat/completions",
                    json=payload,
                    headers=self.get_headers()
                )
                if resp.status_code != 200:
                    print(f"[!] API Error {resp.status_code}: {resp.text}")
                    return 0

                data = resp.json()
                raw_text = data["choices"][0]["message"]["content"].strip()

                if raw_text.startswith("```json"):
                    raw_text = raw_text[7:]
                elif raw_text.startswith("```"):
                    raw_text = raw_text[3:]
                if raw_text.endswith("```"):
                    raw_text = raw_text[:-3]

                parsed_samples = json.loads(raw_text.strip())
                if isinstance(parsed_samples, dict):
                    parsed_samples = [parsed_samples]

                with open(self.output_file, "a", encoding="utf-8") as f:
                    for s in parsed_samples:
                        f.write(json.dumps(s) + "\n")

                print(f"[✔] Successfully generated and saved {len(parsed_samples)} agent traces from {p.name}")
                return len(parsed_samples)

            except Exception as e:
                print(f"[!] Generation failed: {e}")
                return 0

    async def batch_harvest(self, directory: str, samples_per_file: int = 2, max_files: int = 15):
        base = Path(directory)
        files = [f for f in base.rglob("*.py") if not any(ign in f.parts for ign in [".git", ".venv", "__pycache__", "wheels"])]
        selected_files = files[:max_files]

        total_generated = 0
        print(f"[*] Starting batch harvest with {self.provider.upper()} ({self.model}) across {len(selected_files)} code files...")

        for file_path in selected_files:
            count = await self.generate_from_file(str(file_path), num_samples=samples_per_file)
            total_generated += count
            await asyncio.sleep(1.0)

        print("=" * 60)
        print(f"[DONE] Total synthetic agent traces generated: {total_generated}")
        print(f"Dataset location: {self.output_file}")
        print("=" * 60)

if __name__ == "__main__":
    prov = sys.argv[1] if len(sys.argv) > 1 else None
    gen = SyntheticAgentDatasetGenerator(provider=prov)
    asyncio.run(gen.batch_harvest(str(PROJECT_ROOT / "core"), samples_per_file=2))
