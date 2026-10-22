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
    Distills agentic coding traces from frontier teacher models (Claude, GPT-4o, DeepSeek, Qwen 72B)
    into high-quality training pairs formatted specifically for Qwen 7B 4-bit QLoRA.
    """

    def __init__(
        self,
        api_key: str,
        api_base: str = "https://api.openai.com/v1",
        model: str = "gpt-4o",
        output_file: Optional[str] = None
    ):
        self.api_key = api_key
        self.api_base = api_base.rstrip("/")
        self.model = model
        self.output_file = Path(output_file or (DATASETS_DIR / "distilled_agent_dataset.jsonl"))

    async def generate_from_file(self, file_path: str, num_samples: int = 3) -> int:
        p = Path(file_path)
        if not p.is_file():
            print(f"[!] File not found: {file_path}")
            return 0

        code = p.read_text(encoding="utf-8", errors="ignore")
        if len(code.strip()) < 50:
            return 0

        # Truncate snippet to 3500 chars to fit prompt budget
        snippet = code[:3500]
        suffix = p.suffix.lstrip(".") or "python"

        prompt = PROMPT_TEMPLATE.format(
            num_samples=num_samples,
            language=suffix,
            code_snippet=snippet,
            filename=p.name
        )

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": "You are a specialized JSON data synthesizer. Output strictly raw JSON."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.3
        }

        print(f"[*] Querying teacher model ({self.model}) for `{p.name}`...")

        async with httpx.AsyncClient(timeout=120.0) as client:
            try:
                resp = await client.post(
                    f"{self.api_base}/chat/completions",
                    json=payload,
                    headers=headers
                )
                if resp.status_code != 200:
                    print(f"[!] API Error {resp.status_code}: {resp.text}")
                    return 0

                data = resp.json()
                raw_text = data["choices"][0]["message"]["content"].strip()

                # Clean markdown backticks if present
                if raw_text.startswith("```json"):
                    raw_text = raw_text[7:]
                elif raw_text.startswith("```"):
                    raw_text = raw_text[3:]
                if raw_text.endswith("```"):
                    raw_text = raw_text[:-3]

                parsed_samples = json.loads(raw_text.strip())
                if isinstance(parsed_samples, dict):
                    parsed_samples = [parsed_samples]

                # Append to JSONL
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
        print(f"[*] Starting batch harvest across {len(selected_files)} code files...")

        for file_path in selected_files:
            count = await self.generate_from_file(str(file_path), num_samples=samples_per_file)
            total_generated += count
            await asyncio.sleep(1.0)  # Gentle rate limiting

        print("=" * 60)
        print(f"[DONE] Total high-grade synthetic agent traces generated: {total_generated}")
        print(f"Dataset location: {self.output_file}")
        print("=" * 60)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python finetune/synthetic_generator.py <API_KEY> [API_BASE] [MODEL]")
        sys.exit(1)

    key = sys.argv[1]
    base = sys.argv[2] if len(sys.argv) > 2 else "https://api.openai.com/v1"
    mdl = sys.argv[3] if len(sys.argv) > 3 else "gpt-4o"

    gen = SyntheticAgentDatasetGenerator(api_key=key, api_base=base, model=mdl)
    asyncio.run(gen.batch_harvest(str(PROJECT_ROOT / "core"), samples_per_file=2))
