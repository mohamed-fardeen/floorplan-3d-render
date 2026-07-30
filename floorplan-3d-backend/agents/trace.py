"""Structured agent trace logging."""

from __future__ import annotations

import json
import threading
import time
import uuid
from collections import deque
from typing import Any, Deque, Dict, List, Optional


class AgentTraceLog:
    """In-process ring buffer of agent-trace entries. Thread-safe."""

    def __init__(self, max_entries: int = 1000) -> None:
        self._entries: Deque[Dict[str, Any]] = deque(maxlen=max_entries)
        self._lock = threading.Lock()

    def record(self, entry: Dict[str, Any]) -> Dict[str, Any]:
        full = {
            "id": str(uuid.uuid4()),
            "ts": time.time(),
            **entry,
        }
        with self._lock:
            self._entries.append(full)
        return full

    def recent(self, project_id: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
        with self._lock:
            items = list(self._entries)
        if project_id is not None:
            items = [i for i in items if i.get("project_id") == project_id]
        return items[-limit:]


# Module-level singleton so any module can record without DI gymnastics.
TRACE_LOG = AgentTraceLog()


def trace(step: str, **fields: Any) -> Dict[str, Any]:
    return TRACE_LOG.record({"step": step, **fields})