"""
floor_builder.py
Generates bpy code for one floor slab per room.

Every room whose polygon has at least 3 vertices gets its own
``Floor_<room_id>`` mesh underneath it. There is NO big BasePlate
extending past the outer walls — the per-room slabs sit exactly inside
each room's polygon, so the model never shows a floor sticking out
beyond the facade.

Honoured by ``script_builder.build_script`` via the ``include_base`` flag:
when ``include_base=False`` the entire floor section is skipped, so the
model has no floor at all.
"""
from typing import List


def _triangulate(verts: List[tuple]) -> List[List[int]]:
    """Ear-clipping triangulation for a simple polygon.

    `verts` is a list of (x, y) tuples in CCW or CW order. Returns a list
    of 3-tuples of vertex indices forming triangles. Falls back to a
    fan from the first vertex when the polygon is degenerate (collinear
    points, fewer than 3 vertices, etc.).
    """
    n = len(verts)
    if n < 3:
        return []

    # Drop a trailing duplicate if the polygon is closed.
    if verts[0] == verts[-1]:
        verts = verts[:-1]
        n = len(verts)
    if n < 3:
        return []

    # Signed area — positive means CCW in screen space (y up).
    area = 0.0
    for i in range(n):
        x1, y1 = verts[i]
        x2, y2 = verts[(i + 1) % n]
        area += (x2 - x1) * (y2 + y1)
    ccw = area < 0  # In our coordinate system y is up; negative area = CCW visually.

    indices = list(range(n))
    triangles: List[List[int]] = []

    guard = 0
    while len(indices) > 2 and guard < n * 4:
        guard += 1
        ear_found = False
        for i in range(len(indices)):
            i_prev = indices[(i - 1) % len(indices)]
            i_curr = indices[i]
            i_next = indices[(i + 1) % len(indices)]

            a = verts[i_prev]
            b = verts[i_curr]
            c = verts[i_next]

            # Cross product of (b-a) × (c-b); sign tells us convexity.
            cross = (b[0] - a[0]) * (c[1] - b[1]) - (b[1] - a[1]) * (c[0] - b[0])
            if ccw:
                # CCW: keep convex-left turns (cross >= 0).
                if cross >= 0:
                    continue
            else:
                # CW: keep convex-right turns (cross <= 0).
                if cross <= 0:
                    continue

            # Make sure no other vertex lies inside this triangle.
            inside = False
            for j in indices:
                if j in (i_prev, i_curr, i_next):
                    continue
                p = verts[j]
                # Standard point-in-triangle test using barycentric coordinates.
                d1 = (p[0] - b[0]) * (a[1] - b[1]) - (a[0] - b[0]) * (p[1] - b[1])
                d2 = (p[0] - c[0]) * (b[1] - c[1]) - (b[0] - c[0]) * (p[1] - c[1])
                d3 = (p[0] - a[0]) * (c[1] - a[1]) - (c[0] - a[0]) * (p[1] - a[1])
                has_neg = (d1 < 0) or (d2 < 0) or (d3 < 0)
                has_pos = (d1 > 0) or (d2 > 0) or (d3 > 0)
                if not (has_neg and has_pos):
                    inside = True
                    break

            if inside:
                continue

            triangles.append([i_prev, i_curr, i_next])
            indices.pop(i)
            ear_found = True
            break

        if not ear_found:
            # Polygon is non-simple; fall back to a fan from index 0.
            triangles = [[indices[0], indices[k], indices[k + 1]] for k in range(1, len(indices) - 1)]
            break

    return triangles


def build(scene_graph, cfg) -> str:
    thickness = cfg.get("building", {}).get("floor_thickness", 0.20)

    lines = ["# ── Floors (per-room) ─────────────────────────────────────"]

    if not scene_graph.rooms:
        return "\n".join(lines)

    emitted = 0
    for room in scene_graph.rooms:
        poly = list(room.polygon)
        if len(poly) < 3:
            continue

        # Drop the closing duplicate if the parser appended one.
        if poly[0] == poly[-1]:
            poly = poly[:-1]
        if len(poly) < 3:
            continue

        # Triangulate the polygon; fall back to a fan if the polygon is
        # non-simple (self-intersecting after enrichment).
        triangles = _triangulate(poly)
        if not triangles:
            n = len(poly)
            triangles = [[0, k, k + 1] for k in range(1, n - 1)]

        verts3d = [(x, y, -thickness) for (x, y) in poly]
        faces = triangles

        label = (room.label or room.type or room.id).replace(" ", "_")
        rid = room.id or label
        obj_name = f"Floor_{rid}"

        lines += [
            f"# Floor: {label}",
            f"floor_verts_{rid} = {verts3d}",
            f"floor_faces_{rid} = {faces}",
            f"floor_mesh_{rid} = bpy.data.meshes.new({obj_name!r})",
            f"floor_mesh_{rid}.from_pydata(floor_verts_{rid}, [], floor_faces_{rid})",
            f"floor_mesh_{rid}.update()",
            f"floor_obj_{rid} = bpy.data.objects.new({obj_name!r}, floor_mesh_{rid})",
            f"bpy.context.collection.objects.link(floor_obj_{rid})",
            f"floor_mod_{rid} = floor_obj_{rid}.modifiers.new('Solidify', 'SOLIDIFY')",
            f"floor_mod_{rid}.thickness = {thickness}",
            f"floor_mod_{rid}.offset = -1.0",
            "",
        ]
        emitted += 1

    if emitted == 0:
        lines.append("# (no rooms with valid polygons — model has no floor)")
        lines.append("")

    return "\n".join(lines)
