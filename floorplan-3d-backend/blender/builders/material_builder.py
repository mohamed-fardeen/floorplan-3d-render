"""
material_builder.py
Generates bpy code to create and assign PBR material presets.
Materials are data-driven from config.yaml. No values are hardcoded.
"""

# Colour presets: material_key -> (R, G, B, roughness)
MATERIAL_PRESETS = {
    "painted_white":    (0.95, 0.95, 0.95, 0.85),
    "plaster_white":    (0.93, 0.93, 0.90, 0.90),
    "oak_wood":         (0.55, 0.35, 0.18, 0.70),
    "concrete_grey":    (0.50, 0.50, 0.50, 0.95),
    "clear_glass":      (0.80, 0.88, 0.95, 0.05),
    "wood_dark":        (0.25, 0.15, 0.08, 0.60),
    "metal_brushed":    (0.72, 0.72, 0.72, 0.30),
}

def _mat_block(mat_name: str, preset_key: str) -> list:
    r, g, b, rough = MATERIAL_PRESETS.get(preset_key, (0.8, 0.8, 0.8, 0.8))
    return [
        f"# Material: {mat_name}",
        f"if '{mat_name}' not in bpy.data.materials:",
        f"    mat_{mat_name} = bpy.data.materials.new(name='{mat_name}')",
        f"    mat_{mat_name}.use_nodes = True",
        f"    bsdf_{mat_name} = mat_{mat_name}.node_tree.nodes['Principled BSDF']",
        f"    bsdf_{mat_name}.inputs['Base Color'].default_value = ({r}, {g}, {b}, 1.0)",
        f"    bsdf_{mat_name}.inputs['Roughness'].default_value = {rough}",
        "",
    ]

def _assign_block(obj_pattern: str, mat_name: str) -> list:
    return [
        f"for obj in bpy.data.objects:",
        f"    if obj.name.startswith('{obj_pattern}'):",
        f"        if obj.data and hasattr(obj.data, 'materials'):",
        f"            if len(obj.data.materials) == 0:",
        f"                obj.data.materials.append(bpy.data.materials['{mat_name}'])",
        f"            else:",
        f"                obj.data.materials[0] = bpy.data.materials['{mat_name}']",
        "",
    ]

def build(scene_graph, cfg) -> str:
    mat_cfg = cfg.get("materials", {})
    lines = ["# ── Materials ────────────────────────────────────────────"]

    mapping = {
        "Wall":     mat_cfg.get("walls",    "painted_white"),
        "Floor":    mat_cfg.get("floor",    "oak_wood"),
        "Ceiling":  mat_cfg.get("ceiling",  "plaster_white"),
    }

    defined = set()
    for prefix, preset in mapping.items():
        mat_name = preset.replace(" ", "_")
        if mat_name not in defined:
            lines += _mat_block(mat_name, preset)
            defined.add(mat_name)
        lines += _assign_block(prefix, mat_name)

    return "\n".join(lines)
