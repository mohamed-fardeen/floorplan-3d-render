"""Design Agent — interprets natural language into structured design ops.

The Design Agent NEVER executes Blender code. It returns structured
operations that the Execution Agent maps to tool calls.

This implementation is rule-based for deterministic behaviour. The prompt
is exposed as `system_prompt` so the same code path can be swapped for an
LLM-backed planner later without changing the agent interface.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

from .base import Agent, AgentRequest, AgentResponse
from .prompts import DESIGN_AGENT_PROMPT

COLOR_WORDS = {
    "white": "#F5F5F0",
    "black": "#1A1A1A",
    "navy": "#34495E",
    "sage": "#9CAF88",
    "sand": "#D4C4A8",
    "charcoal": "#3D3D3D",
    "warm": "#D8C8B8",
    "gray": "#9CA3AF",
    "grey": "#9CA3AF",
    "red": "#C0392B",
    "blue": "#3A6FA0",
    "green": "#5C8A4E",
    "yellow": "#E0C76A",
}

PATTERN_PHRASES = {
    "stacked coils": "stacked_coils",
    "stacked_coils": "stacked_coils",
    "coils": "stacked_coils",
    "woven rope": "woven_rope",
    "woven_rope": "woven_rope",
    "rope": "woven_rope",
    "ribbed": "ribbed",
    "brick": "brick",
    "wave": "wave",
    "smooth": "smooth",
    "solid": "smooth",
    "flat": "smooth",
}

PRESET_PHRASES = {
    "warm modern": "warm_modern",
    "painted white": "painted_white",
    "cool modern": "cool_modern",
    "stacked coils white": "stacked_coils_white",
    "woven rope natural": "woven_rope_natural",
}


class DesignAgent(Agent):
    name = "design"

    def __init__(self) -> None:
        super().__init__(DESIGN_AGENT_PROMPT)

    async def run(self, request: AgentRequest) -> AgentResponse:
        text = (request.prompt or "").strip()
        if not text:
            return AgentResponse(
                agent=self.name,
                error="empty prompt",
            )

        text_low = text.lower()
        ops: List[Dict[str, Any]] = []
        notes: List[str] = []

        # Color — explicit hex first, then word match.
        hex_match = re.search(r"#[0-9a-fA-F]{6}", text)
        if hex_match:
            ops.append({"type": "set_color", "value": hex_match.group(0).upper()})
        else:
            for word, hex_val in COLOR_WORDS.items():
                if re.search(rf"\b{word}\b", text_low):
                    ops.append({"type": "set_color", "value": hex_val})
                    break

        # Pattern — match against allowed library.
        for phrase, pattern_id in PATTERN_PHRASES.items():
            if phrase in text_low:
                if pattern_id in request.available_patterns or not request.available_patterns:
                    ops.append({"type": "apply_pattern", "pattern": pattern_id})
                    break
                notes.append(f"pattern {pattern_id} not in active library")

        # Material preset phrase.
        for phrase, preset_id in PRESET_PHRASES.items():
            if phrase in text_low:
                if preset_id in request.available_materials or not request.available_materials:
                    ops.append({"type": "set_material_preset", "preset": preset_id})
                    break

        if not ops:
            notes.append("no design intent detected; defaulting to current selection metadata")
            meta = (request.selection_summary or {}).get("current_metadata") or {}
            fallback = meta.get("color") or "#F5F5F0"
            ops.append({"type": "set_color", "value": fallback})

        return AgentResponse(
            agent=self.name,
            operations=ops,
            notes=notes,
        )


def parse_design_response_payload(payload: Dict[str, Any]) -> Optional[AgentResponse]:
    """Helper for LLM-backed implementations: validate a raw model payload."""
    if not isinstance(payload, dict):
        return None
    ops = payload.get("operations")
    if not isinstance(ops, list):
        return None
    cleaned: List[Dict[str, Any]] = []
    for op in ops:
        if not isinstance(op, dict):
            return None
        if "type" not in op:
            return None
        cleaned.append(op)
    notes = payload.get("notes", [])
    if not isinstance(notes, list):
        notes = []
    return AgentResponse(agent="design", operations=cleaned, notes=[str(n) for n in notes])