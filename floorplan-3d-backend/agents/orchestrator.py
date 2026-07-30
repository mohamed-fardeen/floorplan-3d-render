"""Orchestrator — multi-agent coordinator.

Flow:

    user prompt
       │
       ▼
    Orchestrator classifies intent (design / geometry / mixed / clarify / reject)
       │
       ▼
    Invokes Design / Geometry agents → collects structured operations & tool calls
       │
       ▼
    Validates outputs (no free-form Blender code reaches Execution Agent)
       │
       ▼
    Execution Agent translates to Blender tool invocations
       │
       ▼
    Blender MCP or script-fallback pipeline runs the tools
       │
       ▼
    Trace entry recorded for every step
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .base import Agent, AgentRequest, AgentResponse
from .registry import AgentRegistry
from .trace import trace
from .validation import (
    validate_design_operations,
    validate_selection_present,
    validate_tool_calls,
)


@dataclass
class OrchestratorResult:
    intent: str
    invoked_agents: List[str] = field(default_factory=list)
    design_operations: List[Dict[str, Any]] = field(default_factory=list)
    geometry_tool_calls: List[Dict[str, Any]] = field(default_factory=list)
    execution_invocations: List[Dict[str, Any]] = field(default_factory=list)
    fallback_to_script: bool = False
    clarification: Optional[str] = None
    error: Optional[str] = None
    notes: List[str] = field(default_factory=list)
    trace_ids: List[str] = field(default_factory=list)


_DESIGN_HINTS = {"color", "colour", "pattern", "paint", "tint", "shade", "white", "navy", "sage"}
_GEOMETRY_HINTS = {"curve", "bevel", "extrude", "split", "merge", "offset", "round", "bend"}
_REJECT_HINTS = {"hello", "hi ", "thanks", "thank you", "who are you"}


class Orchestrator:
    def __init__(self, registry: AgentRegistry) -> None:
        self.registry = registry

    async def run(
        self,
        prompt: str,
        selection: Dict[str, Any],
        project_id: Optional[str] = None,
        conversation: Optional[List[Dict[str, Any]]] = None,
        available_patterns: Optional[List[str]] = None,
        available_materials: Optional[List[str]] = None,
    ) -> OrchestratorResult:
        prompt_low = (prompt or "").strip().lower()
        if not prompt_low:
            return self._reject("empty prompt", project_id)

        if any(h in prompt_low for h in _REJECT_HINTS) and len(prompt_low) < 30:
            return self._reject("small-talk / out-of-scope", project_id)

        # Decide intent.
        design_score = sum(1 for h in _DESIGN_HINTS if h in prompt_low)
        geometry_score = sum(1 for h in _GEOMETRY_HINTS if h in prompt_low)

        if design_score == 0 and geometry_score == 0:
            clarification = (
                "I can help with design (colors, patterns, materials) or geometry "
                "(curve, bevel, extrude, split, merge, offset). Which would you like?"
            )
            entry = trace("orchestrator.clarify", project_id=project_id, prompt=prompt, clarification=clarification)
            return OrchestratorResult(
                intent="clarify",
                clarification=clarification,
                trace_ids=[entry["id"]],
            )

        intent = (
            "mixed"
            if design_score > 0 and geometry_score > 0
            else "design"
            if design_score > 0
            else "geometry"
        )

        # Selection present?
        selection_mesh_names = [
            m.get("objectName") for m in (selection.get("meshRefs") or []) if m.get("objectName")
        ]
        if not selection_mesh_names:
            clarification = "Please select a region in the 3D viewport first."
            entry = trace(
                "orchestrator.clarify",
                project_id=project_id,
                prompt=prompt,
                reason="no selection",
                clarification=clarification,
            )
            return OrchestratorResult(
                intent="clarify",
                clarification=clarification,
                trace_ids=[entry["id"]],
            )

        invoked: List[str] = []
        result = OrchestratorResult(intent=intent, invoked_agents=invoked)

        # Build a common request for agents that need selection context.
        request_ctx = AgentRequest(
            prompt=prompt,
            selection_summary=selection,
            selection_mesh_names=selection_mesh_names,
            available_patterns=available_patterns or [],
            available_materials=available_materials or [],
            available_tools=[a.name for a in [self.registry.get(n) for n in ("design", "geometry", "execution")]],
            conversation=conversation or [],
            context={
                "face_indices": [
                    int(f.get("faceIndex"))
                    for f in (selection.get("faceRefs") or [])
                    if isinstance(f.get("faceIndex"), int)
                ],
            },
        )

        # 1. Design Agent (if applicable).
        design_response: Optional[AgentResponse] = None
        if intent in {"design", "mixed"}:
            design_agent = self.registry.get("design")
            invoked.append(design_agent.name)
            entry = trace(
                "agent.invoke",
                project_id=project_id,
                agent=design_agent.name,
                prompt=prompt,
                selection=selection_mesh_names,
            )
            result.trace_ids.append(entry["id"])
            design_response = await design_agent.run(request_ctx)
            entry = trace(
                "agent.result",
                project_id=project_id,
                agent=design_agent.name,
                operations=design_response.operations,
                notes=design_response.notes,
                error=design_response.error,
            )
            result.trace_ids.append(entry["id"])
            if not design_response.ok:
                result.error = f"design agent: {design_response.error}"
                return result
            op_errors = validate_design_operations(design_response.operations)
            if op_errors:
                result.error = "design validation: " + "; ".join(op_errors)
                entry = trace("agent.validation_failed", project_id=project_id, errors=op_errors)
                result.trace_ids.append(entry["id"])
                return result
            result.design_operations = design_response.operations
            result.notes.extend(design_response.notes)

        # 2. Geometry Agent (if applicable).
        geometry_response: Optional[AgentResponse] = None
        if intent in {"geometry", "mixed"}:
            geometry_agent = self.registry.get("geometry")
            invoked.append(geometry_agent.name)
            entry = trace(
                "agent.invoke",
                project_id=project_id,
                agent=geometry_agent.name,
                prompt=prompt,
                selection=selection_mesh_names,
            )
            result.trace_ids.append(entry["id"])
            geometry_response = await geometry_agent.run(request_ctx)
            entry = trace(
                "agent.result",
                project_id=project_id,
                agent=geometry_agent.name,
                tool_calls=geometry_response.tool_calls,
                notes=geometry_response.notes,
                error=geometry_response.error,
            )
            result.trace_ids.append(entry["id"])
            if not geometry_response.ok and geometry_response.needs_clarification:
                result.clarification = geometry_response.needs_clarification
                return result
            if not geometry_response.ok:
                result.error = f"geometry agent: {geometry_response.error}"
                return result
            tool_errors = validate_tool_calls(geometry_response.tool_calls)
            if tool_errors:
                result.error = "geometry validation: " + "; ".join(tool_errors)
                entry = trace("agent.validation_failed", project_id=project_id, errors=tool_errors)
                result.trace_ids.append(entry["id"])
                return result
            result.geometry_tool_calls = geometry_response.tool_calls
            result.notes.extend(geometry_response.notes)

        # 3. Execution Agent.
        execution_agent = self.registry.get("execution")
        invoked.append(execution_agent.name)
        exec_request = AgentRequest(
            prompt=prompt,
            selection_summary=selection,
            selection_mesh_names=selection_mesh_names,
            available_patterns=available_patterns or [],
            available_materials=available_materials or [],
            available_tools=[a.name for a in [self.registry.get(n) for n in ("design", "geometry", "execution")]],
            conversation=conversation or [],
            context={
                "design_operations": result.design_operations,
                "geometry_tool_calls": result.geometry_tool_calls,
                "face_indices": request_ctx.context.get("face_indices") or [],
            },
        )
        entry = trace(
            "agent.invoke",
            project_id=project_id,
            agent=execution_agent.name,
            design_ops=result.design_operations,
            geom_calls=result.geometry_tool_calls,
        )
        result.trace_ids.append(entry["id"])
        execution_response = await execution_agent.run(exec_request)
        entry = trace(
            "agent.result",
            project_id=project_id,
            agent=execution_agent.name,
            invocations=execution_response.tool_calls,
            notes=execution_response.notes,
        )
        result.trace_ids.append(entry["id"])
        result.execution_invocations = execution_response.tool_calls
        result.notes.extend(execution_response.notes)
        result.fallback_to_script = bool(execution_response.context_extra.get("fallback_to_script", False))

        entry = trace(
            "orchestrator.done",
            project_id=project_id,
            intent=intent,
            invoked=invoked,
            design_ops=len(result.design_operations),
            geometry_calls=len(result.geometry_tool_calls),
            invocations=len(result.execution_invocations),
        )
        result.trace_ids.append(entry["id"])
        return result

    def _reject(self, reason: str, project_id: Optional[str]) -> OrchestratorResult:
        entry = trace("orchestrator.reject", project_id=project_id, reason=reason)
        return OrchestratorResult(intent="reject", error=reason, trace_ids=[entry["id"]])