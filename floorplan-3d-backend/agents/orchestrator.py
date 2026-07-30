"""Orchestrator — multi-agent coordinator (LLM-backed).

Flow:

    user prompt
       │
       ▼
    OrchestratorLLM classifies intent (design / geometry / mixed / clarify / reject)
       │
       ▼
    Invokes Design / Geometry agents → structured operations / tool calls
       │
       ▼
    Validates outputs (no free-form Blender code reaches Execution Agent)
       │
       ▼
    Construction Rules Engine
       │
       ▼
    Execution Agent translates to Blender tool invocations
       │
       ▼
    Runner dispatches via MCP / script fallback
       │
       ▼
    Trace entry recorded for every step

The Orchestrator never calls an LLM directly; it delegates to
``OrchestratorLLM`` so providers can be swapped without changes here.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .base import Agent, AgentRequest, AgentResponse
from .llm.base import LLMProvider, ProviderUnavailable
from .llm_agents import DesignAgent, GeometryAgent, OrchestratorLLM, SummariserAgent
from .memory import MEMORY_STORE, MemoryTurn
from .registry import AgentRegistry
from .rules import validate_invocations, validate_selection
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
    rule_report: Optional[Dict[str, Any]] = None
    explain: Dict[str, Any] = field(default_factory=dict)
    recommendations: List[str] = field(default_factory=list)


class Orchestrator:
    def __init__(
        self,
        registry: AgentRegistry,
        provider: Optional[LLMProvider] = None,
        orchestrator_llm: Optional[OrchestratorLLM] = None,
        summariser: Optional[SummariserAgent] = None,
    ) -> None:
        self.registry = registry
        self.provider = provider
        self.orchestrator_llm = orchestrator_llm or OrchestratorLLM(provider)
        self.summariser = summariser or SummariserAgent(provider)
        # Propagate provider to any LLM-capable agents already registered.
        for agent in [self.registry.get(n) for n in ("design", "geometry") if n in self.registry.names()]:
            if hasattr(agent, "set_provider"):
                agent.set_provider(provider)  # type: ignore[attr-defined]

    def set_provider(self, provider: Optional[LLMProvider]) -> None:
        self.provider = provider
        self.orchestrator_llm.set_provider(provider)
        self.summariser.set_provider(provider)
        for agent in [self.registry.get(n) for n in self.registry.names()]:
            if hasattr(agent, "set_provider"):
                agent.set_provider(provider)  # type: ignore[attr-defined]

    async def run(
        self,
        prompt: str,
        selection: Dict[str, Any],
        project_id: Optional[str] = None,
        conversation: Optional[List[Dict[str, Any]]] = None,
        available_patterns: Optional[List[str]] = None,
        available_materials: Optional[List[str]] = None,
        available_tools: Optional[List[str]] = None,
        viewport_image_b64: Optional[str] = None,
    ) -> OrchestratorResult:
        conversation = conversation or []
        selection_mesh_names = [
            m.get("objectName") for m in (selection.get("meshRefs") or []) if m.get("objectName")
        ]

        # Record into memory.
        mem = MEMORY_STORE.get(project_id or "unsaved")
        mem.record_turn(MemoryTurn(role="user", content=prompt))

        # Classify intent (LLM-backed with heuristic fallback).
        classification = await self.orchestrator_llm.classify(
            prompt,
            selection_present=bool(selection_mesh_names),
            available_tools=available_tools or self.registry.names(),
        )
        intent = classification.get("intent", "clarify")
        invoked: List[str] = list(classification.get("invoked_agents") or [])

        trace_entry = trace(
            "orchestrator.classify",
            project_id=project_id,
            intent=intent,
            invoked=invoked,
            reason=classification.get("reason"),
            clarification=classification.get("clarification"),
        )

        result = OrchestratorResult(
            intent=intent,
            invoked_agents=invoked,
            explain={
                "intent": intent,
                "reason": classification.get("reason"),
                "invoked_agents": invoked,
            },
        )
        result.trace_ids.append(trace_entry["id"])

        if intent == "reject":
            result.error = classification.get("reason") or "out of scope"
            return result

        if intent == "clarify":
            result.clarification = classification.get("clarification") or "Could you clarify?"
            return result

        if not selection_mesh_names:
            result.intent = "clarify"
            result.clarification = "Please select a region in the 3D viewport first."
            return result

        # Build request context once.
        request_ctx = AgentRequest(
            prompt=prompt,
            selection_summary=selection,
            selection_mesh_names=selection_mesh_names,
            available_patterns=available_patterns or [],
            available_materials=available_materials or [],
            available_tools=available_tools or self.registry.names(),
            conversation=conversation,
            context={
                "face_indices": [
                    int(f.get("faceIndex"))
                    for f in (selection.get("faceRefs") or [])
                    if isinstance(f.get("faceIndex"), int)
                ],
                "design_intent": mem.design_intent,
                "images": [],
            },
        )
        if viewport_image_b64:
            request_ctx.context["images"] = [{
                "data": viewport_image_b64,
                "mime_type": "image/png",
            }]

        design_response: Optional[AgentResponse] = None
        geometry_response: Optional[AgentResponse] = None

        # Design Agent.
        if intent in {"design", "mixed"} and "design" in self.registry.names():
            design_agent = self.registry.get("design")
            invoked.append(design_agent.name) if design_agent.name not in invoked else None
            entry = trace("agent.invoke", project_id=project_id, agent=design_agent.name, prompt=prompt)
            result.trace_ids.append(entry["id"])
            design_response = await design_agent.run(request_ctx)
            result.explain.setdefault("design", {
                "operations": design_response.operations,
                "reasoning": design_response.context_extra.get("reasoning", ""),
                "source": design_response.context_extra.get("source"),
            })
            result.recommendations.extend(design_response.context_extra.get("recommendations") or [])
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
                return result
            result.design_operations = design_response.operations
            result.notes.extend(design_response.notes)

        # Geometry Agent.
        if intent in {"geometry", "mixed"} and "geometry" in self.registry.names():
            geometry_agent = self.registry.get("geometry")
            invoked.append(geometry_agent.name) if geometry_agent.name not in invoked else None
            entry = trace("agent.invoke", project_id=project_id, agent=geometry_agent.name, prompt=prompt)
            result.trace_ids.append(entry["id"])
            geometry_response = await geometry_agent.run(request_ctx)
            result.explain.setdefault("geometry", {
                "tool_calls": geometry_response.tool_calls,
                "reasoning": geometry_response.context_extra.get("reasoning", ""),
                "source": geometry_response.context_extra.get("source"),
            })
            result.recommendations.extend(geometry_response.context_extra.get("recommendations") or [])
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
                return result
            result.geometry_tool_calls = geometry_response.tool_calls
            result.notes.extend(geometry_response.notes)

        # Execution Agent.
        if "execution" in self.registry.names():
            execution_agent = self.registry.get("execution")
            invoked.append(execution_agent.name) if execution_agent.name not in invoked else None
            exec_request = AgentRequest(
                prompt=prompt,
                selection_summary=selection,
                selection_mesh_names=selection_mesh_names,
                available_patterns=available_patterns or [],
                available_materials=available_materials or [],
                available_tools=available_tools or self.registry.names(),
                conversation=conversation,
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
            result.execution_invocations = execution_response.tool_calls
            result.notes.extend(execution_response.notes)
            result.fallback_to_script = bool(execution_response.context_extra.get("fallback_to_script", False))
            entry = trace(
                "agent.result",
                project_id=project_id,
                agent=execution_agent.name,
                invocations=execution_response.tool_calls,
                notes=execution_response.notes,
            )
            result.trace_ids.append(entry["id"])

        # Construction Rules.
        rule_report = validate_invocations(result.execution_invocations, selection)
        result.rule_report = rule_report.to_dict()
        if not rule_report.ok:
            errors = [v for v in rule_report.violations if v.severity == "error"]
            result.error = "rule_violation: " + "; ".join(v.message for v in errors)
            entry = trace("rules.failed", project_id=project_id, errors=[v.message for v in errors])
            result.trace_ids.append(entry["id"])
            return result
        entry = trace(
            "rules.passed",
            project_id=project_id,
            warnings=[v.message for v in rule_report.violations if v.severity == "warning"],
        )
        result.trace_ids.append(entry["id"])

        # Update memory.
        for op in result.design_operations:
            mat = op.get("value") if op.get("type") == "set_color" else op.get("pattern") or op.get("preset")
            if mat:
                mem.record_material(str(mat))
        for call in result.geometry_tool_calls:
            mem.record_tool(call.get("tool", ""))
        mem.update_intent(classification.get("reason", ""))
        mem.record_turn(MemoryTurn(role="agent", content="; ".join(result.notes) or intent, intent=intent))
        for sel in selection_mesh_names:
            mem.record_selection(sel)

        # Summarise on overflow.
        if MEMORY_STORE.should_summarise(project_id or "unsaved"):
            asyncio.create_task(self._maybe_summarise(project_id or "unsaved", mem))

        # Done.
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
        result.explain["invoked_agents"] = invoked
        result.explain["expected_result"] = (
            f"{len(result.execution_invocations)} tool call(s) will be dispatched via "
            f"{'MCP' if not result.fallback_to_script else 'script fallback'}."
        )
        return result

    async def _maybe_summarise(self, project_id: str, mem) -> None:
        if mem.summarising:
            return
        mem.summarising = True
        try:
            summary = await self.summariser.summarise(
                turns=[{"role": t.role, "content": t.content} for t in mem.turns],
                previous_summary=mem.summary,
            )
            mem.summary = summary.get("summary", mem.summary)
        except Exception as exc:  # pragma: no cover
            trace("memory.summarise_failed", project_id=project_id, error=str(exc))
        finally:
            mem.summarising = False


__all__ = ["Orchestrator", "OrchestratorResult"]