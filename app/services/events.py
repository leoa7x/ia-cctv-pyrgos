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


@dataclass(slots=True)
class ActiveTrack:
    camera_id: str
    dominant_label: str
    label_counts: Counter[str]
    bbox: tuple[int, int, int, int]
    confidence: float
    last_seen_at: datetime
    hits: int
    confirmed: bool = False


class EventService:
    def __init__(
        self,
        repository: EventRepository,
        track_ttl_seconds: float = 8.0,
        track_match_iou: float = 0.3,
        track_center_distance_ratio: float = 0.12,
        track_confirmation_hits: int = 3,
    ):
        self.repository = repository
        self.track_ttl_seconds = track_ttl_seconds
        self.track_match_iou = track_match_iou
        self.track_center_distance_ratio = track_center_distance_ratio
        self.track_confirmation_hits = track_confirmation_hits
        self._active_tracks: dict[str, list[ActiveTrack]] = {}
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
        now = datetime.now(UTC)
        for detection in detections:
            event = self._track_detection(
                camera_id=camera_id,
                detection=detection,
                frame_width=frame_width,
                frame_height=frame_height,
                seen_at=now,
            )
            if event is None:
                continue
            event.source = source
            self.repository.add(event)
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

    def _track_detection(
        self,
        camera_id: str,
        detection: Detection,
        frame_width: int,
        frame_height: int,
        seen_at: datetime,
    ) -> DetectionEvent | None:
        bbox = (detection.x1, detection.y1, detection.x2, detection.y2)
        with self._lock:
            self._prune_tracks(seen_at)
            tracks = self._active_tracks.get(camera_id, [])
            for track in tracks:
                iou = self._bbox_iou(track.bbox, bbox)
                center_distance_ratio = self._center_distance_ratio(
                    track.bbox,
                    bbox,
                    frame_width,
                    frame_height,
                )
                same_label_match = track.dominant_label == detection.label and (
                    iou >= self.track_match_iou
                    or center_distance_ratio <= self.track_center_distance_ratio
                )
                cross_label_match = track.dominant_label != detection.label and iou >= max(
                    self.track_match_iou,
                    0.5,
                )
                if same_label_match or cross_label_match:
                    track.label_counts[detection.label] += 1
                    track.dominant_label = self._dominant_label(track.label_counts)
                    track.bbox = bbox
                    track.confidence = max(track.confidence, detection.confidence)
                    track.last_seen_at = seen_at
                    track.hits += 1
                    if not track.confirmed and track.hits >= self.track_confirmation_hits:
                        track.confirmed = True
                        return DetectionEvent(
                            event_id=str(uuid4()),
                            camera_id=camera_id,
                            label=track.dominant_label,
                            confidence=track.confidence,
                            bbox=bbox,
                            frame_width=frame_width,
                            frame_height=frame_height,
                            created_at=seen_at,
                        )
                    return None
            track = ActiveTrack(
                camera_id=camera_id,
                dominant_label=detection.label,
                label_counts=Counter({detection.label: 1}),
                bbox=bbox,
                confidence=detection.confidence,
                last_seen_at=seen_at,
                hits=1,
            )
            self._active_tracks.setdefault(camera_id, []).append(track)
        if self.track_confirmation_hits <= 1:
            track.confirmed = True
            return DetectionEvent(
                event_id=str(uuid4()),
                camera_id=camera_id,
                label=track.dominant_label,
                confidence=detection.confidence,
                bbox=bbox,
                frame_width=frame_width,
                frame_height=frame_height,
                created_at=seen_at,
            )
        return None

    def _prune_tracks(self, now: datetime) -> None:
        cutoff = now - timedelta(seconds=self.track_ttl_seconds)
        for camera_id, tracks in list(self._active_tracks.items()):
            kept = [track for track in tracks if track.last_seen_at >= cutoff]
            if kept:
                self._active_tracks[camera_id] = kept
            else:
                self._active_tracks.pop(camera_id, None)

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

    @staticmethod
    def _center_distance_ratio(
        box_a: tuple[int, int, int, int],
        box_b: tuple[int, int, int, int],
        frame_width: int,
        frame_height: int,
    ) -> float:
        ax = (box_a[0] + box_a[2]) / 2
        ay = (box_a[1] + box_a[3]) / 2
        bx = (box_b[0] + box_b[2]) / 2
        by = (box_b[1] + box_b[3]) / 2
        dx = ax - bx
        dy = ay - by
        diagonal = max((frame_width**2 + frame_height**2) ** 0.5, 1.0)
        return ((dx * dx + dy * dy) ** 0.5) / diagonal

    @staticmethod
    def _dominant_label(label_counts: Counter[str]) -> str:
        return sorted(label_counts.items(), key=lambda item: (-item[1], item[0]))[0][0]
