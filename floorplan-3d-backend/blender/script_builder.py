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
        "\nprint('Script complete.')\n",
    ]

    full_script = "\n\n".join(sections)
    with open(script_path, "w", encoding="utf-8") as f:
        f.write(full_script)

    return script_path
