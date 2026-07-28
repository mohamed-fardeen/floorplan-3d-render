"""
wall_builder.py
Generates bpy code to create wall meshes from Wall line segments.
Each wall is a thin box extruded to wall_height.
"""
import math

def build(scene_graph, cfg) -> str:
    building_cfg  = cfg.get("building", {})
    wall_height   = building_cfg.get("wall_height", 3.0)
    default_thick = building_cfg.get("wall_thickness_default", 0.20)
    min_thick     = building_cfg.get("wall_thickness_min", 0.15)

    lines = ["# ── Walls ───────────────────────────────────────────────"]
    for wall in scene_graph.walls:
        sx, sy = wall.start
        ex, ey = wall.end

        # Use parsed thickness, clamped to the configured minimum.
        # This is the final safety net after parser + normaliser pipeline.
        raw_thick = wall.thickness if wall.thickness else default_thick
        thick     = max(raw_thick, min_thick)

        # Mid-point and orientation
        cx = (sx + ex) / 2
        cy = (sy + ey) / 2
        dx, dy = ex - sx, ey - sy
        length = math.sqrt(dx*dx + dy*dy) if (dx*dx + dy*dy) > 0 else 0.001
        angle  = math.atan2(dy, dx)

        lines += [
            f"# Wall: {wall.id}  (length={length:.3f}m, thickness={thick:.3f}m)",
            f"bpy.ops.mesh.primitive_cube_add(",
            f"    size=1,",
            f"    location=({cx}, {cy}, {wall_height/2})",
            f")",
            f"wall_obj_{wall.id} = bpy.context.active_object",
            f"wall_obj_{wall.id}.name = 'Wall_{wall.id}'",
            f"wall_obj_{wall.id}.scale = ({length}, {thick}, {wall_height})",
            f"wall_obj_{wall.id}.rotation_euler[2] = {angle}",
            # Apply scale so dimensions are baked into mesh data
            f"bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)",
        ]

        lines.append("")

    return "\n".join(lines)
