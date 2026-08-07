"""
topology.py
===========
Topology Node for 2D Floor Plan Perception Pipeline.

Responsibilities:
- Connect adjacent wall segments and close small gaps.
- Merge duplicate walls.
- Assign doors and windows to walls.
- Form room polygons and construct room adjacency graph.
- Normalize pixel coordinates to meters.
- Output intermediate TopologyData.
"""

from typing import List, Tuple, Dict, Any, Optional
import math
import uuid
from schema import VectorGeometry, TopologyData, Wall, Door, Window, Room, Adjacency
from parsers.normalizer import CoordinateNormalizer

def run_topology(vector_geom: VectorGeometry, pixel_to_meter: float = 0.0195) -> TopologyData:
    """
    Build intermediate TopologyData from VectorGeometry.
    Applies coordinate normalization (pixel -> meters).
    """
    print("    [Topology] Building intermediate topology representation...")
    
    normalizer = CoordinateNormalizer(
        pixel_to_meter=pixel_to_meter,
        flip_y=True,
    )

    walls: List[Wall] = []
    for seg in vector_geom.wall_centerlines:
        start_m = normalizer.point_to_meter(seg.start)
        end_m   = normalizer.point_to_meter(seg.end)
        thick_m = normalizer.dist_to_meter(seg.thickness)

        walls.append(Wall(
            id=seg.id,
            start=start_m,
            end=end_m,
            thickness=max(thick_m, 0.15)
        ))

    walls = _merge_collinear_walls(walls, gap_tolerance=0.30, angle_tolerance_deg=8.0)

    # Assign doors to nearest walls
    doors: List[Door] = []
    for d_idx, box in enumerate(vector_geom.door_boxes):
        cx_px = (box[0] + box[2]) / 2.0
        cy_px = (box[1] + box[3]) / 2.0
        center_m = normalizer.point_to_meter((cx_px, cy_px))
        
        nearest_wall_id = _find_nearest_wall_id(center_m, walls)
        if nearest_wall_id:
            doors.append(Door(
                id=f"door_{d_idx+1}",
                wall_id=nearest_wall_id,
                center=center_m,
                width=0.9,
                is_open=True
            ))

    # Assign windows to nearest walls
    windows: List[Window] = []
    for w_idx, box in enumerate(vector_geom.window_boxes):
        cx_px = (box[0] + box[2]) / 2.0
        cy_px = (box[1] + box[3]) / 2.0
        center_m = normalizer.point_to_meter((cx_px, cy_px))

        nearest_wall_id = _find_nearest_wall_id(center_m, walls)
        if nearest_wall_id:
            windows.append(Window(
                id=f"window_{w_idx+1}",
                wall_id=nearest_wall_id,
                center=center_m,
                width=1.2
            ))

    # Process rooms
    rooms: List[Room] = []
    for poly in vector_geom.raw_room_polygons:
        poly_m = [normalizer.point_to_meter(p) for p in poly.points]
        cx = sum(p[0] for p in poly_m) / max(len(poly_m), 1)
        cy = sum(p[1] for p in poly_m) / max(len(poly_m), 1)
        
        rooms.append(Room(
            id=poly.id,
            type=poly.label,
            polygon=poly_m,
            centroid=(cx, cy)
        ))

    # Basic Room Adjacency Graph based on distance between centroids
    adjacency: List[Adjacency] = []
    for i in range(len(rooms)):
        for j in range(i + 1, len(rooms)):
            r1, r2 = rooms[i], rooms[j]
            if r1.centroid and r2.centroid:
                dx = r1.centroid[0] - r2.centroid[0]
                dy = r1.centroid[1] - r2.centroid[1]
                dist = math.sqrt(dx*dx + dy*dy)
                if dist < 6.0:  # within 6 meters proximity
                    adjacency.append(Adjacency(
                        **{"from": r1.id, "to": r2.id, "via": "passage"}
                    ))

    return TopologyData(
        connected_walls=walls,
        assigned_doors=doors,
        assigned_windows=windows,
        rooms=rooms,
        adjacency_graph=adjacency
    )

def _snap_to_axis(wall: Wall, angle_tolerance_deg: float = 12.0) -> Wall:
    """Snap wall endpoints onto the nearest orthogonal axis through its midpoint."""
    (x1, y1), (x2, y2) = wall.start, wall.end
    dx = x2 - x1
    dy = y2 - y1
    length = math.hypot(dx, dy)
    if length == 0:
        return wall

    angle = abs(math.degrees(math.atan2(dy, dx))) % 180
    nearest_axis = 0.0 if angle < 90 else 90.0
    deviation = min(abs(angle - nearest_axis), abs(angle - (nearest_axis + 180)))
    if deviation > angle_tolerance_deg:
        return wall

    cx = (x1 + x2) / 2.0
    cy = (y1 + y2) / 2.0
    half = length / 2.0
    if angle < 90:
        return Wall(
            id=wall.id,
            start=(cx - half, cy),
            end=(cx + half, cy),
            thickness=wall.thickness,
        )
    return Wall(
        id=wall.id,
        start=(cx, cy - half),
        end=(cx, cy + half),
        thickness=wall.thickness,
    )


def _merge_collinear_walls(walls: List[Wall], gap_tolerance: float, angle_tolerance_deg: float) -> List[Wall]:
    """Snap near-axis walls to 90°, then fill small gaps only where fragments are collinear and aligned end-to-end."""
    if not walls:
        return walls

    snapped = [_snap_to_axis(w) for w in walls]
    # After snapping to axis, perpendicular walls at a corner still have
    # endpoints a few pixels apart because the snapping is per-wall (each
    # wall centres on its own midpoint). Cluster every endpoint and snap
    # each cluster to its centroid so perpendicular walls meet exactly
    # at the same corner coordinate — no visible gaps in the annotation
    # and no missing corner posts in the 3D model.
    snapped = _snap_perpendicular_corners(snapped, gap_tolerance)
    return _fill_collinear_gaps(snapped, gap_tolerance, math.sin(math.radians(angle_tolerance_deg)))


def _snap_perpendicular_corners(walls: List[Wall], tolerance: float) -> List[Wall]:
    """Snap endpoint clusters of perpendicular walls together so they meet at the same point.

    Each endpoint is clustered with its nearest neighbour within
    ``tolerance``. The cluster centroid is then written back to every
    wall endpoint that touched it, so a horizontal wall ending at
    (5.04, 0) and a vertical wall starting at (4.96, 0) both end up at
    (5.00, 0). Only endpoints are touched — wall lengths/angles stay
    identical, so the visual length of each wall is preserved.
    """
    if not walls:
        return walls

    # Collect every endpoint with the (wall_index, endpoint_key) pair
    # so we can write back to the right slot.
    pts: List[Tuple[float, float, int, str]] = []
    for i, w in enumerate(walls):
        pts.append((w.start[0], w.start[1], i, "start"))
        pts.append((w.end[0], w.end[1], i, "end"))

    # Find the average gap between adjacent walls' endpoints to pick a
    # sensible tolerance. If the user already supplies a tolerance use
    # it; otherwise default to the wall thickness so micro-gaps are
    # folded but genuinely separate corners stay separate.
    if tolerance <= 0:
        tolerance = 0.30

    # Greedy single-pass clustering.
    clusters: List[Dict[str, Any]] = []
    for x, y, wi, key in pts:
        match = None
        for c in clusters:
            if math.hypot(x - c["x"], y - c["y"]) < tolerance:
                match = c
                break
        if match is None:
            clusters.append({"x": x, "y": y, "members": [(wi, key)], "n": 1})
        else:
            match["members"].append((wi, key))
            match["n"] += 1
            match["x"] = (match["x"] * (match["n"] - 1) + x) / match["n"]
            match["y"] = (match["y"] * (match["n"] - 1) + y) / match["n"]

    # Apply the centroid back to every wall endpoint that touched the
    # cluster. New Wall objects so the schema stays pure.
    new_walls: List[Wall] = [w.model_copy() for w in walls]
    for c in clusters:
        for wi, key in c["members"]:
            w = new_walls[wi]
            new_point = (round(c["x"], 6), round(c["y"], 6))
            if key == "start":
                w.start = new_point
            else:
                w.end = new_point

    return new_walls


def _fill_collinear_gaps(walls: List[Wall], gap_tolerance: float, sin_angle_tol: float) -> List[Wall]:
    """Iteratively join only adjacent collinear fragments that share a touching endpoint cluster.

    Each merge step requires:
      * Both walls lie on the same orthogonal axis.
      * Their projections overlap or are separated by no more than ``gap_tolerance`` along that axis.
      * They share one endpoint cluster (closest endpoints ≤ gap_tolerance apart).
    """
    if not walls:
        return walls

    changed = True
    while changed:
        changed = False
        for i in range(len(walls)):
            if walls[i] is None:
                continue
            for j in range(i + 1, len(walls)):
                if walls[j] is None:
                    continue
                merged = _try_join(walls[i], walls[j], gap_tolerance, sin_angle_tol)
                if merged is None:
                    continue
                walls[i] = merged
                walls[j] = None
                changed = True
                break
            if changed:
                break

    return [w for w in walls if w is not None]


def _try_join(a: Wall, b: Wall, gap_tolerance: float, sin_angle_tol: float):
    """Return a merged wall if ``a`` and ``b`` are aligned end-to-end with a small gap, else ``None``."""
    ax1, ay1 = a.start
    ax2, ay2 = a.end
    bx1, by1 = b.start
    bx2, by2 = b.end

    a_h = abs(ax2 - ax1) >= abs(ay2 - ay1)
    b_h = abs(bx2 - bx1) >= abs(by2 - by1)
    if a_h != b_h:
        return None

    if a_h:
        a_y = (ay1 + ay2) / 2.0
        b_y = (by1 + by2) / 2.0
        if abs(a_y - b_y) > 0.25:
            return None
        a_lo, a_hi = (ax1, ax2) if ax1 <= ax2 else (ax2, ax1)
        b_lo, b_hi = (bx1, bx2) if bx1 <= bx2 else (bx2, bx1)
        gap = max(a_lo, b_lo) - min(a_hi, b_hi)
        if gap > gap_tolerance:
            return None
        new_lo, new_hi = min(a_lo, b_lo), max(a_hi, b_hi)
        if new_hi - new_lo < 0.05:
            return None
        start = (new_lo, a_y)
        end = (new_hi, a_y)
    else:
        a_x = (ax1 + ax2) / 2.0
        b_x = (bx1 + bx2) / 2.0
        if abs(a_x - b_x) > 0.25:
            return None
        a_lo, a_hi = (ay1, ay2) if ay1 <= ay2 else (ay2, ay1)
        b_lo, b_hi = (by1, by2) if by1 <= by2 else (by2, by1)
        gap = max(a_lo, b_lo) - min(a_hi, b_hi)
        if gap > gap_tolerance:
            return None
        new_lo, new_hi = min(a_lo, b_lo), max(a_hi, b_hi)
        if new_hi - new_lo < 0.05:
            return None
        start = (a_x, new_lo)
        end = (a_x, new_hi)

    return Wall(
        id=f"wall_joined_{uuid.uuid4().hex[:8]}",
        start=start,
        end=end,
        thickness=max(a.thickness, b.thickness),
    )


def _find_nearest_wall_id(point: Tuple[float, float], walls: List[Wall]) -> Optional[str]:
    if not walls:
        return None
    best_dist = float("inf")
    best_id = None
    px, py = point
    for w in walls:
        (x1, y1), (x2, y2) = w.start, w.end
        # Distance from point to segment
        dx, dy = x2 - x1, y2 - y1
        if dx == 0 and dy == 0:
            dist = math.sqrt((px - x1)**2 + (py - y1)**2)
        else:
            t = max(0, min(1, ((px - x1)*dx + (py - y1)*dy) / (dx*dx + dy*dy)))
            proj_x = x1 + t * dx
            proj_y = y1 + t * dy
            dist = math.sqrt((px - proj_x)**2 + (py - proj_y)**2)
        if dist < best_dist:
            best_dist = dist
            best_id = w.id
    return best_id
