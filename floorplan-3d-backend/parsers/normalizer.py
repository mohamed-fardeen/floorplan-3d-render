"""
parsers/normalizer.py
=====================
Coordinate normalization and confidence mapping layer.

Every parser may output different coordinate systems, units, and confidence
formats.  This module converts them all into the single canonical system that
downstream components (Geometry Validation, OCR, Scene Graph, Blender) expect.

Canonical system
----------------
  origin          : (0, 0) at the top-left of the bounding box of all geometry
  axis orientation: x → right,  y → up   (standard math convention)
  units           : metres
  polygon winding : counter-clockwise (CCW) for room polygons
  wall thickness  : metres
  rotation        : 0 = aligned with +x axis
"""

from __future__ import annotations

import copy
import math
from typing import List, Tuple

from shapely.geometry import Polygon

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from schema import (
    SceneGraph, Wall, Door, Window, Room, Metadata
)


# ---------------------------------------------------------------------------
# Confidence schema
# ---------------------------------------------------------------------------

class ParserConfidence:
    """
    Uniform confidence record produced by :func:`normalize_confidence`.

    All values are in [0, 1].  Missing data is represented by ``None``.
    """
    def __init__(
        self,
        walls: float | None = None,
        doors: float | None = None,
        windows: float | None = None,
        rooms: float | None = None,
        overall: float | None = None,
    ):
        self.walls   = walls
        self.doors   = doors
        self.windows = windows
        self.rooms   = rooms
        self.overall = overall

    def to_dict(self) -> dict:
        return {
            "walls":   self.walls,
            "doors":   self.doors,
            "windows": self.windows,
            "rooms":   self.rooms,
            "overall": self.overall,
        }

    def __repr__(self) -> str:  # pragma: no cover
        d = {k: f"{v:.3f}" if v is not None else "N/A" for k, v in self.to_dict().items()}
        return f"ParserConfidence({d})"


def normalize_confidence(
    raw: dict | float | None,
    *,
    walls:   float | None = None,
    doors:   float | None = None,
    windows: float | None = None,
    rooms:   float | None = None,
) -> ParserConfidence:
    """
    Normalize heterogeneous parser confidence values into a :class:`ParserConfidence`.

    Accepts any of:
      - A pre-structured dict:  ``{"walls": 0.9, "doors": 0.8, ...}``
      - A single float scalar representing the overall confidence.
      - ``None`` (all fields remain ``None``).
      - Individual keyword arguments for each class.

    The ``overall`` field is computed as the mean of all non-None class scores.
    """
    if isinstance(raw, dict):
        walls   = raw.get("walls",   walls)
        doors   = raw.get("doors",   doors)
        windows = raw.get("windows", windows)
        rooms   = raw.get("rooms",   rooms)
        overall = raw.get("overall", None)
    elif isinstance(raw, float):
        overall = float(raw)
    else:
        overall = None

    # Compute overall if not explicitly given
    class_scores = [v for v in [walls, doors, windows, rooms] if v is not None]
    if overall is None and class_scores:
        overall = sum(class_scores) / len(class_scores)

    # Clamp all to [0, 1]
    def _clamp(v: float | None) -> float | None:
        return max(0.0, min(1.0, float(v))) if v is not None else None

    return ParserConfidence(
        walls   = _clamp(walls),
        doors   = _clamp(doors),
        windows = _clamp(windows),
        rooms   = _clamp(rooms),
        overall = _clamp(overall),
    )


# ---------------------------------------------------------------------------
# Coordinate normalizer
# ---------------------------------------------------------------------------

class CoordinateNormalizer:
    """
    Normalises all spatial data in a :class:`SceneGraph` into the canonical
    coordinate system so that downstream modules are parser-agnostic.

    Parameters
    ----------
    pixel_to_meter : float
        Conversion ratio.  e.g. 0.05 means 1 pixel → 0.05 m.
        Pass ``None`` to keep existing ``scene_graph.metadata.scale_pixel_to_meter``.
    flip_y : bool
        Many parsers use image coordinates (y increases downward).  Set
        ``True`` to flip so y increases upward.
    rotate_deg : float
        Additional rotation to apply (degrees, CCW) after flipping.
    """

    def __init__(
        self,
        pixel_to_meter: float | None = None,
        flip_y: bool = False,
        rotate_deg: float = 0.0,
    ):
        self.pixel_to_meter = pixel_to_meter
        self.flip_y         = flip_y
        self.rotate_deg     = rotate_deg

    def point_to_meter(self, point: Tuple[float, float], max_y: float = 512.0) -> Tuple[float, float]:
        """Convert a single (x, y) point from pixels to meters."""
        scale = self.pixel_to_meter or 0.0195
        angle_rad = math.radians(self.rotate_deg)
        return self._pt(point[0], point[1], scale, self.flip_y, max_y, angle_rad)

    def dist_to_meter(self, dist_px: float) -> float:
        """Convert a scalar pixel distance/thickness to meters."""
        scale = self.pixel_to_meter or 0.0195
        return round(float(dist_px) * scale, 6)

    # -- helpers ----------------------------------------------------------- #

    @staticmethod
    def _pt(x: float, y: float, scale: float, flip_y: bool, max_y: float, angle_rad: float) -> Tuple[float, float]:
        """Apply scale → flip → rotate → round to a single 2-D point."""
        x = x * scale
        y = y * scale
        if flip_y:
            y = max_y * scale - y
        if angle_rad:
            cos_a, sin_a = math.cos(angle_rad), math.sin(angle_rad)
            x, y = x * cos_a - y * sin_a, x * sin_a + y * cos_a
        return (round(x, 6), round(y, 6))

    @staticmethod
    def _ensure_ccw(polygon: List[Tuple[float, float]]) -> List[Tuple[float, float]]:
        """Ensure a polygon's winding order is counter-clockwise."""
        if len(polygon) < 3:
            return polygon
        poly = Polygon(polygon)
        if not poly.is_valid:
            poly = poly.buffer(0)
        # Shapely exterior is CCW when coordinates are in math convention
        if poly.geom_type == 'Polygon':
            coords = list(poly.exterior.coords)[:-1]  # drop repeated closing point
            return [(round(x, 6), round(y, 6)) for x, y in coords]
        return polygon

    def normalize(self, scene_graph: SceneGraph) -> SceneGraph:
        """
        Return a deep-copy of *scene_graph* with all coordinates normalised.
        """
        sg = copy.deepcopy(scene_graph)
        scale = self.pixel_to_meter if self.pixel_to_meter is not None else sg.metadata.scale_pixel_to_meter
        angle_rad = math.radians(self.rotate_deg)

        # Determine max_y for flip (bounding box of all points)
        all_y: List[float] = []
        for w in sg.walls:
            all_y += [w.start[1], w.end[1]]
        for r in sg.rooms:
            all_y += [p[1] for p in r.polygon]
        for d in sg.doors:
            all_y.append(d.center[1])
        for win in sg.windows:
            all_y.append(win.center[1])
        max_y = max(all_y) if all_y else 0.0

        def pt(x: float, y: float) -> Tuple[float, float]:
            return self._pt(x, y, scale, self.flip_y, max_y, angle_rad)

        # Transform walls
        for wall in sg.walls:
            wall.start = pt(*wall.start)
            wall.end   = pt(*wall.end)
            if wall.length is not None:
                # Recompute from transformed coords
                dx = wall.end[0] - wall.start[0]
                dy = wall.end[1] - wall.start[1]
                wall.length = round(math.sqrt(dx * dx + dy * dy), 6)
            wall.thickness = round(wall.thickness * scale, 6)

        # Transform rooms
        for room in sg.rooms:
            room.polygon = self._ensure_ccw([pt(*p) for p in room.polygon])
            if room.centroid is not None:
                room.centroid = pt(*room.centroid)
            room.area = None  # will be recomputed by validation

        # Transform doors
        for door in sg.doors:
            door.center = pt(*door.center)
            door.width  = round(door.width * scale, 6)

        # Transform windows
        for win in sg.windows:
            win.center = pt(*win.center)
            win.width  = round(win.width * scale, 6)

        # Update metadata
        sg.metadata.units = "meters"
        sg.metadata.scale_pixel_to_meter = scale

        # Translate so that minimum x/y is at the origin (0, 0)
        sg = self._translate_to_origin(sg)

        return sg

    @staticmethod
    def _translate_to_origin(sg: SceneGraph) -> SceneGraph:
        """Shift all geometry so the bounding box starts at (0, 0)."""
        all_x: List[float] = []
        all_y: List[float] = []
        for w in sg.walls:
            all_x += [w.start[0], w.end[0]]
            all_y += [w.start[1], w.end[1]]
        for r in sg.rooms:
            all_x += [p[0] for p in r.polygon]
            all_y += [p[1] for p in r.polygon]
        for d in sg.doors:
            all_x.append(d.center[0])
            all_y.append(d.center[1])
        for win in sg.windows:
            all_x.append(win.center[0])
            all_y.append(win.center[1])

        if not all_x:
            return sg

        min_x, min_y = min(all_x), min(all_y)

        def shift(p: Tuple[float, float]) -> Tuple[float, float]:
            return (round(p[0] - min_x, 6), round(p[1] - min_y, 6))

        for w in sg.walls:
            w.start = shift(w.start)
            w.end   = shift(w.end)
        for r in sg.rooms:
            r.polygon = [shift(p) for p in r.polygon]
            if r.centroid:
                r.centroid = shift(r.centroid)
        for d in sg.doors:
            d.center = shift(d.center)
        for win in sg.windows:
            win.center = shift(win.center)

        return sg
