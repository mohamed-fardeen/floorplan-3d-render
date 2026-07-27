import re
import copy
from typing import List, Tuple, Optional

from shapely.geometry import Polygon, Point, LineString
from shapely.ops import nearest_points

from schema import SceneGraph, OCRDetection


# ─────────────────────────────────────────────────────────────────────────────
# Dimension classification
# ─────────────────────────────────────────────────────────────────────────────
#
# A "dimension" must look like an actual measurement:
#   - Imperial:    12' 4"   /   12 ft   /   4"
#   - Metric:      3.5m   /   3500mm   /   350 cm
#   - Bare number: 1200   (interpreted as mm, conservative)
#
# Pure integers like "101" or "12" inside a sheet title (e.g. "VILLA 12")
# are NOT treated as dimensions — they need a unit suffix or trailing prime
# to count.

_DIMENSION_RE = re.compile(
    r"""
    ^\s*
    (?:
        # Imperial feet + optional inches: 12' 4"  /  12'  /  12ft
        (?P<feet>\d+(?:\.\d+)?)\s*(?:'|ft)\s*(?P<inch>\d+(?:\.\d+)?\s*(?:"|in|'')?)?
      | (?:^|\s)
        # Metric:  3.5m / 3500mm / 350 cm / 12 m
        (?P<metric_val>\d+(?:\.\d+)?)\s*(?P<metric_unit>mm|cm|m)\b
      | (?:^|\s)
        # Inches only:  4" / 4 in
        (?P<inches_only>\d+(?:\.\d+)?)\s*(?:"in|'')
    )
    \s*$
    """,
    re.VERBOSE | re.IGNORECASE,
)

_METRIC_TO_M = {
    "mm": 0.001,
    "cm": 0.01,
    "m":  1.0,
}


def is_dimension(text: str) -> bool:
    """True if `text` looks like a measurement (feet/inches or Xm/mm/cm)."""
    if _DIMENSION_RE.match(text):
        return True
    # Also accept the bare-feet shorthand:  "16' 4\"" inside the same string
    return bool(re.search(r"\d+(?:\.\d+)?\s*(?:'|ft|mm|cm|\bm\b|\")", text, re.IGNORECASE))


def parse_dimension_to_meters(text: str) -> Optional[float]:
    """
    Convert an OCR'd dimension string to metres.

    Returns None if the string cannot be parsed.
    """
    if not text:
        return None

    # 1) Imperial feet (+ optional inches):  12' 4"  /  12ft 4in  /  12'
    _IMP_RE = re.compile(
        r"(?P<feet>\d+(?:\.\d+)?)\s*(?:'|ft)\s*(?P<inch>\d+(?:\.\d+)?)?(?:\s*(?:" + chr(34) + r"|in|''))?",
        re.IGNORECASE,
    )
    m = _IMP_RE.search(text)
    if m and m.group("feet"):
        feet = float(m.group("feet"))
        inch = float(m.group("inch") or 0)
        return feet * 0.3048 + inch * 0.0254

    # 2) Metric Xm / Xmm / Xcm
    m = re.search(
        r"(?P<val>\d+(?:\.\d+)?)\s*(?P<unit>mm|cm|m)\b",
        text,
        re.IGNORECASE,
    )
    if m:
        return float(m.group("val")) * _METRIC_TO_M[m.group("unit").lower()]

    # 3) Inches only:  4"  /  4 in  /  4''
    #    No trailing \b because "\b" is satisfied only when a word char follows,
    #    which fails for " at end-of-string.
    _INCH_ONLY_RE = re.compile(
        r"(?P<inch>\d+(?:\.\d+)?)\s*(?:" + chr(34) + r"|in|'')(?=\W|$)",
        re.IGNORECASE,
    )
    m = _INCH_ONLY_RE.search(text)
    if m:
        return float(m.group("inch")) * 0.0254

    return None


# ─────────────────────────────────────────────────────────────────────────────
# Enrichment
# ─────────────────────────────────────────────────────────────────────────────

def enrich_scene_graph(
    scene_graph: SceneGraph,
    detections: List[OCRDetection],
    *,
    dimension_snap_distance: float = 1.0,
    length_match_tolerance: float = 0.30,
) -> Tuple[SceneGraph, List[str]]:
    """
    Enriches the canonical Scene Graph with OCR detections using spatial logic.

    Parameters
    ----------
    scene_graph : SceneGraph
        Existing graph (will be deep-copied, never mutated in place).
    detections : List[OCRDetection]
        Text regions returned by the OCR engine.
    dimension_snap_distance : float
        Max metres a text region may sit from a wall to be considered its
        dimension label.
    length_match_tolerance : float
        When the parsed dimension disagrees with the wall's geometric length
        by more than this many metres, the parsed value is treated as
        decorative and `Wall.length` is left untouched (but the label is
        still attached for debugging).

    Returns
    -------
    (SceneGraph, audit_log)
    """
    sg = copy.deepcopy(scene_graph)
    audit_log: List[str] = []

    sg.ocr_detections = detections

    for det in detections:
        det_pt = Point(
            (det.bounding_box[0] + det.bounding_box[2]) / 2,
            (det.bounding_box[1] + det.bounding_box[3]) / 2,
        )

        # ── 1. Dimension → nearest wall ────────────────────────────────────
        if is_dimension(det.text):
            min_dist = float("inf")
            closest_wall = None

            for wall in sg.walls:
                wall_line = LineString([wall.start, wall.end])
                d = det_pt.distance(wall_line)
                if d < min_dist:
                    min_dist = d
                    closest_wall = wall

            if closest_wall is not None and min_dist < dimension_snap_distance:
                closest_wall.dimension_label = det.text
                audit_log.append(
                    f"Associated dimension '{det.text}' to wall {closest_wall.id} "
                    f"(distance: {min_dist:.2f}m)"
                )

                # If we can parse the dimension, update Wall.length:
                #   - If wall already has a geometric length AND the parsed
                #     value matches within tolerance: keep both consistent.
                #   - If wall has a length but they disagree: trust the
                #     geometry, leave the parsed value as a label only.
                #   - If wall has no length yet: fill it from the OCR'd
                #     dimension (useful for parser outputs that don't
                #     compute length).
                parsed_m = parse_dimension_to_meters(det.text)
                if parsed_m is not None:
                    if closest_wall.length is None:
                        closest_wall.length = parsed_m
                        audit_log.append(
                            f"Set wall {closest_wall.id} length to "
                            f"{parsed_m:.3f}m (from OCR, no geometric length "
                            f"available)."
                        )
                    elif abs(parsed_m - closest_wall.length) <= length_match_tolerance:
                        old_len = closest_wall.length
                        closest_wall.length = parsed_m
                        audit_log.append(
                            f"Snapped wall {closest_wall.id} length "
                            f"{old_len:.3f}m → {parsed_m:.3f}m (OCR matches)."
                        )
                    else:
                        audit_log.append(
                            f"[INFO] Wall {closest_wall.id} length "
                            f"{closest_wall.length:.3f}m disagrees with OCR "
                            f"'{det.text}' ({parsed_m:.3f}m); keeping "
                            f"geometric value."
                        )
                continue

        # ── 2. Room label ──────────────────────────────────────────────────
        matched_room = False
        for room in sg.rooms:
            if len(room.polygon) < 3:
                continue
            try:
                room_poly = Polygon(room.polygon)
            except Exception:
                continue
            if not room_poly.is_valid:
                room_poly = room_poly.buffer(0)
            if room_poly.is_empty or room_poly.geom_type != "Polygon":
                continue
            if room_poly.contains(det_pt):
                matched_room = True
                # OCR confidence must clear threshold to override parser default.
                if det.confidence > 0.8:
                    old_type = room.type
                    room.type = det.text
                    room.label = det.text
                    room.label_confidence = det.confidence
                    room.ocr_source = "OCR Engine"

                    if (
                        old_type
                        and old_type != "Unknown"
                        and old_type.lower() != det.text.lower()
                    ):
                        audit_log.append(
                            f"OVERRIDE: Room {room.id} type changed from "
                            f"'{old_type}' to '{det.text}' based on "
                            f"high-confidence OCR."
                        )
                    else:
                        audit_log.append(
                            f"Assigned label '{det.text}' to room {room.id}."
                        )
                break

        if matched_room:
            continue

        # ── 3. Project metadata (title block) ──────────────────────────────
        text_upper = det.text.upper()
        if (
            "PROJECT" in text_upper
            or "VILLA" in text_upper
            or "PLAN" in text_upper
            or "SHEET" in text_upper
            or "DRAWING" in text_upper
        ):
            sg.metadata.project_name = det.text
            audit_log.append(f"Assigned '{det.text}' as project name.")

    return sg, audit_log
