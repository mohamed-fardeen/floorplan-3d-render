"""
parsers/visualization.py
========================
Debug visualization: overlays the parsed SceneGraph on the original floor plan
image so you can visually inspect what the parser extracted.

Usage
-----
    from parsers.visualization import visualize_scene_graph
    out_path = visualize_scene_graph(scene_graph, image_path, output_dir="output/debug")
"""

from __future__ import annotations

import os
import math
from typing import List, Tuple, Optional

import numpy as np

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from schema import SceneGraph


# Colour palette (BGR for OpenCV)
_WALL_COLOUR    = (50,  50,  220)   # red
_ROOM_COLOUR    = (50, 200,  50)    # green (fill, semi-transparent)
_DOOR_COLOUR    = (200, 100,  0)    # blue
_WINDOW_COLOUR  = (0,  200, 200)    # yellow
_LABEL_COLOUR   = (255, 255, 255)   # white
_CONF_COLOUR    = (180, 255, 180)   # light green


def _meter_to_pixel(
    coord: Tuple[float, float],
    scale_m_to_px: float,
    img_h: int,
) -> Tuple[int, int]:
    """Convert (x, y) in metres back to image pixel coordinates."""
    px = int(coord[0] * scale_m_to_px)
    py = img_h - int(coord[1] * scale_m_to_px)  # flip y back to image coords
    return (px, py)


def visualize_scene_graph(
    scene_graph: SceneGraph,
    image_path: str,
    output_dir: str = "output/debug",
    show_labels: bool = True,
    show_confidence: bool = True,
    filename_suffix: str = "_annotated",
) -> str:
    """
    Overlay *scene_graph* predictions on *image_path* and save the result.

    Returns the path to the saved annotated image.
    """
    try:
        import cv2
    except ImportError:
        raise ImportError("opencv-python is required for visualization. "
                          "Install with: pip install opencv-python")

    try:
        from PIL import Image as PILImage
    except ImportError:
        raise ImportError("Pillow is required. Install with: pip install Pillow")

    os.makedirs(output_dir, exist_ok=True)

    # Load the original image
    img = cv2.imread(image_path)
    if img is None:
        raise FileNotFoundError(f"Cannot load image: {image_path}")

    img_h, img_w = img.shape[:2]

    # Scale: scene_graph is in metres; we need to map back to pixel space.
    # Use the stored scale from metadata.
    scale = scene_graph.metadata.scale_pixel_to_meter  # m/px
    if scale <= 0:
        scale = 0.01
    m_to_px = 1.0 / scale  # px/m

    def to_px(coord: Tuple[float, float]) -> Tuple[int, int]:
        px = int(coord[0] * m_to_px)
        py = img_h - int(coord[1] * m_to_px)  # flip y
        return (max(0, min(img_w - 1, px)), max(0, min(img_h - 1, py)))

    # ---- Draw rooms (filled semi-transparent) ----
    overlay = img.copy()
    for room in scene_graph.rooms:
        if len(room.polygon) < 3:
            continue
        pts = np.array([to_px(p) for p in room.polygon], dtype=np.int32)
        cv2.fillPoly(overlay, [pts], _ROOM_COLOUR)

    # Blend room fills
    cv2.addWeighted(overlay, 0.3, img, 0.7, 0, img)

    # ---- Draw room borders and labels ----
    for room in scene_graph.rooms:
        if len(room.polygon) < 3:
            continue
        pts = np.array([to_px(p) for p in room.polygon], dtype=np.int32)
        cv2.polylines(img, [pts], True, _ROOM_COLOUR, 2)

        if show_labels and room.centroid:
            cx, cy = to_px(room.centroid)
            label = room.label or room.type or room.id
            _draw_label(img, label, (cx, cy), _ROOM_COLOUR)

    # ---- Draw walls ----
    for wall in scene_graph.walls:
        p1 = to_px(wall.start)
        p2 = to_px(wall.end)
        cv2.line(img, p1, p2, _WALL_COLOUR, 3)
        if show_labels:
            mid = ((p1[0] + p2[0]) // 2, (p1[1] + p2[1]) // 2)
            length_str = f"{wall.length:.2f}m" if wall.length else wall.id
            _draw_label(img, length_str, mid, _WALL_COLOUR, font_scale=0.35)

    # ---- Draw doors ----
    for door in scene_graph.doors:
        cx, cy = to_px(door.center)
        half_w = max(3, int(door.width * m_to_px / 2))
        cv2.rectangle(img,
                      (cx - half_w, cy - 5),
                      (cx + half_w, cy + 5),
                      _DOOR_COLOUR, -1)
        if show_labels:
            _draw_label(img, door.id, (cx, cy - 10), _DOOR_COLOUR, font_scale=0.35)

    # ---- Draw windows ----
    for win in scene_graph.windows:
        cx, cy = to_px(win.center)
        half_w = max(3, int(win.width * m_to_px / 2))
        cv2.rectangle(img,
                      (cx - half_w, cy - 4),
                      (cx + half_w, cy + 4),
                      _WINDOW_COLOUR, 2)
        if show_labels:
            _draw_label(img, win.id, (cx, cy - 10), _WINDOW_COLOUR, font_scale=0.35)

    # ---- Confidence overlay (top-left corner) ----
    if show_confidence:
        conf = scene_graph.metadata.confidence_score
        conf_text = f"Overall confidence: {conf:.3f}"
        cv2.rectangle(img, (5, 5), (320, 30), (0, 0, 0), -1)
        cv2.putText(img, conf_text, (10, 22),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, _CONF_COLOUR, 1, cv2.LINE_AA)

    # ---- Save ----
    base = os.path.splitext(os.path.basename(image_path))[0]
    out_path = os.path.join(output_dir, f"{base}{filename_suffix}.png")
    cv2.imwrite(out_path, img)
    print(f"    [Visualization] Saved annotated image → {out_path}")
    return out_path


def _draw_label(
    img,
    text: str,
    pos: Tuple[int, int],
    colour: Tuple[int, int, int],
    font_scale: float = 0.45,
    thickness: int = 1,
):
    """Draw a small text label with a dark shadow for readability."""
    import cv2
    x, y = pos
    shadow_colour = (0, 0, 0)
    cv2.putText(img, text, (x + 1, y + 1),
                cv2.FONT_HERSHEY_SIMPLEX, font_scale, shadow_colour, thickness + 1, cv2.LINE_AA)
    cv2.putText(img, text, (x, y),
                cv2.FONT_HERSHEY_SIMPLEX, font_scale, colour, thickness, cv2.LINE_AA)
