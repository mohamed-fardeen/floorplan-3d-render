"""LLM-backed summariser agent for long conversations."""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from ..output_schemas import SUMMARISER_OUTPUT_SCHEMA
from ..prompt_registry import GLOBAL_REGISTRY as PROMPTS
from ..llm.base import (
    CompletionRequest,
    LLMProvider,
    Message,
    ProviderUnavailable,
)


_log = logging.getLogger("agents.summariser")


class SummariserAgent:
    name = "summariser"

    def __init__(self, provider: Optional[LLMProvider] = None) -> None:
        self._provider = provider
        self._prompt = PROMPTS.load("summariser").body

    def set_provider(self, provider: Optional[LLMProvider]) -> None:
        self._provider = provider

    async def summarise(
        self,
        turns: List[Dict[str, Any]],
        previous_summary: str = "",
    ) -> Dict[str, Any]:
        if not turns:
            return {"summary": previous_summary, "active_selections": [], "recent_tools": [], "recent_materials": [], "open_questions": []}
        if self._provider is None or not self._provider.is_available():
            return self._fallback(turns, previous_summary)

        try:
            payload_lines = [f"PREVIOUS SUMMARY: {previous_summary}", "", "RECENT TURNS:"]
            for turn in turns[-12:]:
                role = turn.get("role", "user")
                content = turn.get("content", "")
                payload_lines.append(f"- {role}: {content}")
            payload_lines.append("\nReturn only JSON matching the schema.")
            structured = self._provider.structured(
                CompletionRequest(
                    messages=[
                        Message(role="system", content=self._prompt),
                        Message(role="user", content="\n".join(payload_lines)),
                    ],
                    temperature=0.1,
                    max_tokens=400,
                ),
                schema=SUMMARISER_OUTPUT_SCHEMA,
                max_retries=1,
            )
            return structured
        except (ProviderUnavailable, ValueError) as exc:
            _log.warning("summariser LLM failed, falling back: %s", exc)
            return self._fallback(turns, previous_summary)

    def _fallback(self, turns: List[Dict[str, Any]], previous_summary: str) -> Dict[str, Any]:
        last_user = next((t for t in reversed(turns) if t.get("role") == "user"), None)
        text = (last_user or {}).get("content", "").strip()
        return {
            "summary": (previous_summary + " " + text).strip()[:400],
            "active_selections": [],
            "recent_tools": [],
            "recent_materials": [],
            "open_questions": [],
        }


__all__ = ["SummariserAgent"]