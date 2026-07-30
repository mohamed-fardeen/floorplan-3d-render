"""Execution Agent — dispatches validated tool calls to the Blender MCP layer.

The Execution Agent owns the boundary between the agent system and Blender.
It receives validated design operations + tool calls and produces a list
of structured ``tool_invocations`` that the Execution layer runs.

This agent never writes Blender Python directly. If an operation is not
covered by the registered tool library, it sets ``fallback_to_script: true``
so the orchestrator can route through the legacy script path.
"""

from __future__ import annotations

from typing import Any, Dict, List

from .base import Agent, AgentRequest, AgentResponse
from .prompts import EXECUTION_AGENT_PROMPT
from .tools import TOOL_LIBRARY, validate_tool_call


class ExecutionAgent(Agent):
    name = "execution"

    def __init__(self) -> None:
        super().__init__(EXECUTION_AGENT_PROMPT)
        self._available_tools = [t.name for t in TOOL_LIBRARY]

    async def run(self, request: AgentRequest) -> AgentResponse:
        tool_invocations: List[Dict[str, Any]] = []
        fallback = False
        notes: List[str] = []

        # Design operations → material tool invocations.
        for idx, op in enumerate(request.context.get("design_operations", []) or []):
            inv = self._design_op_to_invocation(op, request, op_index=idx)
            if inv is None:
                notes.append(f"op#{idx} unmapped: {op}")
                continue
            errs = validate_tool_call(inv)
            if errs:
                notes.append(f"op#{idx} invalid: {'; '.join(errs)}")
                continue
            tool_invocations.append(inv)

        # Geometry tool calls pass through with provenance.
        for idx, call in enumerate(request.context.get("geometry_tool_calls", []) or []):
            if not isinstance(call, dict):
                continue
            tool = call.get("tool")
            if tool not in self._available_tools:
                fallback = True
                notes.append(f"geometry tool {tool!r} unsupported; falling back to script")
                continue
            errs = validate_tool_call(call)
            if errs:
                notes.append(f"geom#{idx} invalid: {'; '.join(errs)}")
                continue
            tool_invocations.append(
                {
                    "tool": tool,
                    "arguments": call.get("arguments") or {},
                    "operation_id": f"geom_{idx}",
                }
            )

        if not tool_invocations:
            notes.append("no tool invocations produced")

        return AgentResponse(
            agent=self.name,
            tool_calls=tool_invocations,
            notes=notes,
            context_extra={"fallback_to_script": fallback, "invocations": tool_invocations},
        )

    @staticmethod
    def _design_op_to_invocation(
        op: Dict[str, Any],
        request: AgentRequest,
        op_index: int,
    ) -> Dict[str, Any] | None:
        if not isinstance(op, dict):
            return None
        op_type = op.get("type")
        target = request.selection_mesh_names[0] if request.selection_mesh_names else None
        if target is None:
            return None
        if op_type == "set_color":
            return {
                "tool": "apply_color",
                "arguments": {"object": target, "color": op.get("value") or "#FFFFFF"},
                "operation_id": f"op_{op_index}",
            }
        if op_type == "apply_pattern":
            return {
                "tool": "apply_pattern",
                "arguments": {"object": target, "pattern": op.get("pattern") or "none"},
                "operation_id": f"op_{op_index}",
            }
        if op_type == "set_material_preset":
            return {
                "tool": "assign_region_material",
                "arguments": {
                    "object": target,
                    "material_name": f"Preset_{op.get('preset') or 'custom'}",
                    "face_indices": request.context.get("face_indices") or [],
                },
                "operation_id": f"op_{op_index}",
            }
        return None