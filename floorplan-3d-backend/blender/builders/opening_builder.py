"""
opening_builder.py
Generates bpy code to cut door and window openings via Boolean Difference.
Each opening is a cutter box placed at the door/window center on its wall.
"""

def _wall_lookup(scene_graph) -> dict:
    return {w.id: w for w in scene_graph.walls}

def _opening_block(oid: str, kind: str, wall, center, width: float,
                   height: float, z_offset: float, cfg: dict) -> list:
    wall_height = cfg.get("building", {}).get("wall_height", 3.0)
    thick = (wall.thickness or cfg.get("building", {}).get("wall_thickness_default", 0.15)) * 2

    import math
    sx, sy = wall.start
    ex, ey = wall.end
    dx, dy = ex - sx, ey - sy
    angle = math.atan2(dy, dx)
    cx, cy = center

    return [
        f"# {kind}: {oid}",
        f"bpy.ops.mesh.primitive_cube_add(size=1, location=({cx}, {cy}, {z_offset + height/2}))",
        f"cut_{oid} = bpy.context.active_object",
        f"cut_{oid}.name = 'Cutter_{oid}'",
        f"cut_{oid}.scale = ({width}, {thick}, {height})",
        f"cut_{oid}.rotation_euler[2] = {angle}",
        f"cut_{oid}.display_type = 'WIRE'",
        # Apply boolean to the parent wall object
        f"wall_target_{oid} = bpy.data.objects.get('Wall_{wall.id}')",
        f"if wall_target_{oid}:",
        f"    bool_mod_{oid} = wall_target_{oid}.modifiers.new('Cut_{oid}', 'BOOLEAN')",
        f"    bool_mod_{oid}.operation = 'DIFFERENCE'",
        f"    bool_mod_{oid}.object = cut_{oid}",
        f"    cut_{oid}.hide_render = True",
        "",
    ]

def build(scene_graph, cfg) -> str:
    wall_height = cfg.get("building", {}).get("wall_height", 3.0)
    wall_map = _wall_lookup(scene_graph)
    lines = ["# ── Openings (Doors & Windows) ───────────────────────────"]

    for door in scene_graph.doors:
        wall = wall_map.get(door.wall_id)
        if not wall:
            lines.append(f"# [WARN] Door {door.id}: parent wall {door.wall_id} not found, skipping.")
            continue
        lines += _opening_block(
            oid=door.id, kind="Door", wall=wall,
            center=door.center, width=door.width,
            height=wall_height * 0.75, z_offset=0.0, cfg=cfg
        )

    for win in scene_graph.windows:
        wall = wall_map.get(win.wall_id)
        if not wall:
            lines.append(f"# [WARN] Window {win.id}: parent wall {win.wall_id} not found, skipping.")
            continue
        lines += _opening_block(
            oid=win.id, kind="Window", wall=wall,
            center=win.center, width=win.width,
            height=wall_height * 0.4, z_offset=wall_height * 0.3, cfg=cfg
        )

    return "\n".join(lines)
