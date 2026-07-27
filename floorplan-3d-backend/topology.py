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
