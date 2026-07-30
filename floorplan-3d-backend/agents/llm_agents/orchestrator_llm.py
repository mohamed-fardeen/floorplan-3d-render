"""LLM-backed Orchestrator.

Classifies user intent and generates clarifying questions dynamically
when ambiguous.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any, Dict, List, Optional, Tuple

from ..output_schemas import ORCHESTRATOR_OUTPUT_SCHEMA
from ..prompt_registry import GLOBAL_REGISTRY as PROMPTS
from ..llm.base import (
    CompletionRequest,
    LLMProvider,
    Message,
    ProviderUnavailable,
)


_log = logging.getLogger("agents.orchestrator_llm")

_DESIGN_HINTS = {"color", "colour", "pattern", "paint", "tint", "shade", "white", "navy", "sage"}
_GEOMETRY_HINTS = {"curve", "bevel", "extrude", "split", "merge", "offset", "round", "bend"}
_REJECT_HINTS = {"hello", "hi ", "thanks", "thank you", "who are you"}


class OrchestratorLLM:
    """LLM-backed orchestrator. Falls back to heuristics when no provider."""

    def __init__(self, provider: Optional[LLMProvider] = None) -> None:
        self._provider = provider
        self._system_prompt = PROMPTS.load("orchestrator").body

    def set_provider(self, provider: Optional[LLMProvider]) -> None:
        self._provider = provider

    async def classify(
        self,
        prompt: str,
        selection_present: bool,
        available_tools: List[str],
    ) -> Dict[str, Any]:
        text_low = (prompt or "").strip().lower()
        if not text_low:
            return {"intent": "reject", "invoked_agents": [], "reason": "empty prompt", "clarification": None}

        if any(h in text_low for h in _REJECT_HINTS) and len(text_low) < 30:
            return {"intent": "reject", "invoked_agents": [], "reason": "small talk", "clarification": None}

        if self._provider is None or not self._provider.is_available():
            return self._heuristic(prompt, selection_present)

        try:
            payload = "\n".join([
                f"USER PROMPT: {prompt}",
                f"SELECTION PRESENT: {selection_present}",
                f"AVAILABLE TOOLS: {', '.join(available_tools)}",
                "",
                "Return only JSON matching the schema. If intent=clarify,",
                "include a SHORT question that offers at most 2-3 options.",
            ])
            structured = self._provider.structured(
                CompletionRequest(
                    messages=[
                        Message(role="system", content=self._system_prompt),
                        Message(role="user", content=payload),
                    ],
                    temperature=0.1,
                    max_tokens=300,
                ),
                schema=ORCHESTRATOR_OUTPUT_SCHEMA,
                max_retries=1,
            )
            if not selection_present and structured.get("intent") in {"design", "geometry", "mixed"}:
                structured["intent"] = "clarify"
                structured["clarification"] = "Please select a region in the 3D viewport first."
            return structured
        except (ProviderUnavailable, ValueError, json.JSONDecodeError) as exc:
            _log.warning("orchestrator LLM failed, falling back: %s", exc)
            return self._heuristic(prompt, selection_present)

    def _heuristic(self, prompt: str, selection_present: bool) -> Dict[str, Any]:
        text_low = prompt.lower()
        design_score = sum(1 for h in _DESIGN_HINTS if h in text_low)
        geom_score = sum(1 for h in _GEOMETRY_HINTS if h in text_low)
        if design_score == 0 and geom_score == 0:
            return {
                "intent": "clarify",
                "invoked_agents": [],
                "reason": "ambiguous intent",
                "clarification": (
                    "I can help with design (colors, patterns, materials) or geometry "
                    "(curve, bevel, extrude, split, merge, offset). Which would you like?"
                ),
            }
        if not selection_present:
            return {
                "intent": "clarify",
                "invoked_agents": [],
                "reason": "no selection",
                "clarification": "Please select a region in the 3D viewport first.",
            }
        if design_score > 0 and geom_score > 0:
            intent = "mixed"
            invoked = ["design", "geometry", "execution"]
        elif design_score > 0:
            intent = "design"
            invoked = ["design", "execution"]
        else:
            intent = "geometry"
            invoked = ["geometry", "execution"]
        return {"intent": intent, "invoked_agents": invoked, "reason": "heuristic", "clarification": None}


__all__ = ["OrchestratorLLM"]