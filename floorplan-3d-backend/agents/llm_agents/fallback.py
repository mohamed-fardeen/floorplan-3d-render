"""Rule-based fallback planner shared by all LLM agents."""

from __future__ import annotations

import re
from typing import Any, Dict, List, Tuple

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
    "honeycomb": "honeycomb",
}

PRESET_PHRASES = {
    "warm modern": "warm_modern",
    "painted white": "painted_white",
    "cool modern": "cool_modern",
    "stacked coils white": "stacked_coils_white",
    "woven rope natural": "woven_rope_natural",
}


def rule_based_plan(prompt: str) -> Tuple[List[Dict[str, Any]], List[str]]:
    text = (prompt or "").strip()
    text_low = text.lower()
    ops: List[Dict[str, Any]] = []
    notes: List[str] = []

    hex_match = re.search(r"#[0-9a-fA-F]{6}", text)
    if hex_match:
        ops.append({"type": "set_color", "value": hex_match.group(0).upper()})
    else:
        for word, hex_val in COLOR_WORDS.items():
            if re.search(rf"\b{word}\b", text_low):
                ops.append({"type": "set_color", "value": hex_val})
                break

    for phrase, pid in PATTERN_PHRASES.items():
        if phrase in text_low:
            ops.append({"type": "apply_pattern", "pattern": pid})
            break

    for phrase, preset in PRESET_PHRASES.items():
        if phrase in text_low:
            ops.append({"type": "set_material_preset", "preset": preset})
            break

    if not ops:
        notes.append("no design intent detected")

    return ops, notes


__all__ = ["rule_based_plan"]