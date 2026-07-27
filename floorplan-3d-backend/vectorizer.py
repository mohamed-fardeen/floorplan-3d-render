"""
vectorizer.py
=============
Deterministic Vectorizer Node for 2D Floor Plan Perception Pipeline.

Responsibilities:
- Convert raw AI segmentation masks into vector geometry.
- Extract wall centerlines, endpoints, junctions, room polygons, door/window bounding boxes.
- Purely deterministic geometry/OpenCV logic. NO AI, NO LLMs.
"""

from typing import List, Tuple, Dict, Any
import math
import uuid
import numpy as np

from schema import PerceptionResult, VectorGeometry, VectorSegment, VectorPolygon

_MIN_WALL_AREA = 150
_MIN_ROOM_AREA = 500
_MIN_OPENING_AREA = 20

def run_vectorization(perception_res: PerceptionResult, pixel_to_meter: float = 0.0195) -> VectorGeometry:
    """
    Extract vector geometry primitives from PerceptionResult masks.
    """
    print("    [Vectorizer] Extracting deterministic vector geometry from masks...")
    
    wall_mask = perception_res.wall_masks
    room_mask = perception_res.room_masks
    door_mask = perception_res.door_masks
    window_mask = perception_res.window_masks

    wall_segments: List[VectorSegment] = []
    endpoints: List[Tuple[float, float]] = []
    junctions: List[Tuple[float, float]] = []
    raw_room_polygons: List[VectorPolygon] = []
    door_boxes: List[Tuple[float, float, float, float]] = []
    window_boxes: List[Tuple[float, float, float, float]] = []

    # If fallback scene graph is present (e.g. from mock parser)
    if perception_res.raw_predictions.get("fallback_scene_graph"):
        sg = perception_res.raw_predictions["fallback_scene_graph"]
        for w in sg.walls:
            wall_segments.append(VectorSegment(id=w.id, start=w.start, end=w.end, thickness=w.thickness))
            endpoints.extend([w.start, w.end])
        for r in sg.rooms:
            raw_room_polygons.append(VectorPolygon(id=r.id, points=r.polygon, label=r.type))
        for d in sg.doors:
            c = d.center
            door_boxes.append((c[0]-0.45, c[1]-0.45, c[0]+0.45, c[1]+0.45))
        for win in sg.windows:
            c = win.center
            window_boxes.append((c[0]-0.6, c[1]-0.6, c[0]+0.6, c[1]+0.6))
            
        return VectorGeometry(
            wall_centerlines=wall_segments,
            endpoints=endpoints,
            junctions=junctions,
            raw_room_polygons=raw_room_polygons,
            door_boxes=door_boxes,
            window_boxes=window_boxes,
        )

    import cv2

    # --- 1. Extract Wall Centerlines & Endpoints ---
    if wall_mask is not None and np.any(wall_mask):
        kernel_close = cv2.getStructuringElement(cv2.MORPH_RECT, (7, 7))
        kernel_open  = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
        clean_wall   = cv2.morphologyEx(wall_mask, cv2.MORPH_OPEN,  kernel_open)
        clean_wall   = cv2.morphologyEx(clean_wall, cv2.MORPH_CLOSE, kernel_close)

        contours, _ = cv2.findContours(clean_wall, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        for cnt in contours:
            area = cv2.contourArea(cnt)
            if area < _MIN_WALL_AREA:
                continue

            rect = cv2.minAreaRect(cnt)
            (cx, cy), (rw, rh), angle = rect

            if rw >= rh:
                half_len = rw / 2.0
                thickness_px = rh
                theta = math.radians(angle)
            else:
                half_len = rh / 2.0
                thickness_px = rw
                theta = math.radians(angle + 90.0)

            dx = math.cos(theta) * half_len
            dy = math.sin(theta) * half_len

            # Invert Y to match coordinate system if needed
            start = (float(cx - dx), float(cy - dy))
            end   = (float(cx + dx), float(cy + dy))

            wall_id = f"wall_{uuid.uuid4().hex[:8]}"
            seg = VectorSegment(
                id=wall_id,
                start=start,
                end=end,
                thickness=max(float(thickness_px), 10.0)
            )
            wall_segments.append(seg)
            endpoints.extend([start, end])

    # --- 2. Extract Room Polygons ---
    if room_mask is not None and np.any(room_mask):
        contours, _ = cv2.findContours(room_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        for cnt in contours:
            if cv2.contourArea(cnt) < _MIN_ROOM_AREA:
                continue
            approx = cv2.approxPolyDP(cnt, epsilon=5.0, closed=True)
            pts = [(float(p[0][0]), float(p[0][1])) for p in approx]
            if len(pts) >= 3:
                raw_room_polygons.append(VectorPolygon(
                    id=f"room_{uuid.uuid4().hex[:8]}",
                    points=pts,
                    label="room"
                ))

    # --- 3. Extract Doors & Windows Bounding Boxes ---
    def _extract_boxes(mask: np.ndarray) -> List[Tuple[float, float, float, float]]:
        boxes = []
        if mask is not None and np.any(mask):
            contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            for cnt in contours:
                if cv2.contourArea(cnt) < _MIN_OPENING_AREA:
                    continue
                x, y, w, h = cv2.boundingRect(cnt)
                boxes.append((float(x), float(y), float(x + w), float(y + h)))
        return boxes

    door_boxes = _extract_boxes(door_mask)
    window_boxes = _extract_boxes(window_mask)

    return VectorGeometry(
        wall_centerlines=wall_segments,
        endpoints=endpoints,
        junctions=junctions,
        raw_room_polygons=raw_room_polygons,
        door_boxes=door_boxes,
        window_boxes=window_boxes,
    )
