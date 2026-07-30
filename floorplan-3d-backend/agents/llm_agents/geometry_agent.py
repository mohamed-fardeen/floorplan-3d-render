"""LLM-backed Geometry Agent with ordered tool-call output."""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional

from ..base import Agent, AgentRequest, AgentResponse
from ..output_schemas import GEOMETRY_OUTPUT_SCHEMA
from ..prompt_registry import GLOBAL_REGISTRY as PROMPTS
from ..tools import validate_tool_call
from ..llm.base import (
    CompletionRequest,
    LLMProvider,
    Message,
    ProviderUnavailable,
)
from .fallback import rule_based_plan

_log = logging.getLogger("agents.geometry")


_GEOMETRY_VERBS = {
    "curve": "curve_wall",
    "bend": "bend_wall",
    "round": "curve_wall",
    "bevel": "bevel_region",
    "chamfer": "bevel_region",
    "fillet": "fillet_region",
    "offset": "offset_wall",
    "split": "split_region",
    "separate": "split_region",
    "merge": "merge_region",
    "combine": "merge_region",
    "extrude": "extrude_region",
    "push": "extrude_region",
    "pull": "extrude_region",
    "smooth": "smooth_region",
}


class GeometryAgent(Agent):
    name = "geometry"

    def __init__(self, provider: Optional[LLMProvider] = None) -> None:
        super().__init__(PROMPTS.load("geometry").body)
        self._provider = provider

    def set_provider(self, provider: Optional[LLMProvider]) -> None:
        self._provider = provider

    async def run(self, request: AgentRequest) -> AgentResponse:
        if self._provider is None or not self._provider.is_available():
            return self._rule_based(request, reason="no LLM provider configured")

        try:
            structured = self._provider.structured(
                CompletionRequest(
                    messages=[
                        Message(role="system", content=self.system_message()),
                        Message(role="user", content=self._build_payload(request), images=request.context.get("images", []) or []),
                    ],
                    temperature=0.15,
                    max_tokens=600,
                ),
                schema=GEOMETRY_OUTPUT_SCHEMA,
                max_retries=1,
            )
            calls = structured.get("tool_calls", []) or []
            self._validate_calls(calls, request)
            return AgentResponse(
                agent=self.name,
                tool_calls=calls,
                notes=[structured.get("reasoning", "")],
                context_extra={"recommendations": structured.get("recommendations", []), "source": "llm"},
            )
        except (ProviderUnavailable, ValueError, json.JSONDecodeError) as exc:
            _log.warning("geometry agent LLM failed, falling back: %s", exc)
            return self._rule_based(request, reason=f"LLM failed: {exc}")

    def _build_payload(self, request: AgentRequest) -> str:
        selection_mesh = request.selection_mesh_names or []
        return "\n".join([
            f"USER PROMPT: {request.prompt}",
            "",
            "ACTIVE SELECTION:",
            json.dumps({
                "mesh_names": selection_mesh,
                "summary": request.selection_summary,
            }, indent=2),
            "",
            f"AVAILABLE TOOLS: {', '.join(request.available_tools)}",
            f"DESIGN INTENT: {request.context.get('design_intent', '')}",
            "",
            "Return only JSON matching the schema. Order operations so the",
            "result is printable (e.g. bevel BEFORE apply_pattern).",
        ])

    def _rule_based(self, request: AgentRequest, reason: str = "") -> AgentResponse:
        text_low = (request.prompt or "").lower()
        target = request.selection_mesh_names[0] if request.selection_mesh_names else None
        if target is None:
            return AgentResponse(agent=self.name, needs_clarification="Select a region first.")

        tool_name = None
        for verb, name in _GEOMETRY_VERBS.items():
            if re.search(rf"\b{verb}\b", text_low):
                tool_name = name
                break

        if tool_name is None:
            return AgentResponse(
                agent=self.name,
                tool_calls=[],
                notes=["no geometry verb detected"],
                context_extra={"source": "rules"},
            )

        args: Dict[str, Any] = {"object": target}
        if tool_name == "curve_wall":
            args["radius"] = 0.5
            args["axis"] = "z"
        elif tool_name == "bend_wall":
            args["angle"] = 30
            args["axis"] = "z"
        elif tool_name == "bevel_region":
            args["width"] = 0.05
            args["segments"] = 1
            args["face_indices"] = []
        elif tool_name == "fillet_region":
            args["radius"] = 0.05
            args["face_indices"] = []
        elif tool_name == "smooth_region":
            args["iterations"] = 1
            args["factor"] = 0.5
            args["face_indices"] = []
        elif tool_name == "extrude_region":
            args["distance"] = 0.1
            args["face_indices"] = []
        elif tool_name == "offset_wall":
            args["distance"] = 0.05
        else:
            args["face_indices"] = []

        call = {"tool": tool_name, "arguments": args}
        errs = validate_tool_call(call)
        if errs:
            return AgentResponse(agent=self.name, error="; ".join(errs))
        return AgentResponse(
            agent=self.name,
            tool_calls=[call],
            notes=[reason],
            context_extra={"source": "rules"},
        )

    def _validate_calls(self, calls: List[Dict[str, Any]], request: AgentRequest) -> None:
        valid_tools = set(request.available_tools or [])
        for call in calls:
            errs = validate_tool_call(call)
            if errs:
                raise ValueError("; ".join(errs))
            if valid_tools and call.get("tool") not in valid_tools:
                raise ValueError(f"unknown tool {call.get('tool')!r}")


import re  # noqa: E402  (used by _rule_based)


__all__ = ["GeometryAgent"]