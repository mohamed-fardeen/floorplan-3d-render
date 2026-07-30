"""Central agent registry — pluggable, lazy-loaded.

New agents (Cost, Structural, Client Presentation, …) can be registered
without touching the orchestrator.
"""

from __future__ import annotations

from typing import Dict, List, Type

from .base import Agent


class AgentRegistry:
    def __init__(self) -> None:
        self._agents: Dict[str, Agent] = {}

    def register(self, agent: Agent) -> None:
        self._agents[agent.name] = agent

    def get(self, name: str) -> Agent:
        if name not in self._agents:
            raise KeyError(f"agent not registered: {name!r}")
        return self._agents[name]

    def names(self) -> List[str]:
        return list(self._agents.keys())


def default_registry() -> AgentRegistry:
    """Build the default registry with Design, Geometry, and Execution agents.

    Design + Geometry agents are LLM-backed (with rule-based fallback).
    Pass an ``LLMProvider`` to enable LLM planning.
    """
    from .llm_agents import DesignAgent, GeometryAgent
    from .execution_agent import ExecutionAgent

    reg = AgentRegistry()
    reg.register(DesignAgent())
    reg.register(GeometryAgent())
    reg.register(ExecutionAgent())
    return reg