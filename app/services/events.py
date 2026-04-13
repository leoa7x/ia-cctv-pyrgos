from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from threading import Lock
from uuid import uuid4

import numpy as np

from app.detectors.base import Detection
from app.domain import DetectionEvent
from app.repositories import EventRepository


@dataclass(slots=True)
class AnalyticsSummary:
    total_events: int
    counts_by_label: dict[str, int]
    recent_counts_by_label: dict[str, int]
    recent_activity_count: int
    recent_window_minutes: int
    latest_event: DetectionEvent | None


class EventService:
    def __init__(
        self,
        repository: EventRepository,
        dedup_seconds: float = 3.0,
        match_iou: float = 0.5,
    ):
        self.repository = repository
        self.dedup_seconds = dedup_seconds
        self.match_iou = match_iou
        self._recent_events: dict[str, list[DetectionEvent]] = {}
        self._lock = Lock()

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
            if self._is_duplicate(camera_id=camera_id, detection=detection):
                continue
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
            self._remember_event(event)
            events.append(event)
        return events

    def list_events(self, limit: int = 50, camera_id: str | None = None) -> list[DetectionEvent]:
        return self.repository.list(limit=limit, camera_id=camera_id)

    def analytics_summary(
        self,
        camera_id: str | None = None,
        recent_window_minutes: int = 10,
    ) -> AnalyticsSummary:
        events = self.repository.list(limit=1000, camera_id=camera_id)
        counts_by_label = dict(Counter(event.label for event in events))
        cutoff = datetime.now(UTC) - timedelta(minutes=recent_window_minutes)
        recent_events = [event for event in events if event.created_at >= cutoff]
        recent_activity_count = len(recent_events)
        recent_counts_by_label = dict(Counter(event.label for event in recent_events))
        latest_event = events[0] if events else None
        return AnalyticsSummary(
            total_events=len(events),
            counts_by_label=counts_by_label,
            recent_counts_by_label=recent_counts_by_label,
            recent_activity_count=recent_activity_count,
            recent_window_minutes=recent_window_minutes,
            latest_event=latest_event,
        )

    def _is_duplicate(self, camera_id: str, detection: Detection) -> bool:
        now = datetime.now(UTC)
        with self._lock:
            self._prune_recent(now)
            recent_events = self._recent_events.get(camera_id, [])
            for event in recent_events:
                if event.label != detection.label:
                    continue
                if self._bbox_iou(
                    event.bbox,
                    (detection.x1, detection.y1, detection.x2, detection.y2),
                ) >= self.match_iou:
                    return True
        return False

    def _remember_event(self, event: DetectionEvent) -> None:
        with self._lock:
            self._prune_recent(event.created_at)
            self._recent_events.setdefault(event.camera_id, []).append(event)

    def _prune_recent(self, now: datetime) -> None:
        cutoff = now - timedelta(seconds=self.dedup_seconds)
        for camera_id, events in list(self._recent_events.items()):
            kept = [event for event in events if event.created_at >= cutoff]
            if kept:
                self._recent_events[camera_id] = kept
            else:
                self._recent_events.pop(camera_id, None)

    @staticmethod
    def _bbox_iou(box_a: tuple[int, int, int, int], box_b: tuple[int, int, int, int]) -> float:
        ax1, ay1, ax2, ay2 = box_a
        bx1, by1, bx2, by2 = box_b
        inter_x1 = max(ax1, bx1)
        inter_y1 = max(ay1, by1)
        inter_x2 = min(ax2, bx2)
        inter_y2 = min(ay2, by2)
        inter_w = max(0, inter_x2 - inter_x1)
        inter_h = max(0, inter_y2 - inter_y1)
        inter_area = inter_w * inter_h
        if inter_area == 0:
            return 0.0
        area_a = max(0, ax2 - ax1) * max(0, ay2 - ay1)
        area_b = max(0, bx2 - bx1) * max(0, by2 - by1)
        union = area_a + area_b - inter_area
        if union <= 0:
            return 0.0
        return inter_area / union
