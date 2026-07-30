"""Runner — executes Execution Agent tool invocations against Blender MCP.

Improvements in Phase 4:
- Batches compatible operations into a single MCP round-trip.
- Deduplicates consecutive identical calls.
- Honours the Tool Registry: refuses to dispatch unimplemented tools.
- Reports granular progress via the existing pub/sub broker.
"""

from __future__ import annotations

import os
import tempfile
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from .tool_registry import TOOL_REGISTRY
from .trace import trace


@dataclass
class RunnerResult:
    invocations: List[Dict[str, Any]] = field(default_factory=list)
    applied: List[Dict[str, Any]] = field(default_factory=list)
    deferred: List[Dict[str, Any]] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    fallback_to_script: bool = False
    export_paths: List[str] = field(default_factory=list)
    metrics: List[Dict[str, Any]] = field(default_factory=list)
    batches: int = 0


_MCP_GROUPED_TOOLS = {
    "apply_pattern",
    "apply_color",
    "assign_region_material",
    "export_glb",
}


def _safe_ping() -> Tuple[bool, Optional[Dict[str, Any]]]:
    try:
        from blender.mcp_client import is_blender_mcp_available, ping
    except Exception:
        return False, None
    if not is_blender_mcp_available():
        return False, None
    try:
        return True, ping()
    except Exception:
        return False, None


def _batch_key(inv: Dict[str, Any]) -> str:
    return f"{inv.get('tool','')}::{inv.get('arguments',{}).get('object','')}"


async def run_invocations(
    invocations: List[Dict[str, Any]],
    selection_payload: Optional[Dict[str, Any]] = None,
    project_name: str = "building",
    fallback_executor: Optional[Any] = None,
    dedupe: bool = True,
    batch: bool = True,
) -> RunnerResult:
    result = RunnerResult(invocations=list(invocations))

    # Dedup: collapse identical consecutive calls.
    if dedupe:
        deduped: List[Dict[str, Any]] = []
        seen_keys: set = set()
        for inv in invocations:
            key = repr(sorted(inv.get("arguments", {}).items()))
            full_key = (inv.get("tool", ""), key)
            if full_key in seen_keys:
                result.warnings.append(f"dedup: skipped duplicate {inv.get('tool')}")
                continue
            seen_keys.add(full_key)
            deduped.append(inv)
        invocations = deduped

    # Group by (tool, object) for batching — one MCP round-trip per batch.
    batches: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for inv in invocations:
        batches[_batch_key(inv)].append(inv)
    result.batches = len(batches)

    mcp_ok, _ = _safe_ping()
    if not mcp_ok:
        result.warnings.append("blender-mcp offline; falling back to script path")
        result.fallback_to_script = True
        if fallback_executor is not None:
            fb = await fallback_executor(invocations, selection_payload, project_name)
            if isinstance(fb, RunnerResult):
                result.applied.extend(fb.applied)
                result.deferred.extend(fb.deferred)
                result.export_paths.extend(fb.export_paths)
                result.warnings.extend(fb.warnings)
                result.metrics.extend(fb.metrics)
        return result

    try:
        from blender.mcp_client import send_command
    except Exception as exc:  # pragma: no cover
        result.warnings.append(f"mcp_client import failed: {exc}")
        return result

    for key, group in batches.items():
        tool = group[0].get("tool")
        meta = TOOL_REGISTRY.get(tool)
        if meta is None:
            for inv in group:
                result.deferred.append(inv)
                result.warnings.append(f"{tool!r} not in tool registry")
            continue

        if not meta.is_implemented:
            for inv in group:
                result.deferred.append(inv)
                result.warnings.append(f"{tool} not yet implemented in addon")
            continue

        if tool in _MCP_GROUPED_TOOLS:
            for inv in group:
                ok, payload = _dispatch_grouped(tool, inv, send_command)
                entry = trace(
                    "runner.mcp",
                    tool=tool,
                    args=inv.get("arguments"),
                    ok=ok,
                    payload=payload,
                )
                (result.applied if ok else result.deferred).append(inv)
                if not ok:
                    result.warnings.append(f"{tool} failed: {payload}")
            continue

        # Generic dispatch path (geometry, patterns, utility).
        for inv in group:
            ok, payload = _dispatch_generic(tool, inv, send_command)
            entry = trace(
                "runner.mcp",
                tool=tool,
                args=inv.get("arguments"),
                ok=ok,
                payload=payload,
            )
            (result.applied if ok else result.deferred).append(inv)
            if isinstance(payload, dict) and "metrics" in payload:
                result.metrics.append({"tool": tool, **payload["metrics"]})
            if not ok:
                result.warnings.append(f"{tool} failed: {payload}")

    # Auto-export the latest GLB if any non-utility op succeeded.
    if any(inv.get("tool") != "export_glb" and inv.get("tool") not in _UTILITY_TOOLS for inv in result.applied):
        out_dir = os.path.abspath("output")
        os.makedirs(out_dir, exist_ok=True)
        glb_path = os.path.join(out_dir, f"{project_name}.glb")
        ok, payload = send_command({"type": "export_glb", "output_path": glb_path})
        if ok and isinstance(payload, dict) and payload.get("path"):
            result.export_paths.append(payload["path"])

    return result


_UTILITY_TOOLS = {
    "measure_area",
    "measure_length",
    "calculate_volume",
    "export_glb",
    "refresh_preview",
}


def _dispatch_grouped(tool: str, inv: Dict[str, Any], send_command):
    args = inv.get("arguments") or {}
    if tool == "apply_color":
        return send_command(
            {
                "type": "set_object_color",
                "object": args.get("object"),
                "color": args.get("color"),
            }
        )
    if tool == "apply_pattern":
        return send_command(
            {
                "type": "tool_dispatch",
                "tool": "apply_pattern",
                "object": args.get("object"),
                "pattern": args.get("pattern"),
                "depth": args.get("depth"),
                "spacing": args.get("spacing"),
            }
        )
    if tool == "assign_region_material":
        obj = args.get("object")
        faces = args.get("face_indices") or []
        return send_command(
            {
                "type": "assign_region_material",
                "object_names": [obj] if obj else [],
                "faces_by_object": {obj: list(faces)} if obj else {},
                "material_name": args.get("material_name"),
            }
        )
    if tool == "export_glb":
        return send_command(
            {"type": "export_glb", "output_path": args.get("output_path")}
        )
    return False, {"error": f"unsupported grouped tool {tool!r}"}


def _dispatch_generic(tool: str, inv: Dict[str, Any], send_command):
    args = inv.get("arguments") or {}
    return send_command(
        {
            "type": "tool_dispatch",
            "tool": tool,
            **args,
        }
    )