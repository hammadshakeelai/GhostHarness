import json
import subprocess
from pathlib import Path
from typing import List, Dict, Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATASETS_DIR = PROJECT_ROOT / "datasets"
DATASETS_DIR.mkdir(parents=True, exist_ok=True)

class USBDatasetLoader:
    """Ingests source code, diffs, git commits, and docs to build high-grade training datasets."""

    @staticmethod
    def create_instruction_sample(instruction: str, input_code: str, output_code: str) -> Dict[str, Any]:
        """Converts an example into Qwen ChatML conversational format."""
        user_text = f"{instruction}\n\n```python\n{input_code}\n```" if input_code else instruction
        return {
            "messages": [
                {"role": "system", "content": "You are GhostHarness, an elite autonomous software engineering model."},
                {"role": "user", "content": user_text},
                {"role": "assistant", "content": output_code}
            ]
        }

    @classmethod
    def harvest_directory_to_dataset(cls, directory_path: str, output_jsonl: str = str(DATASETS_DIR / "codebase_dataset.jsonl")) -> int:
        """Parses Python files in a directory and generates self-contained completion pairs."""
        p = Path(directory_path)
        samples = []

        for f in p.rglob("*.py"):
            if any(ign in f.parts for ign in [".git", ".venv", "__pycache__", "wheels"]):
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

    @classmethod
    def harvest_git_commits(cls, repo_dir: str, output_jsonl: str = "commit_dataset.jsonl", max_commits: int = 100) -> int:
        """
        Parses git commit history (`git log -p`) into commit-message -> code patch training pairs.
        Teaches local Qwen models how real developers structure incremental edits and bug fixes.
        """
        try:
            cmd = ["git", "log", "-n", str(max_commits), "-p", "--no-merges", "--stat"]
            log_output = subprocess.check_output(cmd, cwd=repo_dir, text=True, errors="ignore")
        except Exception as e:
            print(f"[ERROR] Failed to read git history: {e}")
            return 0

        commits_raw = log_output.split("\ncommit ")
        samples = []

        for c in commits_raw:
            if not c.strip():
                continue
            lines = c.splitlines()
            msg_lines = []
            diff_lines = []
            in_diff = False

            for l in lines:
                if l.startswith("diff --git"):
                    in_diff = True
                if in_diff:
                    diff_lines.append(l)
                elif l.startswith("    "):
                    msg_lines.append(l.strip())

            msg = " ".join(msg_lines).strip()
            diff_text = "\n".join(diff_lines).strip()

            if msg and diff_text and len(diff_text) < 4000:
                sample = cls.create_instruction_sample(
                    instruction=f"Apply code modifications to satisfy the following commit requirement:\n{msg}",
                    input_code="",
                    output_code=f"```diff\n{diff_text}\n```"
                )
                samples.append(sample)

        with open(output_jsonl, "w", encoding="utf-8") as out:
            for s in samples:
                out.write(json.dumps(s) + "\n")

        return len(samples)
