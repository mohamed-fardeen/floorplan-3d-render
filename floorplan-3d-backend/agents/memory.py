"""Project memory — bounded per-project context for the LLM agents.

Responsibilities:
- Hold the last N turns of conversation per project.
- Track recent tools, materials, selections, and design intent.
- Produce a structured summary when the conversation grows past a
  threshold (delegated to the LLM via ``SummariserAgent``).

The memory is in-memory for now; future phases will persist it to SQLite.
"""

from __future__ import annotations

import threading
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Any, Deque, Dict, List, Optional


@dataclass
class MemoryTurn:
    role: str  # "user" | "agent"
    content: str
    intent: Optional[str] = None
    ts: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ProjectMemory:
    project_id: str
    turns: Deque[MemoryTurn] = field(default_factory=lambda: deque(maxlen=64))
    recent_tools: Deque[str] = field(default_factory=lambda: deque(maxlen=32))
    recent_materials: Deque[str] = field(default_factory=lambda: deque(maxlen=32))
    active_selections: Deque[str] = field(default_factory=lambda: deque(maxlen=16))
    design_intent: str = ""
    summary: str = ""
    summarising: bool = False
    last_summary_ts: float = 0.0

    def record_turn(self, turn: MemoryTurn) -> None:
        self.turns.append(turn)

    def record_tool(self, tool_name: str) -> None:
        self.recent_tools.append(tool_name)

    def record_material(self, material_id: str) -> None:
        self.recent_materials.append(material_id)

    def record_selection(self, object_name: str) -> None:
        self.active_selections.append(object_name)

    def update_intent(self, text: str) -> None:
        self.design_intent = text

    def to_llm_context(self) -> Dict[str, Any]:
        return {
            "project_id": self.project_id,
            "design_intent": self.design_intent,
            "summary": self.summary,
            "active_selections": list(self.active_selections),
            "recent_tools": list(self.recent_tools),
            "recent_materials": list(self.recent_materials),
            "recent_turn_count": len(self.turns),
        }


class MemoryStore:
    def __init__(self, summary_threshold: int = 12) -> None:
        self._projects: Dict[str, ProjectMemory] = {}
        self._lock = threading.Lock()
        self.summary_threshold = summary_threshold

    def get(self, project_id: str) -> ProjectMemory:
        with self._lock:
            if project_id not in self._projects:
                self._projects[project_id] = ProjectMemory(project_id=project_id)
            return self._projects[project_id]

    def all_projects(self) -> List[str]:
        with self._lock:
            return list(self._projects.keys())

    def should_summarise(self, project_id: str) -> bool:
        mem = self.get(project_id)
        return len(mem.turns) >= self.summary_threshold and not mem.summarising


MEMORY_STORE = MemoryStore()


__all__ = ["MemoryStore", "MemoryTurn", "ProjectMemory", "MEMORY_STORE"]