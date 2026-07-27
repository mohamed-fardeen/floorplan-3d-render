"""
ceiling_builder.py
Mirrors the floor slab at wall_height to create ceilings.
"""

def build(scene_graph, cfg) -> str:
    if not cfg.get("building", {}).get("ceiling_enabled", True):
        return "# ── Ceiling disabled in config ──────────────────────────\n"

    wall_height = cfg.get("building", {}).get("wall_height", 3.0)
    thickness   = cfg.get("building", {}).get("floor_thickness", 0.20)

    lines = ["# ── Ceilings ─────────────────────────────────────────────"]
    for room in scene_graph.rooms:
        verts = list(room.polygon)
        if not verts:
            continue
        label = (room.label or room.type or room.id).replace(" ", "_")
        lines += [
            f"# Ceiling: {label}",
            f"ceil_verts_{room.id} = {[(*v, wall_height) for v in verts]}",
            f"ceil_faces_{room.id} = [list(range(len(ceil_verts_{room.id})))]",
            f"ceil_mesh_{room.id} = bpy.data.meshes.new('ceiling_{room.id}')",
            f"ceil_mesh_{room.id}.from_pydata(ceil_verts_{room.id}, [], ceil_faces_{room.id})",
            f"ceil_mesh_{room.id}.update()",
            f"ceil_obj_{room.id} = bpy.data.objects.new('Ceiling_{label}', ceil_mesh_{room.id})",
            f"bpy.context.collection.objects.link(ceil_obj_{room.id})",
            f"ceil_mod_{room.id} = ceil_obj_{room.id}.modifiers.new('Solidify', 'SOLIDIFY')",
            f"ceil_mod_{room.id}.thickness = {thickness}",
            f"ceil_mod_{room.id}.offset = 1.0",
            "",
        ]
    return "\n".join(lines)
