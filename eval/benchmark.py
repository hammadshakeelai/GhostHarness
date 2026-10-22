import os
import sys
import json
import time
import asyncio
from pathlib import Path
from typing import List, Dict, Any, Optional

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

EVAL_DIR = PROJECT_ROOT / "eval"
EVAL_DIR.mkdir(parents=True, exist_ok=True)

# Standard evaluation tasks evaluating core agentic coding competencies
BENCHMARK_TASKS = [
    {
        "id": "task_01_surgical_edit",
        "category": "Surgical Patching",
        "prompt": "In `core/config.py`, change the default temperature from 0.2 to 0.15 using edit_file.",
        "expected_tool": "edit_file",
        "expected_target_fragment": "temperature: float = Field(default=0.2"
    },
    {
        "id": "task_02_safe_terminal",
        "category": "Terminal Safety",
        "prompt": "Check the current git branch name using the terminal tool.",
        "expected_tool": "run_terminal",
        "expected_target_fragment": "git branch"
    },
    {
        "id": "task_03_code_search",
        "category": "Codebase Navigation",
        "prompt": "Search across the codebase for where `calculate_sum` or `SequenceMatcher` is defined.",
        "expected_tool": "grep_search",
        "expected_target_fragment": "SequenceMatcher"
    },
    {
        "id": "task_04_repo_inspection",
        "category": "AST Architecture",
        "prompt": "Inspect the project symbol tree to see what methods exist in Agent class.",
        "expected_tool": "analyze_repo_structure",
        "expected_target_fragment": "repo_path"
    },
    {
        "id": "task_05_file_bounds_read",
        "category": "Line Slicing",
        "prompt": "Read lines 1 to 15 of `core/dynamic_router.py`.",
        "expected_tool": "read_file",
        "expected_target_fragment": "core/dynamic_router.py"
    }
]

class AgentBenchmarkHarness:
    """
    Evaluates GhostHarness before and after fine-tuning.
    Identifies behavioral weaknesses, tool accuracy gaps, and gives actionable
    data-collection recommendations for the next fine-tuning cycle.
    """

    def __init__(self, model_name: Optional[str] = None):
        from core.agent import Agent
        from core.engine import InferenceEngine
        self.agent = Agent()
        self.engine = InferenceEngine()
        self.model_name = model_name or "qwen2.5-coder-7b-instruct"
        self.report_file = EVAL_DIR / f"benchmark_report_{int(time.time())}.json"

    async def evaluate_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        prompt = task["prompt"]
        expected_tool = task["expected_tool"]
        frag = task.get("expected_target_fragment", "")

        tool_called = None
        arguments_passed = {}
        tokens_streamed = 0
        start_time = time.time()

        try:
            async for evt in self.agent.process_user_turn(prompt):
                if evt.get("type") == "token":
                    tokens_streamed += 1
                elif evt.get("type") == "tool_start":
                    if not tool_called:
                        tool_called = evt.get("tool")
                        arguments_passed = evt.get("arguments", {})
        except Exception as e:
            return {
                "id": task["id"],
                "category": task["category"],
                "passed": False,
                "error": str(e),
                "tool_called": None
            }

        elapsed = time.time() - start_time
        args_str = json.dumps(arguments_passed)
        correct_tool = (tool_called == expected_tool)
        correct_target = (frag in args_str) if frag else True

        passed = correct_tool and correct_target
        gap_notes = []
        if not correct_tool:
            gap_notes.append(f"Used '{tool_called}' instead of expected '{expected_tool}'")
        if not correct_target:
            gap_notes.append(f"Missing expected target fragment '{frag}' in arguments")

        return {
            "id": task["id"],
            "category": task["category"],
            "passed": passed,
            "tool_called": tool_called,
            "expected_tool": expected_tool,
            "correct_tool": correct_tool,
            "correct_target": correct_target,
            "elapsed_sec": round(elapsed, 2),
            "tokens_generated": tokens_streamed,
            "gap_analysis": "; ".join(gap_notes) if gap_notes else "Optimal Execution"
        }

    async def run_benchmark(self) -> Dict[str, Any]:
        print("=" * 65)
        print(f" GhostHarness: Agent Competency & Gap Evaluation")
        print(f" Model Under Test : {self.model_name}")
        print(f" Total Benchmarks : {len(BENCHMARK_TASKS)} tasks")
        print("=" * 65)

        results = []
        for idx, t in enumerate(BENCHMARK_TASKS, 1):
            print(f"[{idx}/{len(BENCHMARK_TASKS)}] Testing {t['category']} ({t['id']})...")
            res = await self.evaluate_task(t)
            status = "✔ PASS" if res["passed"] else "✖ FAIL"
            print(f"    Status: {status} | Tool: {res['tool_called']} | {res['gap_analysis']}")
            results.append(res)
            await asyncio.sleep(1.0)

        passed_count = sum(1 for r in results if r["passed"])
        score_pct = round((passed_count / len(results)) * 100, 1)

        # Generate actionable recommendation for next fine-tuning cycle
        weak_categories = [r["category"] for r in results if not r["passed"]]
        recommendations = []
        if "Surgical Patching" in weak_categories:
            recommendations.append("Generate 150+ synthetic traces focusing on exact whitespace diff matching.")
        if "Terminal Safety" in weak_categories:
            recommendations.append("Train with multi-turn shell inspection traces and status checks.")
        if "Codebase Navigation" in weak_categories:
            recommendations.append("Synthesize AST symbol navigation and grep search patterns.")
        if not recommendations:
            recommendations.append("Agent scored 100% on core tasks! Ready for advanced multi-file refactoring traces.")

        summary = {
            "model": self.model_name,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "score_percent": score_pct,
            "passed": passed_count,
            "total": len(results),
            "results": results,
            "weaknesses_identified": weak_categories,
            "next_dataset_recommendations": recommendations
        }

        self.report_file.write_text(json.dumps(summary, indent=2), encoding="utf-8")
        print("\n" + "=" * 65)
        print(f"[BENCHMARK SUMMARY] Score: {score_pct}% ({passed_count}/{len(results)} Passed)")
        print(f"Identified Gaps: {', '.join(weak_categories) if weak_categories else 'None'}")
        print(f"Data Generation Guidance for Next LoRA Cycle:")
        for rec in recommendations:
            print(f"  ➔ {rec}")
        print(f"Detailed Report saved to: {self.report_file}")
        print("=" * 65)
        return summary

if __name__ == "__main__":
    harness = AgentBenchmarkHarness()
    asyncio.run(harness.run_benchmark())
