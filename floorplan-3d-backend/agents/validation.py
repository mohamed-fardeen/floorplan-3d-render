"""Validation pipeline shared by orchestrator and execution layer.

Failures are returned as a structured list so the frontend can show
agent-friendly error messages.
"""

from __future__ import annotations

from typing import Any, Dict, List, Set

from .tools import TOOL_LIBRARY, validate_tool_call

VALID_PATTERN_IDS: Set[str] = {t for t in ("none", "smooth", "stacked_coils", "woven_rope", "ribbed", "brick", "wave")}
VALID_PRESET_IDS: Set[str] = {
    "warm_modern", "painted_white", "cool_modern", "sage", "sand", "navy",
    "clay", "blush", "charcoal", "olive", "sky", "custom",
    "stacked_coils_white", "woven_rope_natural",
}


def validate_design_operations(operations: List[Dict[str, Any]]) -> List[str]:
    errors: List[str] = []
    for i, op in enumerate(operations):
        if not isinstance(op, dict):
            errors.append(f"operations[{i}]: not a dict")
            continue
        op_type = op.get("type")
        if op_type not in {"apply_pattern", "set_color", "set_material_preset"}:
            errors.append(f"operations[{i}]: unknown type {op_type!r}")
            continue
        if op_type == "apply_pattern":
            pat = op.get("pattern")
            if pat not in VALID_PATTERN_IDS:
                errors.append(f"operations[{i}]: unknown pattern {pat!r}")
        elif op_type == "set_color":
            val = op.get("value") or ""
            if not (isinstance(val, str) and len(val) == 7 and val.startswith("#")):
                errors.append(f"operations[{i}]: invalid color {val!r}")
        elif op_type == "set_material_preset":
            preset = op.get("preset")
            if preset not in VALID_PRESET_IDS:
                errors.append(f"operations[{i}]: unknown preset {preset!r}")
    return errors


def validate_tool_calls(calls: List[Dict[str, Any]]) -> List[str]:
    errors: List[str] = []
    valid_tool_names = {t.name for t in TOOL_LIBRARY}
    for i, call in enumerate(calls):
        if not isinstance(call, dict):
            errors.append(f"tool_calls[{i}]: not a dict")
            continue
        tool = call.get("tool")
        if tool not in valid_tool_names:
            errors.append(f"tool_calls[{i}]: unknown tool {tool!r}")
            continue
        errs = validate_tool_call(call)
        for e in errs:
            errors.append(f"tool_calls[{i}]: {e}")
    return errors


def validate_selection_present(request: "AgentRequest") -> List[str]:  # noqa: F821
    if not request.selection_mesh_names:
        return ["no active selection"]
    return []


__all__ = [
    "VALID_PATTERN_IDS",
    "VALID_PRESET_IDS",
    "validate_design_operations",
    "validate_tool_calls",
    "validate_selection_present",
]