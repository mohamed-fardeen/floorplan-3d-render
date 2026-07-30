"""Common agent data structures.

Agents receive an ``AgentRequest`` carrying only the context they need. They
return an ``AgentResponse`` carrying structured operations that the
Orchestrator composes into a final ``DesignActionPlan``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class AgentRequest:
    """Input to an agent call. ``context`` is agent-specific."""

    prompt: str
    selection_summary: Dict[str, Any] = field(default_factory=dict)
    selection_mesh_names: List[str] = field(default_factory=list)
    available_patterns: List[str] = field(default_factory=list)
    available_materials: List[str] = field(default_factory=list)
    available_tools: List[str] = field(default_factory=list)
    scene_graph_summary: Dict[str, Any] = field(default_factory=dict)
    conversation: List[Dict[str, Any]] = field(default_factory=list)
    context: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentResponse:
    """Structured agent output. Always a list of operations + a status."""

    agent: str
    operations: List[Dict[str, Any]] = field(default_factory=list)
    tool_calls: List[Dict[str, Any]] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)
    needs_clarification: Optional[str] = None
    error: Optional[str] = None
    context_extra: Dict[str, Any] = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return self.error is None


class Agent:
    """Base class. Subclasses declare a name, a system prompt, and a ``run``."""

    name: str = "agent"

    def __init__(self, system_prompt: str) -> None:
        self.system_prompt = system_prompt

    def system_message(self) -> str:
        return self.system_prompt

    async def run(self, request: AgentRequest) -> AgentResponse:  # pragma: no cover
        raise NotImplementedError