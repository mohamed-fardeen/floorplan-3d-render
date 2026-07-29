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
        f"if {name!r} in bpy.data.materials:",
        f"    bpy.data.materials.remove(bpy.data.materials[{name!r}])",
        f"mat = bpy.data.materials.new(name={name!r})",
        f"mat.diffuse_color = ({color[0]}, {color[1]}, {color[2]}, 1.0)",
        "mat.use_nodes = True",
        "_tree = mat.node_tree",
        "for _n in list(_tree.nodes):",
        "    _tree.nodes.remove(_n)",
        "_bsdf = _tree.nodes.new('ShaderNodeBsdfPrincipled')",
        "_out = _tree.nodes.new('ShaderNodeOutputMaterial')",
        "_tree.links.new(_bsdf.outputs['BSDF'], _out.inputs['Surface'])",
        "_bsdf.location = (0, 0)",
        "_out.location = (300, 0)",
        f"_bsdf.inputs['Base Color'].default_value = ({color[0]}, {color[1]}, {color[2]}, 1.0)",
        f"_bsdf.inputs['Roughness'].default_value = {roughness}",
        "_bsdf.inputs['Metallic'].default_value = 0.0",
        "",
    ]


def _wall_ridge_wave(axis: str, scale: float, var_prefix: str) -> list:
    axis_idx = {"X": "X", "Y": "Y", "Z": "Z"}[axis.upper()]
    return [
        f"_{var_prefix}_sep = nodes.new('ShaderNodeSeparateXYZ')",
        f"links.new(_geo.outputs['Position'], _{var_prefix}_sep.inputs['Vector'])",
        f"_{var_prefix}_scale = nodes.new('ShaderNodeMath')",
        f"_{var_prefix}_scale.operation = 'MULTIPLY'",
        f"_{var_prefix}_scale.inputs[1].default_value = {scale}",
        f"links.new(_{var_prefix}_sep.outputs['{axis_idx}'], _{var_prefix}_scale.inputs[0])",
        f"_{var_prefix}_vec = nodes.new('ShaderNodeCombineXYZ')",
        f"_{var_prefix}_vec.inputs['X'].default_value = 0.0",
        f"_{var_prefix}_vec.inputs['Y'].default_value = 0.0",
        f"links.new(_{var_prefix}_scale.outputs['Value'], _{var_prefix}_vec.inputs['Z'])",
        f"_{var_prefix}_wave = nodes.new('ShaderNodeTexWave')",
        f"_{var_prefix}_wave.wave_type = 'BANDS'",
        f"_{var_prefix}_wave.bands_direction = 'Z'",
        f"_{var_prefix}_wave.inputs['Scale'].default_value = 1.0",
        f"_{var_prefix}_wave.inputs['Distortion'].default_value = 0.0",
        f"_{var_prefix}_wave.inputs['Detail'].default_value = 0.0",
        f"links.new(_{var_prefix}_vec.outputs['Vector'], _{var_prefix}_wave.inputs['Vector'])",
    ]


def _wall_material(color, pattern: str, roughness: float) -> list:
    """Build wall material: pattern first (bump), then apply chosen colour."""
    lines = [
        f"# Wall pattern: {pattern}",
        "if 'WallMaterial' in bpy.data.materials:",
        "    bpy.data.materials.remove(bpy.data.materials['WallMaterial'])",
        "mat = bpy.data.materials.new(name='WallMaterial')",
        "mat.use_nodes = True",
        "_tree = mat.node_tree",
        "for _n in list(_tree.nodes):",
        "    _tree.nodes.remove(_n)",
        "nodes = _tree.nodes",
        "links = _tree.links",
        "wall_bsdf = nodes.new('ShaderNodeBsdfPrincipled')",
        "wall_out = nodes.new('ShaderNodeOutputMaterial')",
        "links.new(wall_bsdf.outputs['BSDF'], wall_out.inputs['Surface'])",
        "wall_bsdf.location = (0, 0)",
        "wall_out.location = (500, 0)",
    ]

    if pattern in {"stacked_coils", "woven_rope"}:
        lines += [
            "# 1) Pattern ridges (world-space horizontal bands, same colour via lighting)",
            "_geo = nodes.new('ShaderNodeNewGeometry')",
        ]
        lines += _wall_ridge_wave("Z", 10.0, "hz")
        lines += [
            "_ridge_ramp = nodes.new('ShaderNodeValToRGB')",
            "_ridge_ramp.color_ramp.elements[0].position = 0.40",
            "_ridge_ramp.color_ramp.elements.new(0.60)",
            "_ridge_ramp.color_ramp.elements[1].position = 0.60",
        ]

        if pattern == "woven_rope":
            lines += _wall_ridge_wave("X", 4.0, "wx")
            lines += [
                "_ridge_mix = nodes.new('ShaderNodeMath')",
                "_ridge_mix.operation = 'MAXIMUM'",
                "links.new(_hz_wave.outputs['Fac'], _ridge_mix.inputs[0])",
                "links.new(_wx_wave.outputs['Fac'], _ridge_mix.inputs[1])",
                "links.new(_ridge_mix.outputs['Value'], _ridge_ramp.inputs['Fac'])",
            ]
        else:
            lines += ["links.new(_hz_wave.outputs['Fac'], _ridge_ramp.inputs['Fac'])"]

        lines += [
            "wall_bump = nodes.new('ShaderNodeBump')",
            "wall_bump.inputs['Strength'].default_value = 1.0",
            "wall_bump.inputs['Distance'].default_value = 0.045",
            "links.new(_ridge_ramp.outputs['Color'], wall_bump.inputs['Height'])",
            "links.new(wall_bump.outputs['Normal'], wall_bsdf.inputs['Normal'])",
        ]

    lines += [
        "# 2) Apply chosen wall colour",
        f"wall_bsdf.inputs['Base Color'].default_value = ({color[0]}, {color[1]}, {color[2]}, 1.0)",
        f"mat.diffuse_color = ({color[0]}, {color[1]}, {color[2]}, 1.0)",
        f"wall_bsdf.inputs['Roughness'].default_value = {roughness}",
        "wall_bsdf.inputs['Metallic'].default_value = 0.0",
        "",
        "# Show materials in viewport (pattern is invisible in Solid shading)",
        "for _win in bpy.context.window_manager.windows:",
        "    for _area in _win.screen.areas:",
        "        if _area.type == 'VIEW_3D':",
        "            for _space in _area.spaces:",
        "                if _space.type == 'VIEW_3D':",
        "                    _space.shading.type = 'MATERIAL'",
        "                    _space.shading.use_scene_lights = True",
        "",
    ]
    return lines


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
        "for _n in list(_tree.nodes):",
        "    _tree.nodes.remove(_n)",
        "floor_bsdf = _tree.nodes.new('ShaderNodeBsdfPrincipled')",
        "_out = _tree.nodes.new('ShaderNodeOutputMaterial')",
        "_tree.links.new(floor_bsdf.outputs['BSDF'], _out.inputs['Surface'])",
        "floor_bsdf.location = (0, 0)",
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
            "links.new(tiles.outputs['Color'], floor_bsdf.inputs['Base Color'])",
            "bump = nodes.new('ShaderNodeBump')",
            "bump.inputs['Strength'].default_value = 0.12",
            "bump.inputs['Distance'].default_value = 0.02",
            "links.new(tiles.outputs['Fac'], bump.inputs['Height'])",
            "links.new(bump.outputs['Normal'], floor_bsdf.inputs['Normal'])",
        ]
    elif design == "checker":
        lines += [
            "tiles = nodes.new('ShaderNodeTexChecker')",
            f"tiles.inputs['Color1'].default_value = ({primary[0]}, {primary[1]}, {primary[2]}, 1.0)",
            f"tiles.inputs['Color2'].default_value = ({secondary[0]}, {secondary[1]}, {secondary[2]}, 1.0)",
            "links.new(mapping.outputs['Vector'], tiles.inputs['Vector'])",
            "links.new(tiles.outputs['Color'], floor_bsdf.inputs['Base Color'])",
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
            "links.new(ramp.outputs['Color'], floor_bsdf.inputs['Base Color'])",
        ]
    return lines + [""]


def _assign_block(prefix: str, material_name: str, include_exact: str = "") -> list:
    condition = f"obj.name.startswith({prefix!r})"
    if include_exact:
        condition += f" or obj.name == {include_exact!r}"
    return [
        "for obj in bpy.data.objects:",
        f"    if {condition}:",
        "        if obj.type == 'MESH' and obj.data and hasattr(obj.data, 'materials'):",
        "            obj.data.materials.clear()",
        f"            obj.data.materials.append(bpy.data.materials[{material_name!r}])",
        "            obj.active_material_index = 0",
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
    wall_pattern = wall_options.get("pattern", "none")
    wall_roughness = 0.78 if wall_pattern in {"stacked_coils", "woven_rope"} else 0.82
    ceiling_preset = MATERIAL_PRESETS.get(mat_cfg.get("ceiling", "plaster_white"), MATERIAL_PRESETS["plaster_white"])

    lines = ["# ── Materials ────────────────────────────────────────────"]
    lines += _wall_material(wall_color, wall_pattern, wall_roughness)
    lines += _assign_block("Wall_", "WallMaterial")
    lines += _floor_material(floor_options)
    lines += _assign_block("Floor_", "FloorMaterial", "BasePlate")
    lines += _simple_material("CeilingMaterial", ceiling_preset[:3], ceiling_preset[3])
    lines += _assign_block("Ceiling_", "CeilingMaterial")
    return "\n".join(lines)
