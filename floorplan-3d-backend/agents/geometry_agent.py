"""Geometry Agent — selection-aware geometry operations.

The Geometry Agent NEVER picks colors, patterns, or materials. It maps
natural-language geometry intent into tool calls against the Blender
tool library. Each tool call is validated against the tool schema before
returning.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

from .base import Agent, AgentRequest, AgentResponse
from .prompts import GEOMETRY_AGENT_PROMPT
from .tools import TOOL_LIBRARY, validate_tool_call


_GEOMETRY_VERBS = {
    "curve": "curve_wall",
    "bend": "curve_wall",
    "round": "curve_wall",
    "bevel": "bevel_region",
    "chamfer": "bevel_region",
    "offset": "offset_region",
    "split": "split_region",
    "separate": "split_region",
    "merge": "merge_region",
    "combine": "merge_region",
    "extrude": "extrude_region",
    "push": "extrude_region",
    "pull": "extrude_region",
}


class GeometryAgent(Agent):
    name = "geometry"

    def __init__(self) -> None:
        super().__init__(GEOMETRY_AGENT_PROMPT)
        self._available_tools = [t.name for t in TOOL_LIBRARY]

    async def run(self, request: AgentRequest) -> AgentResponse:
        text = (request.prompt or "").strip()
        if not text:
            return AgentResponse(agent=self.name, error="empty prompt")

        text_low = text.lower()
        selected = request.selection_mesh_names or []
        if not selected:
            return AgentResponse(
                agent=self.name,
                error="no selection",
                needs_clarification="Select a region first.",
            )

        primary_object = selected[0]
        tool_calls: List[Dict[str, Any]] = []
        notes: List[str] = []

        # Detect verbs in priority order.
        verb_match: Optional[str] = None
        for verb, tool_name in _GEOMETRY_VERBS.items():
            if re.search(rf"\b{verb}\b", text_low):
                verb_match = tool_name
                break

        if verb_match is None:
            notes.append("no geometry verb detected in prompt")
            return AgentResponse(agent=self.name, tool_calls=[], notes=notes)

        # Build arguments per tool.
        args: Dict[str, Any] = {"object": primary_object}
        if verb_match == "curve_wall":
            args["radius"] = self._extract_radius(text_low) or 0.5
            args["axis"] = self._extract_axis(text_low) or "z"
        elif verb_match == "bevel_region":
            args["width"] = self._extract_distance(text_low) or 0.05
            args["face_indices"] = self._all_face_indices(request)
        elif verb_match == "offset_region":
            args["distance"] = self._extract_distance(text_low) or 0.05
            args["face_indices"] = self._all_face_indices(request)
        elif verb_match in {"split_region", "merge_region", "extrude_region"}:
            args["face_indices"] = self._all_face_indices(request)
            if verb_match == "extrude_region":
                args["distance"] = self._extract_distance(text_low) or 0.1

        tool_calls.append({"tool": verb_match, "arguments": args})

        # Validate before returning.
        for call in tool_calls:
            errors = validate_tool_call(call)
            if errors:
                return AgentResponse(agent=self.name, error="; ".join(errors))

        return AgentResponse(agent=self.name, tool_calls=tool_calls, notes=notes)

    @staticmethod
    def _extract_radius(text: str) -> Optional[float]:
        m = re.search(r"radius\s*=?\s*([0-9.]+)", text)
        return float(m.group(1)) if m else None

    @staticmethod
    def _extract_axis(text: str) -> Optional[str]:
        for axis in ("x", "y", "z"):
            if re.search(rf"\b{axis}\s*axis\b|\baxis\s*{axis}\b|\balong\s*{axis}\b", text):
                return axis
        return None

    @staticmethod
    def _extract_distance(text: str) -> Optional[float]:
        m = re.search(r"(?:by|of|=|)\s*([0-9.]+)\s*(?:m|cm|mm)?", text)
        return float(m.group(1)) if m else None

    @staticmethod
    def _all_face_indices(request: AgentRequest) -> List[int]:
        # Best-effort: use face count from summary if available.
        summary = request.selection_summary or {}
        count = summary.get("face_count")
        if isinstance(count, int) and count > 0:
            return list(range(count))
        return []