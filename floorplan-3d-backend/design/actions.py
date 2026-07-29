"""Structured design actions — validated and translated for Blender."""

from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field

VALID_PATTERNS = {"none", "stacked_coils", "woven_rope", "ribbed", "brick", "wave", "smooth"}
VALID_PRESETS = {
    "warm_modern", "painted_white", "cool_modern", "sage", "sand", "navy",
    "clay", "blush", "charcoal", "olive", "sky", "custom",
    "stacked_coils_white", "woven_rope_natural",
}

PRESET_COLORS = {
    "warm_modern": "#D8C8B8",
    "painted_white": "#F5F5F0",
    "cool_modern": "#C8D0D8",
    "navy": "#34495E",
    "sage": "#9CAF88",
    "sand": "#D4C4A8",
    "charcoal": "#3D3D3D",
    "stacked_coils_white": "#F0F0F0",
    "woven_rope_natural": "#C4A882",
}


class MeshReference(BaseModel):
    objectName: str
    meshUuid: Optional[str] = None


class FaceReference(BaseModel):
    meshRef: MeshReference
    faceIndex: int


class SelectionPayload(BaseModel):
    id: str
    meshRefs: List[MeshReference] = Field(default_factory=list)
    faceRefs: List[FaceReference] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class DesignOperation(BaseModel):
    type: Literal["apply_pattern", "set_color", "set_material_preset"]
    pattern: Optional[str] = None
    value: Optional[str] = None
    preset: Optional[str] = None


class DesignActionPlan(BaseModel):
    selection: str | Literal["current"] = "current"
    operations: List[DesignOperation]


def validate_operations(operations: List[DesignOperation]) -> List[str]:
    errors: List[str] = []
    for i, op in enumerate(operations):
        if op.type == "apply_pattern":
            pat = (op.pattern or "none").lower()
            if pat == "smooth":
                pat = "none"
            if pat not in VALID_PATTERNS:
                errors.append(f"operations[{i}]: unknown pattern {op.pattern!r}")
        elif op.type == "set_color":
            val = op.value or ""
            if not val.startswith("#") or len(val) != 7:
                errors.append(f"operations[{i}]: invalid color {val!r}")
        elif op.type == "set_material_preset":
            if (op.preset or "") not in VALID_PRESETS:
                errors.append(f"operations[{i}]: unknown preset {op.preset!r}")
    return errors


def translate_to_blender_options(
    operations: List[DesignOperation],
    base_material_options: Dict[str, Any],
    selection: SelectionPayload,
) -> Dict[str, Any]:
    """
    Convert structured design actions into blender_options extensions.
    Returns dict with material_options and region_overrides.
    """
    material_options = {
        "walls": dict(base_material_options.get("walls", {})),
        "floor": dict(base_material_options.get("floor", {})),
    }
    walls = material_options["walls"]

    for op in operations:
        if op.type == "set_color" and op.value:
            walls["color"] = op.value
            walls["theme"] = "custom"
        elif op.type == "apply_pattern":
            pat = (op.pattern or "none").lower()
            if pat == "smooth":
                pat = "none"
            # Browser-only previews map to Blender-supported patterns for now.
            if pat in {"ribbed", "brick", "wave"}:
                pat = "stacked_coils"
            walls["pattern"] = pat
        elif op.type == "set_material_preset" and op.preset:
            preset = op.preset
            if preset in PRESET_COLORS:
                walls["color"] = PRESET_COLORS[preset]
            if preset == "stacked_coils_white":
                walls["pattern"] = "stacked_coils"
            elif preset == "woven_rope_natural":
                walls["pattern"] = "woven_rope"
            else:
                walls["pattern"] = walls.get("pattern", "none")
            walls["theme"] = preset if preset in VALID_PRESETS else "custom"

    object_names = [m.objectName for m in selection.meshRefs if m.objectName]
    region_overrides = []
    if object_names:
        region_overrides.append({
            "object_names": object_names,
            "walls": dict(walls),
        })

    return {
        "material_options": material_options,
        "region_overrides": region_overrides,
    }
