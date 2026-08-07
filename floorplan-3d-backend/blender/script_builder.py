"""
script_builder.py
Assembles a self-contained, headless-executable bpy Python script
from the validated Scene Graph and config. No LLM calls, no inference.
"""
import os
from blender.builders import (
    build_floors, build_walls, build_openings,
    build_ceilings, build_materials, build_lighting,
    build_cameras, build_exports,
)
from blender.asset_manager import build_furniture_code
HEADER = """\
# ====================================================================
# AUTO-GENERATED BLENDER SCRIPT
# Source: FloorPlan-3D Pipeline
# DO NOT EDIT MANUALLY — regenerate by re-running the pipeline
# ====================================================================
import bpy, math, mathutils

# ── Scene Reset ──────────────────────────────────────────────────────
for obj in list(bpy.data.objects):
    bpy.data.objects.remove(obj, do_unlink=True)
for col in list(bpy.data.collections):
    bpy.data.collections.remove(col)
for mat in list(bpy.data.materials):
    bpy.data.materials.remove(mat)

# ── Units ────────────────────────────────────────────────────────────
bpy.context.scene.unit_settings.system = 'METRIC'
bpy.context.scene.unit_settings.length_unit = 'METERS'
bpy.context.scene.unit_settings.scale_length = 1.0

# ── Collection ───────────────────────────────────────────────────────
main_col = bpy.data.collections.new('Building')
bpy.context.scene.collection.children.link(main_col)
bpy.context.view_layer.active_layer_collection = \\
    bpy.context.view_layer.layer_collection.children['Building']

"""


def _bbox(scene_graph) -> tuple[float, float, float]:
    xs, ys = [], []
    for w in scene_graph.walls:
        xs += [w.start[0], w.end[0]]
        ys += [w.start[1], w.end[1]]
    for r in scene_graph.rooms:
        for x, y in r.polygon:
            xs.append(x)
            ys.append(y)
    if not xs:
        return 5.0, 5.0, 10.0
    pad = 2.0
    min_x, max_x = min(xs) - pad, max(xs) + pad
    min_y, max_y = min(ys) - pad, max(ys) + pad
    return (
        (min_x + max_x) / 2.0,
        (min_y + max_y) / 2.0,
        max(max_x - min_x, max_y - min_y, 1.0),
    )


FOOTER = """\


# ── Apply Boolean modifiers before scale baking ─────────────────────
# Step 1: Apply scale on all Cutter objects first so their geometry
#         is correctly sized before the Boolean operation executes.
for _obj in bpy.data.objects:
    if _obj.type != 'MESH':
        continue
    if not _obj.name.startswith('Cutter_'):
        continue
    bpy.context.view_layer.objects.active = _obj
    _obj.select_set(True)
    try:
        bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
    except Exception:
        pass
    _obj.select_set(False)

# Step 2: Apply all pending Boolean modifiers on wall objects so the
#         openings are permanently cut into the mesh before export.
for _obj in bpy.data.objects:
    if _obj.type != 'MESH':
        continue
    if _obj.name.startswith('Cutter_'):
        continue
    _bool_mods = [m for m in _obj.modifiers if m.type == 'BOOLEAN']
    if not _bool_mods:
        continue
    bpy.context.view_layer.objects.active = _obj
    _obj.select_set(True)
    for _mod in _bool_mods:
        try:
            bpy.ops.object.modifier_apply(modifier=_mod.name)
        except Exception:
            pass
    _obj.select_set(False)

# Step 3: Hide cutter objects from viewport and render (they are consumed)
for _obj in bpy.data.objects:
    if _obj.name.startswith('Cutter_'):
        _obj.hide_viewport = True
        _obj.hide_render = True

# ── Origin Centring ─────────────────────────────────────────────────
# Bake every geometry object's scale into its mesh, then recompute the bbox
# in world space and translate the entire scene so the base centre sits at
# the world origin. This makes the result robust to any base-plate padding
# or scale changes upstream.
for _obj in bpy.data.objects:
    if _obj.type == 'CAMERA' or _obj.type == 'LIGHT':
        continue
    if _obj.name.startswith('Cutter_'):
        continue
    if _obj.data and hasattr(_obj.data, 'vertices'):
        try:
            bpy.context.view_layer.objects.active = _obj
            _obj.select_set(True)
            bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
        except Exception:
            pass
        _obj.select_set(False)

_min_x, _min_y, _min_z = 1e30, 1e30, 1e30
_max_x, _max_y, _max_z = -1e30, -1e30, -1e30
for _obj in bpy.data.objects:
    if _obj.type == 'CAMERA' or _obj.type == 'LIGHT':
        continue
    if _obj.name.startswith('Cutter_'):
        continue
    if not _obj.data or not hasattr(_obj.data, 'vertices'):
        continue
    for _v in _obj.data.vertices:
        _w = _obj.matrix_world @ _v.co
        if _w.x < _min_x: _min_x = _w.x
        if _w.y < _min_y: _min_y = _w.y
        if _w.z < _min_z: _min_z = _w.z
        if _w.x > _max_x: _max_x = _w.x
        if _w.y > _max_y: _max_y = _w.y
        if _w.z > _max_z: _max_z = _w.z
if _min_x <= _max_x:
    _cx = (_min_x + _max_x) / 2.0
    _cy = (_min_y + _max_y) / 2.0
    _cz = _min_z
    _span = max(_max_x - _min_x, _max_y - _min_y, 1.0)
    for _obj in bpy.data.objects:
        if _obj.type == 'CAMERA' or _obj.type == 'LIGHT':
            continue
        _obj.location.x -= _cx
        _obj.location.y -= _cy
        _obj.location.z -= _cz
    for _obj in bpy.data.objects:
        if _obj.type == 'CAMERA':
            _obj.location.x -= _cx
            _obj.location.y -= _cy
            if _obj.data and _obj.data.type == 'ORTHO' and 'TopDown' in _obj.name:
                _obj.data.ortho_scale = _span * 1.2
"""


def build_script(scene_graph, cfg: dict, output_dir: str, script_path: str) -> str:
    """
    Builds and writes the full bpy script to disk.
    Returns the path of the written file.
    """
    os.makedirs(output_dir, exist_ok=True)
    os.makedirs(os.path.dirname(script_path) if os.path.dirname(script_path) else ".", exist_ok=True)

    sections = [
        HEADER,
        build_floors(scene_graph, cfg) if cfg.get("include_base", True) else "",
        build_walls(scene_graph, cfg),
        build_openings(scene_graph, cfg),
        build_ceilings(scene_graph, cfg) if cfg.get("include_roof", True) else "",
        build_furniture_code(scene_graph, cfg),
        build_materials(scene_graph, cfg),
        build_lighting(scene_graph, cfg),
        build_cameras(scene_graph, cfg),
        build_exports(scene_graph, cfg, output_dir),
        FOOTER,
        "\nprint('Script complete.')\n",
    ]

    full_script = "\n\n".join(sections)
    with open(script_path, "w", encoding="utf-8") as f:
        f.write(full_script)

    return script_path
