"""In-process pub/sub for streaming design progress to the browser via SSE."""

from __future__ import annotations

import asyncio
import json
import time
from typing import Any, AsyncIterator, Dict, List


class ProgressBroker:
    """Fan-out broker — each subscriber gets its own asyncio.Queue."""

    def __init__(self) -> None:
        self._subscribers: List[asyncio.Queue] = []

    def subscribe(self) -> asyncio.Queue:
        queue: asyncio.Queue = asyncio.Queue(maxsize=256)
        self._subscribers.append(queue)
        return queue

    def unsubscribe(self, queue: asyncio.Queue) -> None:
        if queue in self._subscribers:
            self._subscribers.remove(queue)

    def publish(self, event: Dict[str, Any]) -> None:
        payload = json.dumps({**event, "ts": time.time()})
        for queue in list(self._subscribers):
            try:
                queue.put_nowait(payload)
            except asyncio.QueueFull:
                # Drop the event for slow subscribers; never block the producer.
                pass


broker = ProgressBroker()


def emit(stage: str, message: str, **extra: Any) -> None:
    broker.publish({"stage": stage, "message": message, **extra})


async def stream() -> AsyncIterator[str]:
    """Yield SSE-formatted events until the client disconnects."""
    queue = broker.subscribe()
    try:
        # Initial comment to flush headers promptly.
        yield ": connected\n\n"
        while True:
            payload = await queue.get()
            yield f"data: {payload}\n\n"
    finally:
        broker.unsubscribe(queue)