"""Tool Registry — runtime metadata about every Blender tool the Execution
Agent can dispatch.

The Orchestrator and Execution Agent consult this registry before planning
so they only emit tool calls that Blender can actually run today.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set


@dataclass(frozen=True)
class ToolMetadata:
    name: str
    description: str
    category: str  # "geometry" | "pattern" | "material" | "utility"
    required_params: List[str]
    optional_params: List[str] = field(default_factory=list)
    supported_geometry: Set[str] = field(default_factory=set)
    supported_materials: Set[str] = field(default_factory=set)
    is_implemented: bool = True
    notes: str = ""

    def to_dict(self) -> Dict:
        return {
            "name": self.name,
            "description": self.description,
            "category": self.category,
            "required_params": list(self.required_params),
            "optional_params": list(self.optional_params),
            "supported_geometry": sorted(self.supported_geometry),
            "supported_materials": sorted(self.supported_materials),
            "is_implemented": self.is_implemented,
            "notes": self.notes,
        }


_GEOMETRY_ALL = {"wall", "floor", "ceiling", "door", "window", "any"}
_MATERIALS_ALL = {"concrete", "clay", "plaster", "composite", "any"}
_PATTERN_MATERIALS = {"concrete", "clay", "composite"}


TOOL_REGISTRY: Dict[str, ToolMetadata] = {
    # ── Geometry ────────────────────────────────────────────────────────
    "curve_wall": ToolMetadata(
        name="curve_wall",
        description="Curve a straight wall into a circular arc.",
        category="geometry",
        required_params=["object", "radius"],
        optional_params=["axis", "segments"],
        supported_geometry={"wall"},
        supported_materials=_MATERIALS_ALL,
    ),
    "bend_wall": ToolMetadata(
        name="bend_wall",
        description="Apply a localised bend to a wall region.",
        category="geometry",
        required_params=["object", "angle"],
        optional_params=["axis", "pivot"],
        supported_geometry={"wall"},
    ),
    "offset_wall": ToolMetadata(
        name="offset_wall",
        description="Offset wall geometry along its averaged normal.",
        category="geometry",
        required_params=["object", "distance"],
        supported_geometry={"wall"},
    ),
    "extrude_region": ToolMetadata(
        name="extrude_region",
        description="Extrude selected faces along their normal.",
        category="geometry",
        required_params=["object", "face_indices", "distance"],
        supported_geometry=_GEOMETRY_ALL,
    ),
    "bevel_region": ToolMetadata(
        name="bevel_region",
        description="Bevel selected faces — printable curvature transitions.",
        category="geometry",
        required_params=["object", "face_indices", "width"],
        optional_params=["segments"],
        supported_geometry=_GEOMETRY_ALL,
    ),
    "fillet_region": ToolMetadata(
        name="fillet_region",
        description="Fillet selected edges for printable chamfers.",
        category="geometry",
        required_params=["object", "face_indices", "radius"],
        supported_geometry=_GEOMETRY_ALL,
    ),
    "smooth_region": ToolMetadata(
        name="smooth_region",
        description="Apply smoothing to selected faces.",
        category="geometry",
        required_params=["object", "face_indices"],
        optional_params=["iterations", "factor"],
        supported_geometry=_GEOMETRY_ALL,
    ),
    "split_region": ToolMetadata(
        name="split_region",
        description="Split a region into separate face islands.",
        category="geometry",
        required_params=["object", "face_indices"],
        supported_geometry=_GEOMETRY_ALL,
    ),
    "merge_region": ToolMetadata(
        name="merge_region",
        description="Merge connected face islands into one region.",
        category="geometry",
        required_params=["object", "face_indices"],
        supported_geometry=_GEOMETRY_ALL,
    ),
    "duplicate_region": ToolMetadata(
        name="duplicate_region",
        description="Duplicate selected faces to a new object.",
        category="geometry",
        required_params=["object", "face_indices"],
        optional_params=["offset"],
        supported_geometry=_GEOMETRY_ALL,
    ),
    "project_region": ToolMetadata(
        name="project_region",
        description="Project selected faces onto a target plane.",
        category="geometry",
        required_params=["object", "face_indices", "axis"],
        supported_geometry=_GEOMETRY_ALL,
    ),

    # ── Pattern ────────────────────────────────────────────────────────
    "apply_stacked_coils": ToolMetadata(
        name="apply_stacked_coils",
        description="Apply the stacked-coils printable pattern.",
        category="pattern",
        required_params=["object"],
        optional_params=["depth", "spacing"],
        supported_materials=_PATTERN_MATERIALS,
        supported_geometry={"wall", "ceiling"},
    ),
    "apply_wave_pattern": ToolMetadata(
        name="apply_wave_pattern",
        description="Apply a sinusoidal wave pattern.",
        category="pattern",
        required_params=["object"],
        optional_params=["amplitude", "frequency"],
        supported_materials=_PATTERN_MATERIALS,
        supported_geometry={"wall", "ceiling"},
    ),
    "apply_ribbed_pattern": ToolMetadata(
        name="apply_ribbed_pattern",
        description="Apply vertical ribbed pattern.",
        category="pattern",
        required_params=["object"],
        optional_params=["depth", "spacing"],
        supported_materials=_PATTERN_MATERIALS,
        supported_geometry={"wall"},
    ),
    "apply_honeycomb_pattern": ToolMetadata(
        name="apply_honeycomb_pattern",
        description="Apply hexagonal honeycomb pattern.",
        category="pattern",
        required_params=["object"],
        optional_params=["cell_size", "depth"],
        supported_materials=_PATTERN_MATERIALS,
        supported_geometry={"wall", "floor"},
    ),
    "apply_woven_pattern": ToolMetadata(
        name="apply_woven_pattern",
        description="Apply woven-rope pattern.",
        category="pattern",
        required_params=["object"],
        optional_params=["weave_scale"],
        supported_materials=_PATTERN_MATERIALS,
        supported_geometry={"wall"},
    ),
    "adjust_pattern_depth": ToolMetadata(
        name="adjust_pattern_depth",
        description="Change the depth of the active pattern.",
        category="pattern",
        required_params=["object", "depth"],
        supported_materials=_PATTERN_MATERIALS,
    ),
    "adjust_pattern_spacing": ToolMetadata(
        name="adjust_pattern_spacing",
        description="Change the spacing of the active pattern.",
        category="pattern",
        required_params=["object", "spacing"],
        supported_materials=_PATTERN_MATERIALS,
    ),
    "mirror_pattern": ToolMetadata(
        name="mirror_pattern",
        description="Mirror the active pattern along an axis.",
        category="pattern",
        required_params=["object", "axis"],
        supported_materials=_PATTERN_MATERIALS,
    ),
    "align_pattern": ToolMetadata(
        name="align_pattern",
        description="Realign the active pattern to a world axis.",
        category="pattern",
        required_params=["object", "axis"],
        supported_materials=_PATTERN_MATERIALS,
    ),

    # ── Material ───────────────────────────────────────────────────────
    "set_color": ToolMetadata(
        name="set_color",
        description="Set the base color of the target object.",
        category="material",
        required_params=["object", "color"],
        supported_materials=_MATERIALS_ALL,
    ),
    "set_material": ToolMetadata(
        name="set_material",
        description="Assign a registered material to the target object.",
        category="material",
        required_params=["object", "material_name"],
        supported_materials=_MATERIALS_ALL,
    ),
    "copy_material": ToolMetadata(
        name="copy_material",
        description="Copy material from one object to another.",
        category="material",
        required_params=["source", "target"],
        supported_materials=_MATERIALS_ALL,
    ),
    "mirror_material": ToolMetadata(
        name="mirror_material",
        description="Mirror material to the opposite face of the same object.",
        category="material",
        required_params=["object"],
        supported_materials=_MATERIALS_ALL,
    ),
    "replace_material": ToolMetadata(
        name="replace_material",
        description="Replace every occurrence of a material in the scene.",
        category="material",
        required_params=["find", "replace"],
        supported_materials=_MATERIALS_ALL,
    ),

    # ── Utility ────────────────────────────────────────────────────────
    "measure_area": ToolMetadata(
        name="measure_area",
        description="Measure the world-space area of the selection.",
        category="utility",
        required_params=["object", "face_indices"],
    ),
    "measure_length": ToolMetadata(
        name="measure_length",
        description="Measure length of an edge or sum of edge lengths.",
        category="utility",
        required_params=["object"],
        optional_params=["face_indices"],
    ),
    "calculate_volume": ToolMetadata(
        name="calculate_volume",
        description="Compute the volume of the selection's bounding region.",
        category="utility",
        required_params=["object", "face_indices"],
    ),
    "export_glb": ToolMetadata(
        name="export_glb",
        description="Export the current Blender scene to a GLB file.",
        category="utility",
        required_params=["output_path"],
    ),
    "refresh_preview": ToolMetadata(
        name="refresh_preview",
        description="Force-refresh the Blender preview / viewport shading.",
        category="utility",
        required_params=[],
    ),
}


def get(name: str) -> Optional[ToolMetadata]:
    return TOOL_REGISTRY.get(name)


def all_names() -> List[str]:
    return list(TOOL_REGISTRY.keys())


def by_category(category: str) -> List[ToolMetadata]:
    return [t for t in TOOL_REGISTRY.values() if t.category == category]


def implemented() -> List[ToolMetadata]:
    return [t for t in TOOL_REGISTRY.values() if t.is_implemented]


def compatible_with(geometry_kind: str) -> List[str]:
    return [
        t.name for t in TOOL_REGISTRY.values()
        if not t.supported_geometry or geometry_kind in t.supported_geometry
    ]


__all__ = [
    "ToolMetadata",
    "TOOL_REGISTRY",
    "get",
    "all_names",
    "by_category",
    "implemented",
    "compatible_with",
]