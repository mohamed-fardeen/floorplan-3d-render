"""Construction Rules — deterministic validation before Execution.

These are *not* AI decisions. They are hard printable-construction limits
drawn from the brief:

- minimum wall thickness
- maximum printable pattern depth
- maximum curvature limits
- printable rib spacing
- pattern / material compatibility
- material compatibility matrix

The Engine returns a structured `RuleReport` so the orchestrator can
abort, warn, or proceed before any tool runs.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional

from .tool_registry import TOOL_REGISTRY


@dataclass
class RuleViolation:
    rule: str
    severity: str  # "error" | "warning"
    message: str
    tool: Optional[str] = None
    args: Optional[Dict[str, Any]] = None


@dataclass
class RuleReport:
    ok: bool = True
    violations: List[RuleViolation] = field(default_factory=list)

    def add(self, v: RuleViolation) -> None:
        self.violations.append(v)
        if v.severity == "error":
            self.ok = False

    def merge(self, other: "RuleReport") -> None:
        self.violations.extend(other.violations)
        if not other.ok:
            self.ok = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ok": self.ok,
            "violations": [v.__dict__ for v in self.violations],
        }


# ──────────────────────────────────────────────────────────────────────
# Limits (metres). Tweak in one place.
# ──────────────────────────────────────────────────────────────────────


MIN_WALL_THICKNESS_M = 0.05
MAX_PATTERN_DEPTH_M = 0.08
MIN_PATTERN_DEPTH_M = 0.005
MAX_CURVE_RADIUS_M = 8.0
MIN_PATTERN_SPACING_M = 0.02
MAX_PATTERN_SPACING_M = 0.5


# Materials that cannot accept deep surface relief.
MATERIAL_NO_PATTERN = {"oak_wood", "marble", "granite"}


# ──────────────────────────────────────────────────────────────────────
# Public API
# ──────────────────────────────────────────────────────────────────────


def validate_invocations(
    invocations: Iterable[Dict[str, Any]],
    selection_payload: Optional[Dict[str, Any]] = None,
) -> RuleReport:
    report = RuleReport()
    for inv in invocations or []:
        report.merge(_validate_invocation(inv))
    return report


def validate_selection(selection_payload: Optional[Dict[str, Any]]) -> RuleReport:
    report = RuleReport()
    if not selection_payload:
        report.add(RuleViolation("selection.empty", "error", "no active selection"))
        return report
    if not selection_payload.get("meshRefs"):
        report.add(RuleViolation("selection.no_mesh", "error", "selection has no meshRefs"))
    if not selection_payload.get("faceRefs"):
        report.add(RuleViolation("selection.no_faces", "warning", "selection has no faceRefs"))
    return report


# ──────────────────────────────────────────────────────────────────────
# Per-invocation rules
# ──────────────────────────────────────────────────────────────────────


def _validate_invocation(inv: Dict[str, Any]) -> RuleReport:
    report = RuleReport()
    tool = inv.get("tool")
    args = inv.get("arguments") or {}

    if tool not in TOOL_REGISTRY:
        report.add(
            RuleViolation(
                "tool.unknown",
                "error",
                f"unknown tool {tool!r}",
                tool=tool,
                args=args,
            )
        )
        return report

    meta = TOOL_REGISTRY[tool]
    if not meta.is_implemented:
        report.add(
            RuleViolation(
                "tool.unimplemented",
                "warning",
                f"{tool} not yet implemented in addon",
                tool=tool,
                args=args,
            )
        )

    # Required params
    for key in meta.required_params:
        if key not in args:
            report.add(
                RuleViolation(
                    "args.missing",
                    "error",
                    f"{tool}: missing required arg {key!r}",
                    tool=tool,
                    args=args,
                )
            )

    # Specific numeric limits
    if tool in {"curve_wall"}:
        radius = float(args.get("radius", 0) or 0)
        if radius <= 0:
            report.add(RuleViolation(
                "geometry.curve.invalid_radius",
                "error",
                "curve_wall radius must be > 0",
                tool=tool, args=args,
            ))
        if radius > MAX_CURVE_RADIUS_M:
            report.add(RuleViolation(
                "geometry.curve.too_large",
                "warning",
                f"radius {radius}m exceeds printable curvature limit ({MAX_CURVE_RADIUS_M}m)",
                tool=tool, args=args,
            ))
    if tool == "bevel_region":
        width = float(args.get("width", 0) or 0)
        if width > MAX_PATTERN_DEPTH_M:
            report.add(RuleViolation(
                "geometry.bevel.too_wide",
                "warning",
                f"bevel width {width}m exceeds printable pattern depth ({MAX_PATTERN_DEPTH_M}m)",
                tool=tool, args=args,
            ))
    if tool in {"apply_stacked_coils", "apply_wave_pattern", "apply_ribbed_pattern",
                "apply_honeycomb_pattern", "apply_woven_pattern", "adjust_pattern_depth",
                "adjust_pattern_spacing"}:
        depth = args.get("depth")
        if depth is not None:
            d = float(depth)
            if d < MIN_PATTERN_DEPTH_M or d > MAX_PATTERN_DEPTH_M:
                report.add(RuleViolation(
                    "pattern.depth.out_of_range",
                    "warning",
                    f"pattern depth {d}m outside printable range "
                    f"[{MIN_PATTERN_DEPTH_M}, {MAX_PATTERN_DEPTH_M}]",
                    tool=tool, args=args,
                ))
        spacing = args.get("spacing")
        if spacing is not None:
            s = float(spacing)
            if s < MIN_PATTERN_SPACING_M or s > MAX_PATTERN_SPACING_M:
                report.add(RuleViolation(
                    "pattern.spacing.out_of_range",
                    "warning",
                    f"pattern spacing {s}m outside printable range "
                    f"[{MIN_PATTERN_SPACING_M}, {MAX_PATTERN_SPACING_M}]",
                    tool=tool, args=args,
                ))
    if tool == "set_material":
        mat = args.get("material_name") or ""
        if mat in MATERIAL_NO_PATTERN:
            report.add(RuleViolation(
                "material.pattern_incompatible",
                "warning",
                f"material {mat!r} does not accept surface patterns",
                tool=tool, args=args,
            ))

    return report


__all__ = [
    "RuleReport",
    "RuleViolation",
    "validate_invocations",
    "validate_selection",
    "MIN_WALL_THICKNESS_M",
    "MAX_PATTERN_DEPTH_M",
    "MAX_CURVE_RADIUS_M",
]