"""
parsers/failure_analysis.py
============================
Automatic parser failure detection and diagnostic reporting.

When a parser produces a SceneGraph, this module inspects it for structural
problems that would cause downstream nodes to fail or produce bad 3D output.

Usage
-----
    from parsers.failure_analysis import analyze_failures, FailureReport
    report = analyze_failures(scene_graph)
    print(report.summary())
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import List, Tuple

from shapely.geometry import Polygon, LineString, MultiPolygon

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from schema import SceneGraph


# ---------------------------------------------------------------------------
# Thresholds
# ---------------------------------------------------------------------------

_MIN_WALL_LENGTH     = 0.05   # metres — shorter walls are almost certainly noise
_MIN_ROOM_AREA       = 0.5    # m²     — rooms smaller than this are noise
_MAX_ROOM_AREA       = 500.0  # m²     — sanity cap
_OPEN_ENDPOINT_TOL   = 0.3    # metres — wall endpoints must be within this to be "connected"
_DOOR_WALL_MAX_DIST  = 1.0    # metres — door center must be within this of its wall
_DUP_WALL_TOL        = 0.1    # metres — walls closer than this are likely duplicates


@dataclass
class Issue:
    severity: str        # "ERROR" | "WARNING" | "INFO"
    category: str        # "walls" | "rooms" | "doors" | "windows" | "scaling"
    element_id: str
    description: str

    def __str__(self) -> str:
        return f"[{self.severity}][{self.category}] {self.element_id}: {self.description}"


@dataclass
class FailureReport:
    issues: List[Issue] = field(default_factory=list)

    @property
    def errors(self) -> List[Issue]:
        return [i for i in self.issues if i.severity == "ERROR"]

    @property
    def warnings(self) -> List[Issue]:
        return [i for i in self.issues if i.severity == "WARNING"]

    @property
    def has_critical_failures(self) -> bool:
        return len(self.errors) > 0

    def summary(self) -> str:
        lines = [
            "=" * 55,
            "  PARSER FAILURE ANALYSIS",
            "=" * 55,
            f"  Total issues : {len(self.issues)}",
            f"  Errors       : {len(self.errors)}",
            f"  Warnings     : {len(self.warnings)}",
            "-" * 55,
        ]
        for issue in self.issues:
            lines.append(str(issue))
        if not self.issues:
            lines.append("  No issues detected. ✓")
        lines.append("=" * 55)
        return "\n".join(lines)

    def to_dict(self) -> dict:
        return {
            "total": len(self.issues),
            "errors": len(self.errors),
            "warnings": len(self.warnings),
            "issues": [
                {
                    "severity": i.severity,
                    "category": i.category,
                    "element_id": i.element_id,
                    "description": i.description,
                }
                for i in self.issues
            ],
        }


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def analyze_failures(scene_graph: SceneGraph) -> FailureReport:
    """
    Inspect *scene_graph* for structural failures and return a :class:`FailureReport`.

    Checks performed
    ----------------
    * missing rooms (no room polygons at all)
    * disconnected walls (open endpoints that don't connect to any other wall)
    * broken polygons (fewer than 3 points, self-intersecting, zero area)
    * missing openings (no doors AND no windows while walls exist)
    * duplicated walls (overlapping or near-identical segments)
    * incorrect scaling (implausibly large or small geometry)
    * orphaned doors / windows (reference non-existent wall ids)
    """
    report = FailureReport()
    _check_rooms(scene_graph, report)
    _check_walls(scene_graph, report)
    _check_openings(scene_graph, report)
    _check_scaling(scene_graph, report)
    return report


# ---------------------------------------------------------------------------
# Individual checks
# ---------------------------------------------------------------------------

def _check_rooms(sg: SceneGraph, report: FailureReport):
    if not sg.rooms:
        report.issues.append(Issue(
            severity="ERROR",
            category="rooms",
            element_id="<all>",
            description="No rooms detected. Parser may have failed to identify floor regions.",
        ))
        return

    for room in sg.rooms:
        if len(room.polygon) < 3:
            report.issues.append(Issue(
                severity="ERROR",
                category="rooms",
                element_id=room.id,
                description=f"Polygon has only {len(room.polygon)} points (minimum 3 required).",
            ))
            continue

        try:
            poly = Polygon(room.polygon)
        except Exception as e:
            report.issues.append(Issue(
                severity="ERROR",
                category="rooms",
                element_id=room.id,
                description=f"Cannot construct Shapely polygon: {e}",
            ))
            continue

        if not poly.is_valid:
            report.issues.append(Issue(
                severity="WARNING",
                category="rooms",
                element_id=room.id,
                description="Polygon is invalid (self-intersecting). Will be repaired by validation node.",
            ))

        if poly.area < _MIN_ROOM_AREA:
            report.issues.append(Issue(
                severity="WARNING",
                category="rooms",
                element_id=room.id,
                description=f"Room area {poly.area:.3f} m² is very small (< {_MIN_ROOM_AREA} m²).",
            ))
        elif poly.area > _MAX_ROOM_AREA:
            report.issues.append(Issue(
                severity="WARNING",
                category="rooms",
                element_id=room.id,
                description=f"Room area {poly.area:.1f} m² is implausibly large (> {_MAX_ROOM_AREA} m²).",
            ))


def _check_walls(sg: SceneGraph, report: FailureReport):
    if not sg.walls:
        report.issues.append(Issue(
            severity="ERROR",
            category="walls",
            element_id="<all>",
            description="No walls detected. Parser may have failed entirely.",
        ))
        return

    # Collect all endpoints
    endpoints: List[Tuple[float, float]] = []
    for w in sg.walls:
        endpoints.append(w.start)
        endpoints.append(w.end)

    for wall in sg.walls:
        # Zero-length / short wall
        dx = wall.end[0] - wall.start[0]
        dy = wall.end[1] - wall.start[1]
        length = math.sqrt(dx * dx + dy * dy)
        if length < _MIN_WALL_LENGTH:
            report.issues.append(Issue(
                severity="WARNING",
                category="walls",
                element_id=wall.id,
                description=f"Wall length {length:.4f} m is extremely short.",
            ))

        # Disconnected endpoint check
        for endpoint in (wall.start, wall.end):
            connected = False
            for other in sg.walls:
                if other.id == wall.id:
                    continue
                for other_pt in (other.start, other.end):
                    d = math.hypot(endpoint[0] - other_pt[0], endpoint[1] - other_pt[1])
                    if d < _OPEN_ENDPOINT_TOL:
                        connected = True
                        break
                if connected:
                    break
            if not connected:
                report.issues.append(Issue(
                    severity="WARNING",
                    category="walls",
                    element_id=wall.id,
                    description=(
                        f"Endpoint {endpoint} is disconnected from all other walls "
                        f"(nearest gap > {_OPEN_ENDPOINT_TOL} m)."
                    ),
                ))

    # Duplicate wall detection
    seen: List[tuple] = []
    for wall in sg.walls:
        key_a = (round(wall.start[0], 1), round(wall.start[1], 1),
                 round(wall.end[0], 1), round(wall.end[1], 1))
        key_b = (round(wall.end[0], 1), round(wall.end[1], 1),
                 round(wall.start[0], 1), round(wall.start[1], 1))
        if key_a in seen or key_b in seen:
            report.issues.append(Issue(
                severity="WARNING",
                category="walls",
                element_id=wall.id,
                description=f"Wall appears to be a duplicate of an earlier wall segment.",
            ))
        else:
            seen.append(key_a)


def _check_openings(sg: SceneGraph, report: FailureReport):
    wall_ids = {w.id for w in sg.walls}

    # Missing openings overall
    if sg.walls and not sg.doors and not sg.windows:
        report.issues.append(Issue(
            severity="WARNING",
            category="doors",
            element_id="<all>",
            description="No doors or windows detected. Floor plan may have no openings.",
        ))

    # Orphaned doors
    for door in sg.doors:
        if door.wall_id not in wall_ids:
            report.issues.append(Issue(
                severity="ERROR",
                category="doors",
                element_id=door.id,
                description=f"References non-existent wall '{door.wall_id}'.",
            ))

    # Orphaned windows
    for win in sg.windows:
        if win.wall_id not in wall_ids:
            report.issues.append(Issue(
                severity="ERROR",
                category="windows",
                element_id=win.id,
                description=f"References non-existent wall '{win.wall_id}'.",
            ))


def _check_scaling(sg: SceneGraph, report: FailureReport):
    """Detect implausibly scaled geometry."""
    if not sg.walls:
        return

    lengths = []
    for w in sg.walls:
        dx = w.end[0] - w.start[0]
        dy = w.end[1] - w.start[1]
        lengths.append(math.sqrt(dx * dx + dy * dy))

    max_length = max(lengths) if lengths else 0.0
    mean_length = sum(lengths) / len(lengths) if lengths else 0.0

    if max_length > 200.0:
        report.issues.append(Issue(
            severity="WARNING",
            category="scaling",
            element_id="<walls>",
            description=(
                f"Longest wall is {max_length:.1f} m. Possible scaling error "
                f"(expected residential range: 1–30 m)."
            ),
        ))

    if max_length < 0.1:
        report.issues.append(Issue(
            severity="ERROR",
            category="scaling",
            element_id="<walls>",
            description=(
                f"Longest wall is only {max_length:.4f} m. Parser may have "
                f"returned un-scaled pixel coordinates."
            ),
        ))
