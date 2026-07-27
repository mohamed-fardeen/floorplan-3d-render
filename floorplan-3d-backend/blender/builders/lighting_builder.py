"""
lighting_builder.py
Generates bpy code to add Sun lamp and optional HDRI world lighting.
All values driven from config.yaml.
"""

def build(scene_graph, cfg) -> str:
    lcfg = cfg.get("lighting", {})
    lines = ["# ── Lighting ─────────────────────────────────────────────"]

    # Sun lamp
    if lcfg.get("enable_sun", True):
        strength = lcfg.get("sun_strength", 3.0)
        angle_deg = lcfg.get("sun_angle_deg", 45)
        angle_rad = angle_deg * 3.14159 / 180.0
        lines += [
            "bpy.ops.object.light_add(type='SUN', location=(0, 0, 10))",
            "sun = bpy.context.active_object",
            "sun.name = 'Sun_Light'",
            f"sun.data.energy = {strength}",
            f"sun.rotation_euler = ({angle_rad}, 0, {angle_rad})",
            "",
        ]

    # HDRI world
    if lcfg.get("enable_hdri", False):
        hdri_path = lcfg.get("hdri_path", "")
        lines += [
            "world = bpy.context.scene.world",
            "world.use_nodes = True",
            "env_node = world.node_tree.nodes.new('ShaderNodeTexEnvironment')",
            f"env_node.image = bpy.data.images.load(r'{hdri_path}')",
            "bg_node = world.node_tree.nodes['Background']",
            "world.node_tree.links.new(env_node.outputs['Color'], bg_node.inputs['Color'])",
            "",
        ]

    # Interior area lights — one per room centroid
    if lcfg.get("enable_interior_lights", False):
        lines += ["# Interior lights"]
        for room in scene_graph.rooms:
            if room.centroid:
                cx, cy = room.centroid
                lines += [
                    f"bpy.ops.object.light_add(type='AREA', location=({cx}, {cy}, 2.8))",
                    f"bpy.context.active_object.name = 'Light_{room.id}'",
                    f"bpy.context.active_object.data.energy = 50",
                    "",
                ]

    return "\n".join(lines)
