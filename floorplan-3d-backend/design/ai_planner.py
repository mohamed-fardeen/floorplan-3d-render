"""Rule-based design planner — returns structured actions, never Blender Python."""

from __future__ import annotations

import re
from typing import Any, Dict, List

from design.actions import DesignActionPlan, DesignOperation

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
    "smooth": "none",
    "solid": "none",
    "flat": "none",
}


def plan_from_prompt(prompt: str, selection_summary: Dict[str, Any] | None = None) -> DesignActionPlan:
    text = prompt.lower().strip()
    operations: List[DesignOperation] = []

    hex_match = re.search(r"#[0-9a-f]{6}", text, re.I)
    if hex_match:
        operations.append(DesignOperation(type="set_color", value=hex_match.group(0).upper()))

    for word, hex_color in COLOR_WORDS.items():
        if re.search(rf"\b{word}\b", text) and not hex_match:
            operations.append(DesignOperation(type="set_color", value=hex_color))
            break

    for phrase, pattern_id in PATTERN_PHRASES.items():
        if phrase in text:
            operations.append(DesignOperation(type="apply_pattern", pattern=pattern_id))
            break

    if "warm modern" in text:
        operations.append(DesignOperation(type="set_material_preset", preset="warm_modern"))
    elif "painted white" in text:
        operations.append(DesignOperation(type="set_material_preset", preset="painted_white"))

    if not operations:
        meta = (selection_summary or {}).get("current_metadata") or {}
        if meta.get("color"):
            operations.append(DesignOperation(type="set_color", value=meta["color"]))
        else:
            operations.append(DesignOperation(type="set_color", value="#F5F5F0"))

    return DesignActionPlan(selection="current", operations=operations)
