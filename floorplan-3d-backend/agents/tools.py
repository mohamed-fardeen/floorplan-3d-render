"""Blender tool library — the Execution Agent's vocabulary.

Each tool is a structured operation the agent can invoke. Tools produce
either:
  - a structured MCP command (preferred — sent live to the addon), OR
  - a fragment of bpy code (used only when the tool is not yet implemented
    in the addon; the orchestrator wraps and runs it via the script path).

Tool metadata + argument schemas come from `tool_registry.py`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List

from .tool_registry import TOOL_REGISTRY, ToolMetadata


@dataclass
class BlenderTool:
    name: str
    description: str
    arg_schema: Dict[str, str]
    category: str
    requires_live_mcp: bool = True

    def validate(self, args: Dict[str, Any]) -> List[str]:
        errors: List[str] = []
        meta = TOOL_REGISTRY.get(self.name)
        required = set(meta.required_params) if meta else set(self.arg_schema.keys())
        optional = set(meta.optional_params) if meta else set()

        for key in required:
            if key not in args:
                errors.append(f"{self.name}: missing required arg {key!r}")
        for key, value in args.items():
            if key not in required and key not in optional:
                errors.append(f"{self.name}: unexpected arg {key!r}")
                continue
            kind = self.arg_schema.get(key)
            if not kind:
                continue
            if kind == "string" and not isinstance(value, str):
                errors.append(f"{self.name}.{key}: expected string")
            elif kind == "number" and not isinstance(value, (int, float)):
                errors.append(f"{self.name}.{key}: expected number")
            elif kind == "int" and not isinstance(value, int):
                errors.append(f"{self.name}.{key}: expected integer")
            elif kind == "string_list" and (
                not isinstance(value, list) or not all(isinstance(x, str) for x in value)
            ):
                errors.append(f"{self.name}.{key}: expected list of strings")
            elif kind == "int_list" and (
                not isinstance(value, list) or not all(isinstance(x, int) for x in value)
            ):
                errors.append(f"{self.name}.{key}: expected list of integers")
        return errors


# Tool argument schemas (kept here as a fast validation table).
_SCHEMAS: Dict[str, Dict[str, str]] = {
    # Geometry
    "curve_wall": {"object": "string", "radius": "number", "axis": "string", "segments": "int"},
    "bend_wall": {"object": "string", "angle": "number", "axis": "string", "pivot": "string"},
    "offset_wall": {"object": "string", "distance": "number"},
    "extrude_region": {"object": "string", "face_indices": "int_list", "distance": "number"},
    "bevel_region": {"object": "string", "face_indices": "int_list", "width": "number", "segments": "int"},
    "fillet_region": {"object": "string", "face_indices": "int_list", "radius": "number"},
    "smooth_region": {"object": "string", "face_indices": "int_list", "iterations": "int", "factor": "number"},
    "split_region": {"object": "string", "face_indices": "int_list"},
    "merge_region": {"object": "string", "face_indices": "int_list"},
    "duplicate_region": {"object": "string", "face_indices": "int_list", "offset": "number"},
    "project_region": {"object": "string", "face_indices": "int_list", "axis": "string"},

    # Pattern
    "apply_stacked_coils": {"object": "string", "depth": "number", "spacing": "number"},
    "apply_wave_pattern": {"object": "string", "amplitude": "number", "frequency": "number"},
    "apply_ribbed_pattern": {"object": "string", "depth": "number", "spacing": "number"},
    "apply_honeycomb_pattern": {"object": "string", "cell_size": "number", "depth": "number"},
    "apply_woven_pattern": {"object": "string", "weave_scale": "number"},
    "adjust_pattern_depth": {"object": "string", "depth": "number"},
    "adjust_pattern_spacing": {"object": "string", "spacing": "number"},
    "mirror_pattern": {"object": "string", "axis": "string"},
    "align_pattern": {"object": "string", "axis": "string"},

    # Material
    "set_color": {"object": "string", "color": "string"},
    "set_material": {"object": "string", "material_name": "string"},
    "copy_material": {"source": "string", "target": "string"},
    "mirror_material": {"object": "string"},
    "replace_material": {"find": "string", "replace": "string"},

    # Utility
    "measure_area": {"object": "string", "face_indices": "int_list"},
    "measure_length": {"object": "string", "face_indices": "int_list"},
    "calculate_volume": {"object": "string", "face_indices": "int_list"},
    "export_glb": {"output_path": "string"},
    "refresh_preview": {},
}


def _build_tools() -> List[BlenderTool]:
    out: List[BlenderTool] = []
    for name, meta in TOOL_REGISTRY.items():
        schema = _SCHEMAS.get(name, {})
        out.append(
            BlenderTool(
                name=name,
                description=meta.description,
                arg_schema=schema,
                category=meta.category,
            )
        )
    return out


TOOL_LIBRARY: List[BlenderTool] = _build_tools()


def tool_index() -> Dict[str, BlenderTool]:
    return {t.name: t for t in TOOL_LIBRARY}


def validate_tool_call(call: Dict[str, Any]) -> List[str]:
    name = call.get("tool")
    if not isinstance(name, str):
        return ["tool_call: missing 'tool' string"]
    idx = tool_index()
    if name not in idx:
        return [f"unknown tool: {name!r}"]
    args = call.get("arguments") or {}
    return idx[name].validate(args)


__all__ = ["BlenderTool", "TOOL_LIBRARY", "tool_index", "validate_tool_call"]