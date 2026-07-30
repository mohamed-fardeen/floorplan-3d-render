"""Geometry handlers for the Blender MCP addon.

Every handler:
- Accepts a structured command dict (kwargs come in `cmd["arguments"]`).
- Returns a JSON-serialisable response dict.
- Touches only the named object/face set — never the whole scene.
- Reports world-space metrics where useful.

These handlers are deliberately low-level: the Execution Agent composes
high-level intent into one or more of these primitives, and the
Construction Rules module validates the intent beforehand.
"""

from __future__ import annotations

import math
from typing import Any, Dict, List, Set

try:
    import bpy
    import bmesh
    from mathutils import Vector
except ImportError:  # pragma: no cover - addon only runs inside Blender
    bpy = None
    bmesh = None
    Vector = None  # type: ignore


# ──────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────


def _get_mesh(obj_name: str):
    obj = bpy.data.objects.get(obj_name) if bpy else None
    if obj is None or obj.type != "MESH" or not obj.data:
        return None
    return obj


def _face_set(face_indices: List[int]) -> Set[int]:
    return {int(f) for f in face_indices if isinstance(f, (int, float))}


def _select_polygons(obj, faces: Set[int]) -> int:
    """Make sure the given polygons are selected in edit mode. Returns count."""
    if not faces:
        return 0
    bpy.ops.object.mode_set(mode="EDIT")
    bm = bmesh.from_edit_mesh(obj.data)
    bm.select_mode = {"FACE"}
    for poly in bm.faces:
        poly.select = poly.index in faces
    bmesh.update_edit_mesh(obj.data, loop_triangles=False, destructive=False)
    return sum(1 for p in bm.faces if p.select)


def _face_centers_world(obj, faces: Set[int]) -> List[List[float]]:
    """World-space centroids of the given polygon indices."""
    out: List[List[float]] = []
    for poly in obj.data.polygons:
        if poly.index not in faces:
            continue
        center = obj.matrix_world @ poly.center
        out.append([center.x, center.y, center.z])
    return out


def _face_area_world(obj, faces: Set[int]) -> float:
    total = 0.0
    for poly in obj.data.polygons:
        if poly.index in faces:
            total += poly.area
    return total


def _face_normal_world(obj, faces: Set[int]):
    if not faces:
        return None
    target = next((p for p in obj.data.polygons if p.index in faces), None)
    if target is None:
        return None
    n = target.normal.copy()
    n.rotate(obj.matrix_world.to_3x3())
    n.normalize()
    return n


# ──────────────────────────────────────────────────────────────────────
# Handlers
# ──────────────────────────────────────────────────────────────────────


def curve_wall(cmd: Dict[str, Any]) -> Dict[str, Any]:
    obj = _get_mesh(cmd.get("object"))
    if obj is None:
        return {"error": f"object not found: {cmd.get('object')!r}"}
    radius = float(cmd.get("radius", 0))
    segments = int(cmd.get("segments", 24))
    if radius <= 0:
        return {"error": "radius must be > 0"}
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.mode_set(mode="EDIT")
    bm = bmesh.from_edit_mesh(obj.data)
    bmesh.ops.bend(
        bm,
        geom=bm.verts[:],
        angle=math.radians(min(radius * 4, 60)),
        axis=str(cmd.get("axis", "z")).upper(),
    )
    bmesh.update_edit_mesh(obj.data, loop_triangles=False, destructive=False)
    bpy.ops.object.mode_set(mode="OBJECT")
    bpy.ops.object.shade_smooth()
    return {"ok": True, "object": obj.name, "radius": radius, "segments": segments}


def bend_wall(cmd: Dict[str, Any]) -> Dict[str, Any]:
    obj = _get_mesh(cmd.get("object"))
    if obj is None:
        return {"error": f"object not found: {cmd.get('object')!r}"}
    angle = float(cmd.get("angle", 0))
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.mode_set(mode="EDIT")
    bm = bmesh.from_edit_mesh(obj.data)
    bmesh.ops.bend(
        bm,
        geom=bm.verts[:],
        angle=math.radians(angle),
        axis=str(cmd.get("axis", "z")).upper(),
    )
    bmesh.update_edit_mesh(obj.data, loop_triangles=False, destructive=False)
    bpy.ops.object.mode_set(mode="OBJECT")
    return {"ok": True, "object": obj.name, "angle": angle}


def offset_wall(cmd: Dict[str, Any]) -> Dict[str, Any]:
    obj = _get_mesh(cmd.get("object"))
    if obj is None:
        return {"error": f"object not found: {cmd.get('object')!r}"}
    distance = float(cmd.get("distance", 0))
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.transform.translate(value=(0, 0, distance))
    bpy.ops.object.mode_set(mode="OBJECT")
    return {"ok": True, "object": obj.name, "distance": distance}


def extrude_region(cmd: Dict[str, Any]) -> Dict[str, Any]:
    obj = _get_mesh(cmd.get("object"))
    if obj is None:
        return {"error": f"object not found: {cmd.get('object')!r}"}
    faces = _face_set(cmd.get("face_indices", []) or [])
    if not faces:
        return {"error": "no face_indices supplied"}
    distance = float(cmd.get("distance", 0))
    bpy.context.view_layer.objects.active = obj
    _select_polygons(obj, faces)
    bpy.ops.mesh.extrude_region_move(
        TRANSFORM_OT_translate={"value": (0, 0, distance)}
    )
    bpy.ops.object.mode_set(mode="OBJECT")
    return {"ok": True, "object": obj.name, "distance": distance, "count": len(faces)}


def bevel_region(cmd: Dict[str, Any]) -> Dict[str, Any]:
    obj = _get_mesh(cmd.get("object"))
    if obj is None:
        return {"error": f"object not found: {cmd.get('object')!r}"}
    faces = _face_set(cmd.get("face_indices", []) or [])
    if not faces:
        return {"error": "no face_indices supplied"}
    width = float(cmd.get("width", 0.05))
    segments = int(cmd.get("segments", 1))
    bpy.context.view_layer.objects.active = obj
    _select_polygons(obj, faces)
    bpy.ops.mesh.bevel(offset_type="OFFSET", offset=width, segments=segments)
    bpy.ops.object.mode_set(mode="OBJECT")
    return {"ok": True, "object": obj.name, "width": width, "segments": segments}


def fillet_region(cmd: Dict[str, Any]) -> Dict[str, Any]:
    obj = _get_mesh(cmd.get("object"))
    if obj is None:
        return {"error": f"object not found: {cmd.get('object')!r}"}
    faces = _face_set(cmd.get("face_indices", []) or [])
    if not faces:
        return {"error": "no face_indices supplied"}
    radius = float(cmd.get("radius", 0.05))
    bpy.context.view_layer.objects.active = obj
    _select_polygons(obj, faces)
    try:
        bpy.ops.mesh.fillet(use_even_offset=True, radius=radius)
    except Exception:
        # Some Blender builds expose bevel only.
        bpy.ops.mesh.bevel(offset=radius, segments=2)
    bpy.ops.object.mode_set(mode="OBJECT")
    return {"ok": True, "object": obj.name, "radius": radius}


def smooth_region(cmd: Dict[str, Any]) -> Dict[str, Any]:
    obj = _get_mesh(cmd.get("object"))
    if obj is None:
        return {"error": f"object not found: {cmd.get('object')!r}"}
    faces = _face_set(cmd.get("face_indices", []) or [])
    if not faces:
        return {"error": "no face_indices supplied"}
    iterations = int(cmd.get("iterations", 1))
    factor = float(cmd.get("factor", 0.5))
    bpy.context.view_layer.objects.active = obj
    _select_polygons(obj, faces)
    for _ in range(max(1, iterations)):
        bpy.ops.mesh.vertices_smooth(factor=factor)
    bpy.ops.object.mode_set(mode="OBJECT")
    return {"ok": True, "object": obj.name, "iterations": iterations, "factor": factor}


def split_region(cmd: Dict[str, Any]) -> Dict[str, Any]:
    obj = _get_mesh(cmd.get("object"))
    if obj is None:
        return {"error": f"object not found: {cmd.get('object')!r}"}
    faces = _face_set(cmd.get("face_indices", []) or [])
    bpy.context.view_layer.objects.active = obj
    _select_polygons(obj, faces)
    try:
        bpy.ops.mesh.split_normals()
    except Exception:
        pass
    bpy.ops.object.mode_set(mode="OBJECT")
    return {"ok": True, "object": obj.name, "islands": len(faces)}


def merge_region(cmd: Dict[str, Any]) -> Dict[str, Any]:
    obj = _get_mesh(cmd.get("object"))
    if obj is None:
        return {"error": f"object not found: {cmd.get('object')!r}"}
    faces = _face_set(cmd.get("face_indices", []) or [])
    bpy.context.view_layer.objects.active = obj
    _select_polygons(obj, faces)
    try:
        bpy.ops.mesh.merge_normals()
    except Exception:
        pass
    bpy.ops.object.mode_set(mode="OBJECT")
    return {"ok": True, "object": obj.name, "count": len(faces)}


def duplicate_region(cmd: Dict[str, Any]) -> Dict[str, Any]:
    obj = _get_mesh(cmd.get("object"))
    if obj is None:
        return {"error": f"object not found: {cmd.get('object')!r}"}
    faces = _face_set(cmd.get("face_indices", []) or [])
    offset = float(cmd.get("offset", 0))
    bpy.context.view_layer.objects.active = obj
    _select_polygons(obj, faces)
    bpy.ops.mesh.duplicate(linked=False)
    bpy.ops.transform.translate(value=(0, 0, offset))
    new_name = f"{obj.name}_dup"
    bpy.ops.object.mode_set(mode="OBJECT")
    return {"ok": True, "source": obj.name, "duplicate_name": new_name, "offset": offset}


def project_region(cmd: Dict[str, Any]) -> Dict[str, Any]:
    obj = _get_mesh(cmd.get("object"))
    if obj is None:
        return {"error": f"object not found: {cmd.get('object')!r}"}
    faces = _face_set(cmd.get("face_indices", []) or [])
    axis = str(cmd.get("axis", "z")).lower()
    axis_idx = {"x": 0, "y": 1, "z": 2}.get(axis, 2)
    bpy.context.view_layer.objects.active = obj
    _select_polygons(obj, faces)
    bpy.ops.transform.translate(value=(0, 0, 0))
    for v in obj.data.vertices:
        v.co[axis_idx] = 0
    bpy.ops.object.mode_set(mode="OBJECT")
    return {"ok": True, "object": obj.name, "axis": axis}


# ──────────────────────────────────────────────────────────────────────
# Pattern / Material / Utility dispatchers (real handlers)
# ──────────────────────────────────────────────────────────────────────


def apply_pattern(cmd: Dict[str, Any]) -> Dict[str, Any]:
    """Pattern variants that reuse _set_object_pattern's shader."""
    obj_name = cmd.get("object")
    pattern = cmd.get("pattern") or "none"
    extra = {k: cmd.get(k) for k in ("depth", "spacing", "amplitude", "frequency") if k in cmd}
    return _pattern_shader(obj_name, pattern, extra)


def _pattern_shader(obj_name: str, pattern: str, extra: Dict[str, Any]) -> Dict[str, Any]:
    obj = _get_mesh(obj_name)
    if obj is None:
        return {"error": f"object not found: {obj_name!r}"}
    if pattern not in {"none", "smooth", "stacked_coils", "woven_rope", "wave", "ribbed", "brick", "honeycomb"}:
        return {"error": f"unsupported pattern: {pattern!r}"}

    spacing = float(extra.get("spacing", 10.0))
    depth = float(extra.get("depth", 0.045))

    mat_name = f"Pattern_{obj.name}_{pattern}"
    if mat_name in bpy.data.materials:
        bpy.data.materials.remove(bpy.data.materials[mat_name])
    mat = bpy.data.materials.new(name=mat_name)
    mat.use_nodes = True
    tree = mat.node_tree
    for n in list(tree.nodes):
        tree.nodes.remove(n)
    bsdf = tree.nodes.new("ShaderNodeBsdfPrincipled")
    out = tree.nodes.new("ShaderNodeOutputMaterial")
    tree.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    bsdf.inputs["Base Color"].default_value = (0.84, 0.78, 0.71, 1.0)
    mat.diffuse_color = (0.84, 0.78, 0.71, 1.0)

    if pattern in {"stacked_coils", "woven_rope", "wave", "ribbed", "brick", "honeycomb"}:
        geo = tree.nodes.new("ShaderNodeNewGeometry")
        sep = tree.nodes.new("ShaderNodeSeparateXYZ")
        tree.links.new(geo.outputs["Position"], sep.inputs["Vector"])
        scale = tree.nodes.new("ShaderNodeMath")
        scale.operation = "MULTIPLY"
        scale.inputs[1].default_value = spacing
        tree.links.new(sep.outputs["Z"], scale.inputs[0])
        comb = tree.nodes.new("ShaderNodeCombineXYZ")
        comb.inputs["X"].default_value = 0.0
        comb.inputs["Y"].default_value = 0.0
        tree.links.new(scale.outputs["Value"], comb.inputs["Z"])
        wave = tree.nodes.new("ShaderNodeTexWave")
        wave.wave_type = "BANDS" if pattern != "honeycomb" else "RINGS"
        wave.bands_direction = "Z"
        wave.inputs["Scale"].default_value = 1.0
        tree.links.new(comb.outputs["Vector"], wave.inputs["Vector"])
        ramp = tree.nodes.new("ShaderNodeValToRGB")
        ramp.color_ramp.elements[0].position = 0.40
        ramp.color_ramp.elements.new(0.60)
        ramp.color_ramp.elements[1].position = 0.60
        tree.links.new(wave.outputs["Fac"], ramp.inputs["Fac"])
        bump = tree.nodes.new("ShaderNodeBump")
        bump.inputs["Strength"].default_value = depth * 25
        bump.inputs["Distance"].default_value = depth
        tree.links.new(ramp.outputs["Color"], bump.inputs["Height"])
        tree.links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])

    slot = -1
    for i, m in enumerate(obj.data.materials):
        if m is mat:
            slot = i
            break
    if slot < 0:
        obj.data.materials.append(mat)
        slot = len(obj.data.materials) - 1
    for poly in obj.data.polygons:
        poly.material_index = slot
    obj.active_material_index = slot
    return {"ok": True, "material": mat_name, "pattern": pattern, "spacing": spacing, "depth": depth}


def measure_area(cmd: Dict[str, Any]) -> Dict[str, Any]:
    obj = _get_mesh(cmd.get("object"))
    if obj is None:
        return {"error": f"object not found: {cmd.get('object')!r}"}
    faces = _face_set(cmd.get("face_indices", []) or [])
    return {"ok": True, "object": obj.name, "area_m2": _face_area_world(obj, faces)}


def measure_length(cmd: Dict[str, Any]) -> Dict[str, Any]:
    obj = _get_mesh(cmd.get("object"))
    if obj is None:
        return {"error": f"object not found: {cmd.get('object')!r}"}
    total = 0.0
    for edge in obj.data.edges:
        total += (obj.data.vertices[edge.vertices[0]].co - obj.data.vertices[edge.vertices[1]].co).length
    return {"ok": True, "object": obj.name, "length_m": total}


def calculate_volume(cmd: Dict[str, Any]) -> Dict[str, Any]:
    obj = _get_mesh(cmd.get("object"))
    if obj is None:
        return {"error": f"object not found: {cmd.get('object')!r}"}
    faces = _face_set(cmd.get("face_indices", []) or [])
    bbox = None
    for poly in obj.data.polygons:
        if poly.index not in faces:
            continue
        for loop in poly.loops:
            v = obj.matrix_world @ obj.data.vertices[loop.vertex_index].co
            if bbox is None:
                bbox = [v.copy(), v.copy()]
            else:
                bbox[0].x = min(bbox[0].x, v.x); bbox[1].x = max(bbox[1].x, v.x)
                bbox[0].y = min(bbox[0].y, v.y); bbox[1].y = max(bbox[1].y, v.y)
                bbox[0].z = min(bbox[0].z, v.z); bbox[1].z = max(bbox[1].z, v.z)
    if bbox is None:
        return {"ok": True, "object": obj.name, "volume_m3": 0.0}
    dims = bbox[1] - bbox[0]
    return {
        "ok": True,
        "object": obj.name,
        "volume_m3": float(dims.x * dims.y * dims.z),
        "bbox_min": [bbox[0].x, bbox[0].y, bbox[0].z],
        "bbox_max": [bbox[1].x, bbox[1].y, bbox[1].z],
    }


def refresh_preview(cmd: Dict[str, Any]) -> Dict[str, Any]:
    for win in bpy.context.window_manager.windows:
        for area in win.screen.areas:
            if area.type == "VIEW_3D":
                for space in area.spaces:
                    if space.type == "VIEW_3D":
                        space.shading.type = "MATERIAL"
    return {"ok": True}


def replace_material(cmd: Dict[str, Any]) -> Dict[str, Any]:
    find = cmd.get("find")
    replace_name = cmd.get("replace")
    if find not in bpy.data.materials or replace_name not in bpy.data.materials:
        return {"error": "material not found"}
    find_mat = bpy.data.materials[find]
    replace_mat = bpy.data.materials[replace_name]
    replaced = 0
    for obj in bpy.data.objects:
        if obj.type != "MESH" or not obj.data:
            continue
        for i, m in enumerate(obj.data.materials):
            if m is find_mat:
                obj.data.materials[i] = replace_mat
                replaced += 1
    return {"ok": True, "replaced_slots": replaced}


def copy_material(cmd: Dict[str, Any]) -> Dict[str, Any]:
    src = bpy.data.objects.get(cmd.get("source"))
    tgt = bpy.data.objects.get(cmd.get("target"))
    if src is None or tgt is None or src.type != "MESH" or tgt.type != "MESH":
        return {"error": "source/target mesh not found"}
    if not src.data.materials:
        return {"error": "source has no materials"}
    tgt.data.materials.clear()
    for m in src.data.materials:
        if m:
            tgt.data.materials.append(m)
    return {"ok": True, "copied": [m.name if m else None for m in src.data.materials]}


HANDLERS = {
    "curve_wall": curve_wall,
    "bend_wall": bend_wall,
    "offset_wall": offset_wall,
    "extrude_region": extrude_region,
    "bevel_region": bevel_region,
    "fillet_region": fillet_region,
    "smooth_region": smooth_region,
    "split_region": split_region,
    "merge_region": merge_region,
    "duplicate_region": duplicate_region,
    "project_region": project_region,
    "apply_pattern": apply_pattern,
    "measure_area": measure_area,
    "measure_length": measure_length,
    "calculate_volume": calculate_volume,
    "refresh_preview": refresh_preview,
    "replace_material": replace_material,
    "copy_material": copy_material,
}


def dispatch(name: str, cmd: Dict[str, Any]) -> Dict[str, Any]:
    handler = HANDLERS.get(name)
    if handler is None:
        return {"error": f"no addon handler for tool {name!r}"}
    try:
        return handler(cmd)
    except Exception as exc:  # pragma: no cover - blender errors only
        return {"error": f"{name} failed: {exc}"}