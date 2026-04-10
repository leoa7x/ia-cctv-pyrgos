from __future__ import annotations

from uuid import uuid4

import numpy as np

from app.detectors.base import Detection
from app.domain import DetectionEvent
from app.repositories import InMemoryEventRepository


class EventService:
    def __init__(self, repository: InMemoryEventRepository):
        self.repository = repository

    def record_detections(
        self,
        camera_id: str,
        frame: np.ndarray,
        detections: list[Detection],
        source: str = "rfdetr",
    ) -> list[DetectionEvent]:
        frame_height, frame_width = frame.shape[:2]
        events: list[DetectionEvent] = []
        for detection in detections:
            event = DetectionEvent(
                event_id=str(uuid4()),
                camera_id=camera_id,
                label=detection.label,
                confidence=detection.confidence,
                bbox=(detection.x1, detection.y1, detection.x2, detection.y2),
                frame_width=frame_width,
                frame_height=frame_height,
                source=source,
            )
            self.repository.add(event)
            events.append(event)
        return events

    def list_events(self, limit: int = 50, camera_id: str | None = None) -> list[DetectionEvent]:
        return self.repository.list(limit=limit, camera_id=camera_id)
