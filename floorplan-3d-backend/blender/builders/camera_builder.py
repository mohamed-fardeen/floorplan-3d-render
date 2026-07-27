"""
camera_builder.py
Generates bpy code to create three cameras:
  1. Top-down orthographic (plan view)
  2. Perspective (exterior corner)
  3. Walkthrough camera at chest height inside first room
"""

def build(scene_graph, cfg) -> str:
    lines = ["# ── Cameras ──────────────────────────────────────────────"]

    # Compute bounding box of all walls for camera placement
    all_x, all_y = [], []
    for w in scene_graph.walls:
        all_x += [w.start[0], w.end[0]]
        all_y += [w.start[1], w.end[1]]

    if not all_x:
        # Fallback for empty scenes
        cx_mid, cy_mid, span = 5.0, 5.0, 10.0
    else:
        cx_mid = (min(all_x) + max(all_x)) / 2
        cy_mid = (min(all_y) + max(all_y)) / 2
        span   = max(max(all_x) - min(all_x), max(all_y) - min(all_y), 1.0)

    # 1. Top-down orthographic
    lines += [
        "# Camera 1: Top-down (plan view)",
        f"bpy.ops.object.camera_add(location=({cx_mid}, {cy_mid}, {span + 5}))",
        "cam_top = bpy.context.active_object",
        "cam_top.name = 'Camera_TopDown'",
        f"cam_top.rotation_euler = (0, 0, 0)",
        "cam_top.data.type = 'ORTHO'",
        f"cam_top.data.ortho_scale = {span * 1.2}",
        "",
        # 2. Perspective corner
        "# Camera 2: Perspective (exterior corner view)",
        f"bpy.ops.object.camera_add(location=({max(all_x) + span*0.6 if all_x else 10}, "
        f"{min(all_y) - span*0.6 if all_y else -10}, {span * 0.5}))",
        "cam_persp = bpy.context.active_object",
        "cam_persp.name = 'Camera_Perspective'",
        "cam_persp.data.type = 'PERSP'",
        "cam_persp.data.lens = 35",
        "import mathutils",
        f"cam_persp.rotation_euler = mathutils.Euler((1.047, 0, 0.785), 'XYZ')",
        "",
    ]

    # 3. Walkthrough camera inside first room
    if scene_graph.rooms and scene_graph.rooms[0].centroid:
        rcx, rcy = scene_graph.rooms[0].centroid
        lines += [
            "# Camera 3: Walkthrough (first-person, inside first room)",
            f"bpy.ops.object.camera_add(location=({rcx}, {rcy}, 1.6))",
            "cam_walk = bpy.context.active_object",
            "cam_walk.name = 'Camera_Walkthrough'",
            "cam_walk.data.type = 'PERSP'",
            "cam_walk.data.lens = 24",
            "",
        ]

    # Set top-down as active render camera
    lines += [
        "bpy.context.scene.camera = bpy.data.objects['Camera_TopDown']",
        "",
    ]
    return "\n".join(lines)
