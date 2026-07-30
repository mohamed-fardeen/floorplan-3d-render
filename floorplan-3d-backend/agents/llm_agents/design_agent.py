"""LLM-backed Design Agent.

Falls back to the rule-based planner when no LLM provider is configured.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional

from ..base import Agent, AgentRequest, AgentResponse
from ..output_schemas import DESIGN_OUTPUT_SCHEMA
from ..prompt_registry import GLOBAL_REGISTRY as PROMPTS
from ..llm.base import (
    CompletionRequest,
    LLMProvider,
    Message,
    ProviderUnavailable,
    validate_json,
)
from .fallback import rule_based_plan

_log = logging.getLogger("agents.design")


class DesignAgent(Agent):
    name = "design"

    def __init__(self, provider: Optional[LLMProvider] = None) -> None:
        super().__init__(PROMPTS.load("design").body)
        self._provider = provider

    def set_provider(self, provider: Optional[LLMProvider]) -> None:
        self._provider = provider

    async def run(self, request: AgentRequest) -> AgentResponse:
        if self._provider is None or not self._provider.is_available():
            return self._rule_based(request, reason="no LLM provider configured")

        user_payload = self._build_user_payload(request)
        try:
            structured = self._provider.structured(
                CompletionRequest(
                    messages=[
                        Message(role="system", content=self.system_message()),
                        Message(role="user", content=user_payload, images=request.context.get("images", []) or []),
                    ],
                    temperature=0.2,
                    max_tokens=600,
                ),
                schema=DESIGN_OUTPUT_SCHEMA,
                max_retries=1,
            )
            ops = structured.get("operations", []) or []
            recs = structured.get("recommendations", []) or []
            reasoning = structured.get("reasoning", "")
            validate_ops(ops, request)
            return AgentResponse(
                agent=self.name,
                operations=ops,
                notes=[reasoning, *recs],
                context_extra={"recommendations": recs, "reasoning": reasoning, "source": "llm"},
            )
        except (ProviderUnavailable, ValueError, json.JSONDecodeError) as exc:
            _log.warning("design agent LLM failed, falling back: %s", exc)
            return self._rule_based(request, reason=f"LLM failed: {exc}")

    def _build_user_payload(self, request: AgentRequest) -> str:
        parts = [
            f"USER PROMPT: {request.prompt}",
            "",
            "SELECTION:",
            json.dumps(request.selection_summary, indent=2),
            "",
            f"AVAILABLE PATTERNS: {', '.join(request.available_patterns) or '(none)'}",
            f"AVAILABLE MATERIALS: {', '.join(request.available_materials) or '(none)'}",
            f"DESIGN INTENT: {request.context.get('design_intent', '')}",
            "",
            "Return only JSON matching the schema.",
        ]
        if request.conversation:
            parts.append("\nRECENT CONVERSATION:")
            for turn in request.conversation[-6:]:
                role = turn.get("role", "user")
                content = turn.get("content", "")
                parts.append(f"- {role}: {content}")
        return "\n".join(parts)

    def _rule_based(self, request: AgentRequest, reason: str = "") -> AgentResponse:
        ops, notes = rule_based_plan(request.prompt)
        return AgentResponse(
            agent=self.name,
            operations=ops,
            notes=[reason, *notes],
            context_extra={"recommendations": [], "reasoning": "; ".join(notes) or "rule-based", "source": "rules"},
        )


def validate_ops(ops: List[Dict[str, Any]], request: AgentRequest) -> None:
    valid_patterns = set(request.available_patterns or [])
    valid_materials = set(request.available_materials or [])
    for op in ops:
        op_type = op.get("type")
        if op_type == "apply_pattern" and valid_patterns and op.get("pattern") not in valid_patterns:
            raise ValueError(f"unknown pattern {op.get('pattern')!r}")
        if op_type == "set_material_preset" and valid_materials and op.get("preset") not in valid_materials:
            raise ValueError(f"unknown preset {op.get('preset')!r}")
        if op_type == "set_color":
            val = op.get("value") or ""
            if not (isinstance(val, str) and len(val) == 7 and val.startswith("#")):
                raise ValueError(f"invalid color {val!r}")
    validate_json({"operations": ops}, DESIGN_OUTPUT_SCHEMA)


__all__ = ["DesignAgent"]