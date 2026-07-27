from typing import Tuple, List
import copy
from shapely.geometry import Polygon, LineString, Point
from shapely.ops import nearest_points

from schema import SceneGraph

def validate_and_repair_scene(scene_graph: SceneGraph, tolerance: float = 0.5) -> Tuple[SceneGraph, List[str]]:
    """
    Validates and repairs the scene graph geometry using Shapely.
    Returns the corrected SceneGraph and a list of validation report messages.
    """
    report = []
    # Work on a copy so we can safely mutate
    corrected_sg = copy.deepcopy(scene_graph)
    
    # 1. Validate and compute metrics for Walls
    for wall in corrected_sg.walls:
        p1 = Point(wall.start)
        p2 = Point(wall.end)
        line = LineString([p1, p2])
        wall.length = line.length
        if wall.length < 0.01:
            report.append(f"[WARNING] Wall {wall.id} is extremely short ({wall.length:.3f}m).")
    
    # 2. Validate and compute metrics for Rooms
    for i, room in enumerate(corrected_sg.rooms):
        if len(room.polygon) < 3:
            report.append(f"[ERROR] Room {room.id} has fewer than 3 points, invalid polygon.")
            continue
            
        poly = Polygon(room.polygon)
        
        if not poly.is_valid:
            # Attempt repair via buffer(0)
            poly = poly.buffer(0)
            if poly.is_valid:
                report.append(f"[FIXED] Room {room.id} polygon was invalid (self-intersecting) and was repaired.")
                # Update coords (handling MultiPolygon is complex, assume simple Polygon for now)
                if poly.geom_type == 'Polygon':
                    room.polygon = list(poly.exterior.coords)
            else:
                report.append(f"[ERROR] Room {room.id} polygon is invalid and could not be repaired.")
                continue
                
        # Compute area and centroid
        room.area = poly.area
        room.centroid = (poly.centroid.x, poly.centroid.y)
        
    # 3. Validate and snap Doors
    for door in corrected_sg.doors:
        door_pt = Point(door.center)
        # Find the parent wall
        parent_wall = next((w for w in corrected_sg.walls if w.id == door.wall_id), None)
        if not parent_wall:
            report.append(f"[ERROR] Door {door.id} references missing wall {door.wall_id}.")
            continue
            
        wall_line = LineString([parent_wall.start, parent_wall.end])
        distance = door_pt.distance(wall_line)
        
        if distance > 1e-5:
            if distance <= tolerance:
                # Snap it
                closest_pt_on_wall, _ = nearest_points(wall_line, door_pt)
                door.center = (closest_pt_on_wall.x, closest_pt_on_wall.y)
                report.append(f"[FIXED] Door {door.id} was snapped to wall {parent_wall.id} (moved {distance:.3f}m).")
            else:
                report.append(f"[ERROR] Door {door.id} is too far ({distance:.3f}m) from its wall {parent_wall.id} to safely snap.")

    # 4. Validate and snap Windows
    for window in corrected_sg.windows:
        win_pt = Point(window.center)
        parent_wall = next((w for w in corrected_sg.walls if w.id == window.wall_id), None)
        if not parent_wall:
            report.append(f"[ERROR] Window {window.id} references missing wall {window.wall_id}.")
            continue
            
        wall_line = LineString([parent_wall.start, parent_wall.end])
        distance = win_pt.distance(wall_line)
        
        if distance > 1e-5:
            if distance <= tolerance:
                closest_pt_on_wall, _ = nearest_points(wall_line, win_pt)
                window.center = (closest_pt_on_wall.x, closest_pt_on_wall.y)
                report.append(f"[FIXED] Window {window.id} was snapped to wall {parent_wall.id} (moved {distance:.3f}m).")
            else:
                report.append(f"[ERROR] Window {window.id} is too far ({distance:.3f}m) from its wall {parent_wall.id} to safely snap.")
                
    return corrected_sg, report
