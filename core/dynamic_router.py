import re
from typing import Dict, Any, List
from core.config import settings

class DynamicModelRouter:
    """Intelligently routes prompts to 7B (pure 6GB VRAM) or 14B/32B (hybrid VRAM+RAM)."""

    HEAVY_REASONING_TRIGGERS = [
        r"\barchitect(ure)?\b",
        r"\brefactor(ing)?\b",
        r"\bdeep\s+debug\b",
        r"\balgorithm\b",
        r"\bmulti-file\b",
        r"\bsecurity\s+audit\b",
        r"\bdesign\s+pattern\b",
        r"\bconcurrency\b",
        r"\brace\s+condition\b",
        r"\bmemory\s+leak\b",
        r"\bdistributed\b",
        r"\bmath(ematical)?\b"
    ]

    FAST_ACTIONS_TRIGGERS = [
        r"\bread\b",
        r"\blist\b",
        r"\bgrep\b",
        r"\bsearch\b",
        r"\bformat\b",
        r"\blint\b",
        r"\bgit\b",
        r"\bcommit\b",
        r"\bstatus\b",
        r"\brun\b",
        r"\btest\b",
        r"\bquick\s+fix\b",
    ]

    def __init__(self):
        self.fast_model = settings.models.fast_model
        self.heavy_model = settings.models.heavy_model
        self.manual_override: str | None = None

    def set_override(self, model_name: str | None):
        self.manual_override = model_name

    def select_model(self, prompt: str, conversation_history: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Chooses the optimal model based on complexity and hardware safety."""
        if self.manual_override:
            return {
                "model": self.manual_override,
                "reason": "Manual user override active",
                "tier": "override"
            }

        # Check conversation history depth and code block count
        total_code_lines = sum(
            m.get("content", "").count("\n") for m in conversation_history[-3:] if isinstance(m.get("content"), str)
        )

        p_lower = prompt.lower()

        # Check for heavy reasoning signals
        is_heavy = any(re.search(pat, p_lower) for pat in self.HEAVY_REASONING_TRIGGERS)
        is_fast = any(re.search(pat, p_lower) for pat in self.FAST_ACTIONS_TRIGGERS)

        if is_heavy or total_code_lines > 250:
            return {
                "model": self.heavy_model,
                "reason": "High complexity / architectural planning detected. Escalating to 14B/32B hybrid offload.",
                "tier": "heavy"
            }

        # Default to blazing fast 7B (100% VRAM resident)
        return {
            "model": self.fast_model,
            "reason": "Operational/tactical coding task. Executing on 7B 100% VRAM (zero spill, maximum t/s).",
            "tier": "fast"
        }

model_router = DynamicModelRouter()
