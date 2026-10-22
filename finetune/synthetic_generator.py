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

Requirements for each sample:
1. The user request must be an authentic coding task, bug fix, feature request, or optimization based directly on the provided code.
2. The assistant must first state its analytical thought process, followed by an exact surgical tool call:
   Tools available: `read_file`, `write_file`, `edit_file`, `run_terminal`, `grep_search`.
   For `edit_file`, the `target` must be an exact substring from the snippet, and `replacement` must be clean, production-ready code.
3. Provide realistic tool outputs and a final assistant verification concluding the turn.
4. Schema MUST be an array of JSON objects matching this exact ChatML schema:
[
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
        "content": "<Analytical reasoning>\\n\\n```json\\n{{\\"tool\\": \\"edit_file\\", \\"arguments\\": {{\\"path\\": \\"{filename}\\", \\"target\\": \\"<exact target block>\\", \\"replacement\\": \\"<improved replacement>\\"}}}}```"
      }},
      {{
        "role": "tool",
        "content": "{{\\"success\\": true, \\"message\\": \\"Applied patch.\\"}}"
      }},
      {{
        "role": "assistant",
        "content": "<Confirmation and verification analysis>"
      }}
    ]
  }}
]

Output ONLY a valid JSON array matching this structure.
"""

class SyntheticAgentDatasetGenerator:
    """
    Distills high-grade agentic coding traces using frontier models
    into high-quality training pairs formatted specifically for Qwen 7B 4-bit QLoRA.
    """

    def __init__(self, output_file: Optional[str] = None):
        self.gemini_key = os.environ.get("GEMINI_API_KEY", "").strip()
        self.openrouter_key = os.environ.get("OPENROUTER_API_KEY", "").strip()
        self.freemodel_key = os.environ.get("FREEMODEL_API_KEY", "").strip()
        self.output_file = Path(output_file or (DATASETS_DIR / "distilled_agent_dataset.jsonl"))

    async def generate_with_gemini(self, code_snippet: str, filename: str, suffix: str, num_samples: int = 2) -> List[Dict[str, Any]]:
        """Generates structured ChatML pairs using Gemini 2.5 Flash with strict JSON schema."""
        if not self.gemini_key:
            return []

        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={self.gemini_key}"
        prompt = PROMPT_TEMPLATE.format(
            num_samples=num_samples,
            language=suffix,
            code_snippet=code_snippet,
            filename=filename
        )

        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "responseMimeType": "application/json",
                "temperature": 0.2
            }
        }

        for attempt in range(1, 4):
            try:
                async with httpx.AsyncClient(timeout=90.0) as client:
                    resp = await client.post(url, json=payload)
                    if resp.status_code == 200:
                        raw = resp.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
                        data = json.loads(raw)
                        return data if isinstance(data, list) else [data]
                    elif resp.status_code in (429, 503):
                        print(f"    [Gemini {resp.status_code}] Rate boundary reached, backing off {attempt * 6}s...")
                        await asyncio.sleep(attempt * 6)
                    else:
                        print(f"    [!] Gemini Error {resp.status_code}: {resp.text[:120]}")
                        break
            except Exception as e:
                print(f"    [Gemini attempt {attempt}/3] {e}, retrying in {attempt * 4}s...")
                await asyncio.sleep(attempt * 4)

        return []

    async def generate_with_freemodel(self, code_snippet: str, filename: str, suffix: str, num_samples: int = 2) -> List[Dict[str, Any]]:
        """Queries FreeModel.dev API."""
        if not self.freemodel_key:
            return []

        prompt = PROMPT_TEMPLATE.format(
            num_samples=num_samples,
            language=suffix,
            code_snippet=code_snippet,
            filename=filename
        )

        headers = {
            "Authorization": f"Bearer {self.freemodel_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": "gpt-6-luna",
            "messages": [
                {"role": "system", "content": "You are a JSON dataset synthesizer. Output strictly a raw JSON array."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.2
        }

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                resp = await client.post("https://api.freemodel.dev/v1/chat/completions", json=payload, headers=headers)
                if resp.status_code == 200:
                    raw = resp.json()["choices"][0]["message"]["content"].strip()
                    if raw.startswith("```json"):
                        raw = raw[7:]
                    elif raw.startswith("```"):
                        raw = raw[3:]
                    if raw.endswith("```"):
                        raw = raw[:-3]
                    data = json.loads(raw.strip())
                    return data if isinstance(data, list) else [data]
                else:
                    print(f"    [FreeModel] Status {resp.status_code}: {resp.text[:100]}")
        except Exception as e:
            print(f"    [FreeModel Error] {e}")

        return []

    async def process_file(self, file_path: Path, num_samples: int = 2) -> int:
        code = file_path.read_text(encoding="utf-8", errors="ignore")
        if len(code.strip()) < 50:
            return 0

        snippet = code[:3500]
        suffix = file_path.suffix.lstrip(".") or "python"

        print(f"[*] Synthesizing agent traces for `{file_path.name}`...")

        # 1. Primary: Gemini 2.5 Flash
        samples = await self.generate_with_gemini(snippet, file_path.name, suffix, num_samples)

        # 2. Secondary: FreeModel
        if not samples and self.freemodel_key:
            print("    [Fallback] Trying FreeModel.dev...")
            samples = await self.generate_with_freemodel(snippet, file_path.name, suffix, num_samples)

        if not samples:
            print(f"    [!] Failed to generate traces for {file_path.name}")
            return 0

        valid_count = 0
        with open(self.output_file, "a", encoding="utf-8") as f:
            for s in samples:
                if isinstance(s, dict) and "messages" in s:
                    f.write(json.dumps(s) + "\n")
                    valid_count += 1

        print(f"    [✔] Saved {valid_count} validated agent traces to {self.output_file.name}")
        return valid_count

    async def run_full_harvest(self, target_dirs: Optional[List[str]] = None, samples_per_file: int = 2):
        if not target_dirs:
            target_dirs = ["core", "tools", "finetune", "web", "eval"]

        all_files: List[Path] = []
        for d in target_dirs:
            p = PROJECT_ROOT / d
            if p.is_dir():
                all_files.extend([f for f in p.rglob("*.py") if not any(ign in f.parts for ign in [".venv", "__pycache__"])])

        print("=" * 65)
        print(f" GhostHarness: Frontier Agent Trace Distillation")
        print(f" Teachers Configured: Gemini 2.5 Flash | FreeModel.dev | OpenRouter")
        print(f" Target Files       : {len(all_files)} codebase files")
        print(f" Output Dataset     : {self.output_file}")
        print("=" * 65)

        total = 0
        for idx, f in enumerate(all_files, 1):
            print(f"[{idx}/{len(all_files)}] Processing {f.relative_to(PROJECT_ROOT)}...")
            count = await self.process_file(f, num_samples=samples_per_file)
            total += count
            # Smooth 4.5s pacing ensures 100% compliance with Google AI Studio 15 RPM free limit
            await asyncio.sleep(4.5)

        print("\n" + "=" * 65)
        print(f"[COMPLETED] Batch finished! Total traces in dataset: {total}")
        print(f"Dataset location: {self.output_file}")
        print("=" * 65)

if __name__ == "__main__":
    generator = SyntheticAgentDatasetGenerator()
    asyncio.run(generator.run_full_harvest())
