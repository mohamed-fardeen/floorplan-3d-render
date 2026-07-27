"""
datasets/benchmark/generate_test_images.py
==========================================
Generates synthetic floor plan PNG images for benchmark testing.
These are NOT real scanned floor plans — they are procedurally drawn
architectural diagrams that match the accompanying *_gt.json ground truth files.

Run once to populate the datasets/benchmark/ directory:
    python datasets/benchmark/generate_test_images.py
"""

from __future__ import annotations

import os
import sys

import numpy as np

try:
    import cv2
except ImportError:
    sys.exit("opencv-python is required. Install with: pip install opencv-python")

# All sizes are in metres; we render at SCALE px/m
SCALE      = 50   # pixels per metre
IMG_SIZE   = 512  # output image size (square)
WALL_COLOR = (20, 20, 20)
BG_COLOR   = (245, 240, 230)
WALL_THICK = 3    # pixels
FONT       = cv2.FONT_HERSHEY_SIMPLEX
FONT_SCALE = 0.5
FONT_COLOR = (80, 80, 80)
DOOR_COLOR = (100, 60, 20)
WIN_COLOR  = (50, 150, 220)


def world_to_px(x: float, y: float, h: int) -> tuple[int, int]:
    """Convert world (metres) to image pixel (y-flip)."""
    return (int(x * SCALE), h - int(y * SCALE))


def draw_floor_plan(
    canvas: np.ndarray,
    walls: list,
    rooms: list,
    doors: list,
    windows: list,
    labels: list | None = None,
):
    h, w = canvas.shape[:2]

    # Room fills
    for i, room in enumerate(rooms):
        pts = np.array([world_to_px(x, y, h) for x, y in room["polygon"]], dtype=np.int32)
        hue = (i * 40) % 180
        # Convert HSV to BGR
        hsv = np.uint8([[[hue, 40, 235]]])
        bgr = cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)[0][0].tolist()
        cv2.fillPoly(canvas, [pts], tuple(bgr))

    # Walls
    for wall in walls:
        p1 = world_to_px(*wall["start"], h)
        p2 = world_to_px(*wall["end"],   h)
        cv2.line(canvas, p1, p2, WALL_COLOR, WALL_THICK)

    # Doors (small rectangles)
    for door in doors:
        cx, cy = world_to_px(*door["center"], h)
        half_w = int(door.get("width", 0.9) * SCALE / 2)
        cv2.rectangle(canvas, (cx - half_w, cy - 4), (cx + half_w, cy + 4), DOOR_COLOR, -1)

    # Windows (double line)
    for win in windows:
        cx, cy = world_to_px(*win["center"], h)
        half_w = int(win.get("width", 1.2) * SCALE / 2)
        cv2.rectangle(canvas, (cx - half_w, cy - 6), (cx + half_w, cy + 6), WIN_COLOR, 2)
        cv2.line(canvas, (cx - half_w, cy), (cx + half_w, cy), WIN_COLOR, 1)

    # Room type labels
    if labels:
        for label_info in labels:
            lx, ly = world_to_px(*label_info["pos"], h)
            cv2.putText(canvas, label_info["text"], (lx, ly),
                        FONT, FONT_SCALE, FONT_COLOR, 1, cv2.LINE_AA)


def generate_apartment_01():
    canvas = np.full((IMG_SIZE, IMG_SIZE, 3), BG_COLOR, dtype=np.uint8)
    walls = [
        {"start": [0.0, 0.0], "end": [10.0, 0.0]},
        {"start": [10.0, 0.0], "end": [10.0, 6.0]},
        {"start": [10.0, 6.0], "end": [0.0, 6.0]},
        {"start": [0.0, 6.0], "end": [0.0, 0.0]},
        {"start": [5.0, 0.0], "end": [5.0, 4.0]},
        {"start": [0.0, 3.5], "end": [5.0, 3.5]},
    ]
    rooms = [
        {"polygon": [[0.0, 0.0], [5.0, 0.0], [5.0, 3.5], [0.0, 3.5]]},
        {"polygon": [[0.0, 3.5], [5.0, 3.5], [5.0, 6.0], [0.0, 6.0]]},
        {"polygon": [[5.0, 0.0], [10.0, 0.0], [10.0, 6.0], [5.0, 6.0]]},
    ]
    doors   = [{"center": [2.5, 0.0], "width": 0.9},
               {"center": [7.5, 0.0], "width": 0.9},
               {"center": [5.0, 2.0], "width": 0.9}]
    windows = [{"center": [1.5, 6.0], "width": 1.2},
               {"center": [8.0, 6.0], "width": 1.5},
               {"center": [10.0, 3.0], "width": 1.2}]
    labels  = [{"text": "Bedroom",     "pos": [1.5, 2.0]},
               {"text": "Kitchen",     "pos": [1.5, 5.0]},
               {"text": "Living Room", "pos": [6.0, 3.0]}]
    draw_floor_plan(canvas, walls, rooms, doors, windows, labels)
    return canvas


def generate_office_01():
    """Open-plan office with 4 meeting rooms along one wall."""
    canvas = np.full((IMG_SIZE, IMG_SIZE, 3), BG_COLOR, dtype=np.uint8)
    walls = [
        {"start": [0.0, 0.0], "end": [10.0, 0.0]},
        {"start": [10.0, 0.0], "end": [10.0, 8.0]},
        {"start": [10.0, 8.0], "end": [0.0, 8.0]},
        {"start": [0.0, 8.0], "end": [0.0, 0.0]},
        # 4 meeting rooms along the top wall
        {"start": [0.0, 5.5], "end": [10.0, 5.5]},
        {"start": [2.5, 5.5], "end": [2.5, 8.0]},
        {"start": [5.0, 5.5], "end": [5.0, 8.0]},
        {"start": [7.5, 5.5], "end": [7.5, 8.0]},
    ]
    rooms = [
        {"polygon": [[0.0, 0.0], [10.0, 0.0], [10.0, 5.5], [0.0, 5.5]]},
        {"polygon": [[0.0, 5.5], [2.5, 5.5], [2.5, 8.0], [0.0, 8.0]]},
        {"polygon": [[2.5, 5.5], [5.0, 5.5], [5.0, 8.0], [2.5, 8.0]]},
        {"polygon": [[5.0, 5.5], [7.5, 5.5], [7.5, 8.0], [5.0, 8.0]]},
        {"polygon": [[7.5, 5.5], [10.0, 5.5], [10.0, 8.0], [7.5, 8.0]]},
    ]
    doors = [{"center": [5.0, 0.0], "width": 1.2},
             {"center": [1.25, 5.5], "width": 0.9},
             {"center": [3.75, 5.5], "width": 0.9},
             {"center": [6.25, 5.5], "width": 0.9},
             {"center": [8.75, 5.5], "width": 0.9}]
    windows = [{"center": [2.5, 0.0], "width": 1.5},
               {"center": [7.5, 0.0], "width": 1.5},
               {"center": [10.0, 2.0], "width": 1.5},
               {"center": [10.0, 7.0], "width": 1.5}]
    draw_floor_plan(canvas, walls, rooms, doors, windows)
    return canvas


def main():
    out_dir = os.path.dirname(os.path.abspath(__file__))

    images = {
        "apartment_01.png": generate_apartment_01(),
        "office_01.png":    generate_office_01(),
    }

    for fname, img in images.items():
        path = os.path.join(out_dir, fname)
        cv2.imwrite(path, img)
        print(f"  Saved: {path}")

    print(f"\nGenerated {len(images)} test images in {out_dir}")


if __name__ == "__main__":
    main()
