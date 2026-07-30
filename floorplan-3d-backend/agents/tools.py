"""Blender tool library — the Execution Agent's vocabulary.

Each tool is a structured operation the agent can invoke. Tools produce
either:
  - a structured MCP command (preferred — sent live to the addon), OR
  - a fragment of bpy code (used only when the tool is not yet implemented
    in the addon; the orchestrator wraps and runs it via the script path).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class BlenderTool:
    name: str
    description: str
    arg_schema: Dict[str, str]
    category: str  # "material" | "geometry" | "export"
    requires_live_mcp: bool = True

    def validate(self, args: Dict[str, Any]) -> List[str]:
        errors: List[str] = []
        for key, kind in self.arg_schema.items():
            if key not in args:
                errors.append(f"{self.name}: missing required arg {key!r}")
                continue
            value = args[key]
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


TOOL_LIBRARY: List[BlenderTool] = [
    BlenderTool(
        name="apply_pattern",
        description="Apply a printable pattern to the active selection's mesh.",
        arg_schema={"object": "string", "pattern": "string"},
        category="material",
    ),
    BlenderTool(
        name="apply_color",
        description="Apply a base color to the active selection's mesh.",
        arg_schema={"object": "string", "color": "string"},
        category="material",
    ),
    BlenderTool(
        name="assign_region_material",
        description="Assign a named material to specific faces of an object.",
        arg_schema={
            "object": "string",
            "material_name": "string",
            "face_indices": "int_list",
        },
        category="material",
    ),
    BlenderTool(
        name="curve_wall",
        description="Convert a straight wall to a curved geometry (radius / axis).",
        arg_schema={"object": "string", "radius": "number", "axis": "string"},
        category="geometry",
    ),
    BlenderTool(
        name="offset_region",
        description="Offset the selected faces along their averaged normal.",
        arg_schema={"object": "string", "face_indices": "int_list", "distance": "number"},
        category="geometry",
    ),
    BlenderTool(
        name="split_region",
        description="Split a contiguous region into separate islands.",
        arg_schema={"object": "string", "face_indices": "int_list"},
        category="geometry",
    ),
    BlenderTool(
        name="merge_region",
        description="Merge disconnected faces into one connected region.",
        arg_schema={"object": "string", "face_indices": "int_list"},
        category="geometry",
    ),
    BlenderTool(
        name="bevel_region",
        description="Bevel selected faces (curved printed walls use case).",
        arg_schema={
            "object": "string",
            "face_indices": "int_list",
            "width": "number",
        },
        category="geometry",
    ),
    BlenderTool(
        name="extrude_region",
        description="Extrude selected faces along their averaged normal.",
        arg_schema={
            "object": "string",
            "face_indices": "int_list",
            "distance": "number",
        },
        category="geometry",
    ),
    BlenderTool(
        name="export_glb",
        description="Export the current Blender scene as a GLB file.",
        arg_schema={"output_path": "string"},
        category="export",
    ),
]


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