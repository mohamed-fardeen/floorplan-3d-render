"""
floor_builder.py
Generates bpy code to create floor slabs from room polygons.
"""

def build(scene_graph, cfg) -> str:
    thickness = cfg.get("building", {}).get("floor_thickness", 0.20)
    lines = ["# ── Floor Slabs & Base ──────────────────────────────────────────"]
    
    # 1. Generate room-specific floors (if any rooms exist)
    for room in scene_graph.rooms:
        verts = list(room.polygon)
        if not verts:
            continue
        label = (room.label or room.type or room.id).replace(" ", "_")
        lines += [
            f"# Room: {label}",
            f"verts_{room.id} = {[(*v, 0.0) for v in verts]}",
            f"faces_{room.id} = [list(range(len(verts_{room.id})))]",
            f"mesh_{room.id} = bpy.data.meshes.new('floor_{room.id}')",
            f"mesh_{room.id}.from_pydata(verts_{room.id}, [], faces_{room.id})",
            f"mesh_{room.id}.update()",
            f"obj_{room.id} = bpy.data.objects.new('Floor_{label}', mesh_{room.id})",
            f"bpy.context.collection.objects.link(obj_{room.id})",
            f"mod_{room.id} = obj_{room.id}.modifiers.new('Solidify', 'SOLIDIFY')",
            f"mod_{room.id}.thickness = {thickness}",
            f"mod_{room.id}.offset = -1.0",
            "",
        ]

    # 2. Generate a generic base plate under the whole model
    if scene_graph.walls:
        min_x = min(min(w.start[0], w.end[0]) for w in scene_graph.walls)
        max_x = max(max(w.start[0], w.end[0]) for w in scene_graph.walls)
        min_y = min(min(w.start[1], w.end[1]) for w in scene_graph.walls)
        max_y = max(max(w.start[1], w.end[1]) for w in scene_graph.walls)
        
        # Add some padding
        pad = 2.0
        min_x -= pad; max_x += pad; min_y -= pad; max_y += pad
        
        base_verts = [
            (min_x, min_y, -thickness),
            (max_x, min_y, -thickness),
            (max_x, max_y, -thickness),
            (min_x, max_y, -thickness)
        ]
        
        lines += [
            "# Generic Base Plate",
            f"base_verts = {base_verts}",
            f"base_faces = [[0, 1, 2, 3]]",
            f"base_mesh = bpy.data.meshes.new('BasePlate')",
            f"base_mesh.from_pydata(base_verts, [], base_faces)",
            f"base_mesh.update()",
            f"base_obj = bpy.data.objects.new('BasePlate', base_mesh)",
            f"bpy.context.collection.objects.link(base_obj)",
            f"base_mod = base_obj.modifiers.new('Solidify', 'SOLIDIFY')",
            f"base_mod.thickness = {thickness}",
            f"base_mod.offset = -1.0",
            ""
        ]

    return "\n".join(lines)
