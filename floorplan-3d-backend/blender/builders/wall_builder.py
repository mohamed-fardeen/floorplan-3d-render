"""
wall_builder.py
Generates bpy code to create wall meshes from Wall line segments.

Each wall is a thin box extruded to wall_height. The geometry is built
in three passes so the corners read as solid, seamless joining of two
walls:

  Pass 1 — walls
    Each wall is extended by half its thickness at BOTH ends along its
    own direction. The two walls at a corner therefore overlap by half
    the thickness on each face, which hides the seam between the wall
    and the corner post and makes the visible outer face look like a
    continuous box. Wall edges stay sharp — they read as a clean,
    fabricated timber/concrete meet.

  Pass 2 — corner posts
    At every junction (a position shared by ≥2 walls, OR a vertex of
    the room polygon that touches a wall endpoint), we emit a vertical
    ``post`` cube sized to the wall thickness. The post physically
    fills the inside of the corner so there's no hollow where the two
    walls overlap. The post cross-section matches the wall thickness
    exactly (no extra protrusion) and uses the same wall material, so
    the corner reads as a solid meeting of two walls rather than a
    visible column.

  Pass 3 — bevel pass on posts (3D print mode only)
    When the active wall pattern is a 3D-printed pattern (stacked_coils
    or woven_rope), only the POSTS receive a bevel modifier — NOT the
    walls. This is the visual signature of a 3D-printed concrete wall:
    the wall surfaces stay sharp and orthogonal, while the column at
    the corner reads as a smooth, rounded curve because the nozzle
    naturally lays a continuous bead around the outside corner. The
    bevel width is ≈ 0.5 × wall thickness and the segments are dense
    so the corner reads as a smooth, rounded curve.

``wall.length`` populated by the OCR enrichment pass is trusted over
the geometric start→end distance — that's how the 3D model gets its
true scale from the architect's dimension labels on the floor plan.
"""
import math


_3D_PRINT_PATTERNS = {"stacked_coils", "woven_rope"}


def _wall_thickness(wall, default_thick: float, min_thick: float) -> float:
    """Pick the wall's effective thickness (clamped to min_thick)."""
    raw = wall.thickness if wall.thickness else default_thick
    return max(raw, min_thick)


def _is_3d_print_mode(cfg: dict) -> bool:
    """Return True when the active wall pattern is a 3D-printed pattern."""
    wall_options = cfg.get("material_options", {}).get("walls", {}) or {}
    pattern = wall_options.get("pattern", "none")
    return pattern in _3D_PRINT_PATTERNS


def build(scene_graph, cfg) -> str:
    building_cfg  = cfg.get("building", {})
    wall_height   = building_cfg.get("wall_height", 3.0)
    default_thick = building_cfg.get("wall_thickness_default", 0.20)
    min_thick     = building_cfg.get("wall_thickness_min", 0.15)
    curve_corners = _is_3d_print_mode(cfg)

    # Post cross-section = wall thickness exactly. The post is therefore
    # *flush* with the wall (no extra protrusion) so the corner reads
    # as a solid meeting of two walls. The post still uses the same wall
    # material and pattern, so it blends in — the only reason for the post
    # is to fill the small gap left between two walls that don't quite
    # meet at the same pixel.
    # Two endpoints within this distance are the same junction. Bumped
    # to 30 cm (was 20) so noisy endpoint clusters around the corners
    # still snap together. Room polygon vertices are also folded in
    # below as guaranteed corners.
    snap_dist     = max(default_thick * 1.5, 0.30)

    # Bevel segments used in 3D print mode for corner posts.
    bevel_segments = 8

    lines = ["# ── Walls ───────────────────────────────────────────────"]

    # ── Pass 1: walls ──────────────────────────────────────────────────────
    # Each wall is extended by half its thickness at each end so the
    # two walls at a corner overlap and the seam between wall and post
    # is hidden behind solid geometry. The wall is rotated by ``angle``
    # so we can extend it along its own direction without rotating the
    # head/tail thicknesses.
    for wall in scene_graph.walls:
        sx, sy = wall.start
        ex, ey = wall.end

        thick = _wall_thickness(wall, default_thick, min_thick)

        dx = ex - sx
        dy = ey - sy
        geo_len = math.sqrt(dx * dx + dy * dy)

        # OCR-enriched length wins. When the OCR label disagrees with the
        # vectorized geometry we rescale the end-coordinate so the rendered
        # wall matches the dimension on the floor plan. Direction is
        # preserved — only the magnitude changes.
        if (
            wall.length is not None
            and wall.length > 0
            and geo_len > 0
            and abs(geo_len - wall.length) > 0.01
        ):
            scale = wall.length / geo_len
            ex = sx + dx * scale
            ey = sy + dy * scale
            dx = ex - sx
            dy = ey - sy
            length = wall.length
        elif geo_len > 0:
            length = geo_len
        else:
            length = 0.001

        # Extend the wall by half its thickness at each end so the
        # two walls at a corner overlap by the full thickness. The
        # extra overlap hides the wall ↔ post seam and makes the
        # outside surface look continuous.
        extended_length = length + thick

        cx = (sx + ex) / 2
        cy = (sy + ey) / 2
        angle = math.atan2(dy, dx)

        dim_note = f" ocr={wall.length:.3f}m" if wall.length else ""

        lines += [
            f"# Wall: {wall.id}  (length={length:.3f}m{dim_note})",
            f"bpy.ops.mesh.primitive_cube_add(",
            f"    size=1,",
            f"    location=({cx}, {cy}, {wall_height/2})",
            f")",
            f"wall_obj_{wall.id} = bpy.context.active_object",
            f"wall_obj_{wall.id}.name = 'Wall_{wall.id}'",
            f"wall_obj_{wall.id}.scale = ({extended_length}, {thick}, {wall_height})",
            f"wall_obj_{wall.id}.rotation_euler[2] = {angle}",
            f"bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)",
            "",
        ]

    # ── Pass 2: corner posts ──────────────────────────────────────────────
    # Build a list of corner-point candidates from two sources:
    #   1. Every wall start/end endpoint (these may be noisy).
    #   2. Every vertex of every room polygon (these are guaranteed
    #      corners — room polygons are closed and already snapped).
    # We then cluster all candidates together with a generous snap so
    # any endpoint within snap_dist of a room vertex gets folded into
    # the same corner. The post is emitted at the cluster centroid,
    # so even noisy walls get a corner where the room polygon says
    # one should exist.
    candidates: list[tuple] = []
    for wall in scene_graph.walls:
        for ep in (wall.start, wall.end):
            thick = _wall_thickness(wall, default_thick, min_thick)
            candidates.append((ep[0], ep[1], "wall", wall.id, thick))
    for room in scene_graph.rooms:
        for vx, vy in room.polygon:
            candidates.append((float(vx), float(vy), "room", room.id, default_thick))

    # Greedy single-pass clustering. Each cluster stores the running
    # centroid (x, y) and the unique wall/room IDs touching it.
    clusters: list[dict] = []
    for x, y, src, src_id, thick in candidates:
        match = None
        for c in clusters:
            if math.hypot(x - c["x"], y - c["y"]) < snap_dist:
                match = c
                break
        if match is None:
            clusters.append({
                "x": x,
                "y": y,
                "walls": {src_id} if src == "wall" else set(),
                "rooms": {src_id} if src == "room" else set(),
                "n": 1,
                "thick_sum": thick,
                "thick_n": 1,
            })
        else:
            if src == "wall":
                match["walls"].add(src_id)
            else:
                match["rooms"].add(src_id)
            match["n"] += 1
            match["thick_sum"] = match.get("thick_sum", default_thick) + thick
            match["thick_n"] = match.get("thick_n", 1) + 1
            # Re-centre on the fly so clustered points converge.
            match["x"] = (match["x"] * (match["n"] - 1) + x) / match["n"]
            match["y"] = (match["y"] * (match["n"] - 1) + y) / match["n"]

    # Emit a post at every cluster that touches ≥2 walls OR touches a
    # room polygon vertex AND at least one wall endpoint. (A cluster
    # with only room vertices and no walls is the building outline
    # corner with no actual wall reaching it — skip those.)
    post_idx = 0
    for c in clusters:
        if len(c["walls"]) < 2:
            continue
        post_idx += 1

        # Use the average thickness of the walls meeting at this junction
        # so the post is exactly flush with the walls on both sides.
        avg_thick = c.get("thick_sum", default_thick) / max(c.get("thick_n", 1), 1)
        post_scale = max(avg_thick, min_thick)

        bevel_block = []
        if curve_corners:
            # In bevel mode use a narrow bevel (20% of thickness) just to
            # soften the corner edge — do NOT grow the post, it stays flush.
            bevel_w = max(post_scale * 0.20, 0.02)
            bevel_block = [
                f"_bev_p{post_idx} = post_obj_p{post_idx}.modifiers.new('Bevel_3DPrint', 'BEVEL')",
                f"_bev_p{post_idx}.width = {bevel_w}",
                f"_bev_p{post_idx}.segments = {bevel_segments}",
                f"_bev_p{post_idx}.limit_method = 'ANGLE'",
                f"_bev_p{post_idx}.angle_limit = 1.309  # 75 degrees — only perpendicular edges",
                "",
            ]

        lines += [
            f"# Corner post at ({c['x']:.3f}, {c['y']:.3f}) — {len(c['walls'])} wall(s), {len(c['rooms'])} room vertex",
            f"bpy.ops.mesh.primitive_cube_add(",
            f"    size=1,",
            f"    location=({c['x']:.4f}, {c['y']:.4f}, {wall_height/2})",
            f")",
            f"post_obj_p{post_idx} = bpy.context.active_object",
            f"post_obj_p{post_idx}.name = 'WallPost_p{post_idx}'",
            f"post_obj_p{post_idx}.scale = ({post_scale}, {post_scale}, {wall_height + 0.05})",
            f"bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)",
            "",
            *bevel_block,
        ]

    if post_idx:
        lines.insert(1, f"# {post_idx} corner posts at wall junctions (flush with wall)")

    if curve_corners:
        lines.insert(1, f"# 3D PRINT MODE: corner posts receive a bevel modifier so the "
                       f"outside corners are smooth-curved (≈ {bevel_width:.3f} m radius, "
                       f"{bevel_segments} segments). Walls stay sharp.")

    return "\n".join(lines)
