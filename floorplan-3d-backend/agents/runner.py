"""Runner — executes Execution Agent tool invocations against Blender MCP.

Each invocation is mapped to a structured MCP command. If MCP is offline,
material ops fall back to the script-regeneration path. Geometry ops
without an MCP handler set a ``deferred`` flag and skip execution for now.
"""

from __future__ import annotations

import os
import tempfile
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from .trace import trace


@dataclass
class RunnerResult:
    invocations: List[Dict[str, Any]] = field(default_factory=list)
    applied: List[Dict[str, Any]] = field(default_factory=list)
    deferred: List[Dict[str, Any]] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    fallback_to_script: bool = False
    export_paths: List[str] = field(default_factory=list)


_MCP_TOOL_MAP = {
    "apply_pattern",
    "apply_color",
    "assign_region_material",
    "export_glb",
}

_GEOMETRY_TOOL_MAP = {
    "curve_wall",
    "offset_region",
    "split_region",
    "merge_region",
    "bevel_region",
    "extrude_region",
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


async def run_invocations(
    invocations: List[Dict[str, Any]],
    selection_payload: Optional[Dict[str, Any]] = None,
    project_name: str = "building",
    fallback_executor: Optional[Any] = None,
) -> RunnerResult:
    """Translate tool invocations into MCP commands, run them, return result.

    ``fallback_executor`` is an optional async callable that receives the
    raw invocations and the selection payload and runs the legacy
    script-regeneration path. Used only when MCP is offline.
    """
    result = RunnerResult(invocations=list(invocations))

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
        return result

    try:
        from blender.mcp_client import send_command
    except Exception as exc:  # pragma: no cover
        result.warnings.append(f"mcp_client import failed: {exc}")
        return result

    for inv in invocations:
        tool = inv.get("tool")
        args = inv.get("arguments") or {}
        if tool in _MCP_TOOL_MAP:
            ok, payload = _run_mcp_tool(tool, args, send_command)
            entry = trace(
                "runner.mcp",
                tool=tool,
                args=args,
                ok=ok,
                payload=payload,
            )
            (result.applied if ok else result.deferred).append(inv)
            if not ok:
                result.warnings.append(f"{tool} failed: {payload}")
            continue
        if tool in _GEOMETRY_TOOL_MAP:
            # Geometry tools require addon-side handlers that ship in a
            # later phase. Defer them so the orchestrator can emit a
            # clarifying note.
            result.deferred.append(inv)
            result.warnings.append(
                f"{tool} geometry op deferred — addon handler pending"
            )
            continue
        result.deferred.append(inv)
        result.warnings.append(f"unknown tool {tool!r}; deferred")

    return result


def _run_mcp_tool(
    tool: str,
    args: Dict[str, Any],
    send_command,
) -> Tuple[bool, Any]:
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
                "type": "set_object_pattern",
                "object": args.get("object"),
                "pattern": args.get("pattern"),
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
    return False, {"error": f"unsupported tool {tool!r}"}