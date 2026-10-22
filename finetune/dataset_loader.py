import json
from pathlib import Path
from typing import List, Dict, Any

class USBDatasetLoader:
    """Ingests source code, diffs, and docs from the USB to generate fine-tuning datasets."""

    @staticmethod
    def create_instruction_sample(instruction: str, input_code: str, output_code: str) -> Dict[str, Any]:
        """Converts an example into Qwen ChatML conversational format."""
        return {
            "messages": [
                {"role": "system", "content": "You are an expert autonomous software engineer."},
                {"role": "user", "content": f"{instruction}\n\n```python\n{input_code}\n```" if input_code else instruction},
                {"role": "assistant", "content": output_code}
            ]
        }

    @classmethod
    def harvest_directory_to_dataset(cls, directory_path: str, output_jsonl: str = "dataset.jsonl") -> int:
        """Parses Python files in a directory and generates self-contained completion pairs."""
        p = Path(directory_path)
        samples = []

        for f in p.rglob("*.py"):
            if any(ign in f.parts for ign in [".git", ".venv", "__pycache__"]):
                continue
            try:
                code = f.read_text(encoding="utf-8", errors="ignore")
                if len(code.strip()) > 50:
                    sample = cls.create_instruction_sample(
                        instruction=f"Write the implementation for `{f.name}` providing production-quality code:",
                        input_code="",
                        output_code=f"```python\n{code}\n```"
                    )
                    samples.append(sample)
            except Exception:
                continue

        with open(output_jsonl, "w", encoding="utf-8") as out:
            for s in samples:
                out.write(json.dumps(s) + "\n")

        return len(samples)
