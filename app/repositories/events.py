from __future__ import annotations

from collections import deque
from threading import Lock

from app.domain import DetectionEvent


class InMemoryEventRepository:
    def __init__(self, max_events: int = 1000):
        self._events: deque[DetectionEvent] = deque(maxlen=max_events)
        self._lock = Lock()

    def add(self, event: DetectionEvent) -> DetectionEvent:
        with self._lock:
            self._events.appendleft(event)
        return event

    def list(self, limit: int = 50, camera_id: str | None = None) -> list[DetectionEvent]:
        with self._lock:
            events = list(self._events)
        if camera_id:
            events = [event for event in events if event.camera_id == camera_id]
        return events[:limit]
