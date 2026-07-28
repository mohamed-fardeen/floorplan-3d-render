MATERIAL_PRESETS = {
    "painted_white": (0.95, 0.95, 0.95, 0.85),
    "plaster_white": (0.93, 0.93, 0.90, 0.90),
    "oak_wood": (0.55, 0.35, 0.18, 0.70),
    "concrete_grey": (0.50, 0.50, 0.50, 0.95),
}

WALL_THEMES = {
    "warm_modern": (0.686, 0.578, 0.479),
    "painted_white": (0.888, 0.888, 0.888),
    "cool_modern": (0.485, 0.539, 0.584),
    "sage": (0.423, 0.485, 0.366),
    "sand": (0.694, 0.571, 0.386),
    "navy": (0.034, 0.068, 0.112),
    "clay": (0.479, 0.159, 0.085),
    "blush": (0.687, 0.456, 0.429),
    "charcoal": (0.068, 0.074, 0.080),
    "olive": (0.205, 0.223, 0.117),
    "sky": (0.397, 0.571, 0.687),
}


def _hex_rgb(value: str, fallback):
    if not isinstance(value, str) or len(value) != 7 or not value.startswith("#"):
        return fallback
    try:
        return tuple(int(value[i:i + 2], 16) / 255 for i in (1, 3, 5))
    except ValueError:
        return fallback


def _simple_material(name: str, color, roughness: float) -> list:
    return [
        f"mat = bpy.data.materials.get({name!r}) or bpy.data.materials.new(name={name!r})",
        f"mat.diffuse_color = ({color[0]}, {color[1]}, {color[2]}, 1.0)",
        "mat.use_nodes = True",
        "_tree = mat.node_tree",
        "_bsdf = next((n for n in _tree.nodes if n.type == 'BSDF_PRINCIPLED'), None)",
        "if _bsdf is None:",
        "    for n in list(_tree.nodes): _tree.nodes.remove(n)",
        "    _bsdf = _tree.nodes.new('ShaderNodeBsdfPrincipled')",
        "    _out = _tree.nodes.new('ShaderNodeOutputMaterial')",
        "    _tree.links.new(_bsdf.outputs['BSDF'], _out.inputs['Surface'])",
        "    _bsdf.location = (0, 0)",
        "    _out.location = (300, 0)",
        f"_bsdf.inputs['Base Color'].default_value = ({color[0]}, {color[1]}, {color[2]}, 1.0)",
        f"_bsdf.inputs['Roughness'].default_value = {roughness}",
        "",
    ]


def _floor_material(options: dict) -> list:
    design = options.get("design", "square_grid")
    primary = _hex_rgb(options.get("primary_color"), (0.91, 0.89, 0.85))
    secondary = _hex_rgb(options.get("secondary_color"), (0.55, 0.55, 0.55))
    grout = _hex_rgb(options.get("grout_color"), (0.66, 0.64, 0.61))
    tile_size = max(float(options.get("tile_size_m", 0.4)), 0.05)

    lines = _simple_material("FloorMaterial", primary, 0.55)
    if design == "solid":
        return lines

    lines += [
        "_tree = mat.node_tree",
        "for n in list(_tree.nodes): _tree.nodes.remove(n)",
        "_bsdf = _tree.nodes.new('ShaderNodeBsdfPrincipled')",
        "_out = _tree.nodes.new('ShaderNodeOutputMaterial')",
        "_tree.links.new(_bsdf.outputs['BSDF'], _out.inputs['Surface'])",
        "_bsdf.location = (0, 0)",
        "_out.location = (400, 0)",
        "nodes = mat.node_tree.nodes",
        "links = mat.node_tree.links",
        "texcoord = nodes.new('ShaderNodeTexCoord')",
        "mapping = nodes.new('ShaderNodeMapping')",
        f"mapping.inputs['Scale'].default_value = ({1 / tile_size}, {1 / tile_size}, {1 / tile_size})",
        "links.new(texcoord.outputs['Object'], mapping.inputs['Vector'])",
    ]

    if design in {"square_grid", "terracotta", "slate", "wood", "mosaic", "sandstone", "custom"}:
        lines += [
            "tiles = nodes.new('ShaderNodeTexBrick')",
            f"tiles.inputs['Color1'].default_value = ({primary[0]}, {primary[1]}, {primary[2]}, 1.0)",
            f"tiles.inputs['Color2'].default_value = ({secondary[0]}, {secondary[1]}, {secondary[2]}, 1.0)",
            f"tiles.inputs['Mortar'].default_value = ({grout[0]}, {grout[1]}, {grout[2]}, 1.0)",
            "tiles.inputs['Mortar Size'].default_value = 0.025",
            f"tiles.offset = {0.5 if design == 'wood' else 0.0}",
            "tiles.offset_frequency = 1",
            "tiles.squash = 1.0",
            "links.new(mapping.outputs['Vector'], tiles.inputs['Vector'])",
            "links.new(tiles.outputs['Color'], bsdf.inputs['Base Color'])",
            "bump = nodes.new('ShaderNodeBump')",
            "bump.inputs['Strength'].default_value = 0.12",
            "bump.inputs['Distance'].default_value = 0.02",
            "links.new(tiles.outputs['Fac'], bump.inputs['Height'])",
            "links.new(bump.outputs['Normal'], bsdf.inputs['Normal'])",
        ]
    elif design == "checker":
        lines += [
            "tiles = nodes.new('ShaderNodeTexChecker')",
            f"tiles.inputs['Color1'].default_value = ({primary[0]}, {primary[1]}, {primary[2]}, 1.0)",
            f"tiles.inputs['Color2'].default_value = ({secondary[0]}, {secondary[1]}, {secondary[2]}, 1.0)",
            "links.new(mapping.outputs['Vector'], tiles.inputs['Vector'])",
            "links.new(tiles.outputs['Color'], bsdf.inputs['Base Color'])",
        ]
    elif design in {"marble", "granite"}:
        lines += [
            "tiles = nodes.new('ShaderNodeTexNoise')",
            "tiles.inputs['Scale'].default_value = 3.0",
            "tiles.inputs['Detail'].default_value = 8.0",
            "tiles.inputs['Roughness'].default_value = 0.7",
            "ramp = nodes.new('ShaderNodeValToRGB')",
            f"ramp.color_ramp.elements[0].color = ({primary[0]}, {primary[1]}, {primary[2]}, 1.0)",
            f"ramp.color_ramp.elements[1].color = ({secondary[0]}, {secondary[1]}, {secondary[2]}, 1.0)",
            "links.new(mapping.outputs['Vector'], tiles.inputs['Vector'])",
            "links.new(tiles.outputs['Fac'], ramp.inputs['Fac'])",
            "links.new(ramp.outputs['Color'], bsdf.inputs['Base Color'])",
        ]
    return lines + [""]


def _assign_block(prefix: str, material_name: str, include_exact: str = "") -> list:
    condition = f"obj.name.startswith({prefix!r})"
    if include_exact:
        condition += f" or obj.name == {include_exact!r}"
    return [
        "for obj in bpy.data.objects:",
        f"    if {condition}:",
        "        if obj.data and hasattr(obj.data, 'materials'):",
        "            if len(obj.data.materials) == 0:",
        f"                obj.data.materials.append(bpy.data.materials[{material_name!r}])",
        "            else:",
        f"                obj.data.materials[0] = bpy.data.materials[{material_name!r}]",
        "",
    ]


def build(scene_graph, cfg) -> str:
    mat_cfg = cfg.get("materials", {})
    options = cfg.get("material_options", {})
    wall_options = options.get("walls", {})
    floor_options = options.get("floor", {})

    theme = wall_options.get("theme", "painted_white")
    wall_fallback = WALL_THEMES.get(theme, MATERIAL_PRESETS.get(mat_cfg.get("walls"), (0.95, 0.95, 0.95, 0.85))[:3])
    wall_color = _hex_rgb(wall_options.get("color"), wall_fallback)
    ceiling_preset = MATERIAL_PRESETS.get(mat_cfg.get("ceiling", "plaster_white"), MATERIAL_PRESETS["plaster_white"])

    lines = ["# ── Materials ────────────────────────────────────────────"]
    lines += _simple_material("WallMaterial", wall_color, 0.82)
    lines += _assign_block("Wall_", "WallMaterial")
    lines += _floor_material(floor_options)
    lines += _assign_block("Floor_", "FloorMaterial", "BasePlate")
    lines += _simple_material("CeilingMaterial", ceiling_preset[:3], ceiling_preset[3])
    lines += _assign_block("Ceiling_", "CeilingMaterial")
    return "\n".join(lines)
