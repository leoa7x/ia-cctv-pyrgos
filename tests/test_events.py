import numpy as np
from datetime import UTC, datetime, timedelta

from app.detectors.base import Detection
from app.repositories import InMemoryEventRepository
from app.services import EventService


def test_record_detections_creates_events():
    repository = InMemoryEventRepository()
    service = EventService(repository, track_confirmation_hits=1)
    frame = np.zeros((720, 1280, 3), dtype=np.uint8)
    detections = [
        Detection(label="person", confidence=0.91, x1=10, y1=20, x2=100, y2=200),
        Detection(label="car", confidence=0.88, x1=50, y1=80, x2=220, y2=260),
    ]

    events = service.record_detections("cam-1", frame, detections)

    assert len(events) == 2
    assert events[0].camera_id == "cam-1"
    assert events[0].frame_width == 1280
    assert events[0].frame_height == 720
    stored = service.list_events(limit=10, camera_id="cam-1")
    assert len(stored) == 2


def test_analytics_summary_counts_events_by_label():
    repository = InMemoryEventRepository()
    service = EventService(repository, track_confirmation_hits=1)
    frame = np.zeros((720, 1280, 3), dtype=np.uint8)
    detections = [
        Detection(label="person", confidence=0.91, x1=10, y1=20, x2=100, y2=200),
        Detection(label="person", confidence=0.87, x1=260, y1=40, x2=360, y2=240),
        Detection(label="car", confidence=0.88, x1=50, y1=80, x2=220, y2=260),
    ]

    service.record_detections("cam-1", frame, detections)
    summary = service.analytics_summary(camera_id="cam-1", recent_window_minutes=10)

    assert summary.total_events == 3
    assert summary.counts_by_label["person"] == 2
    assert summary.counts_by_label["car"] == 1
    assert summary.recent_activity_count == 3
    assert summary.recent_counts_by_label["person"] == 2
    assert summary.recent_counts_by_label["car"] == 1
    assert summary.latest_event is not None


def test_record_detections_deduplicates_same_object_within_time_window():
    repository = InMemoryEventRepository()
    service = EventService(
        repository,
        track_ttl_seconds=8.0,
        track_match_iou=0.3,
        track_confirmation_hits=1,
    )
    frame = np.zeros((720, 1280, 3), dtype=np.uint8)
    detection = Detection(label="motorcycle", confidence=0.93, x1=100, y1=120, x2=220, y2=260)

    first = service.record_detections("cam-1", frame, [detection])
    second = service.record_detections("cam-1", frame, [detection])

    assert len(first) == 1
    assert second == []
    assert len(service.list_events(limit=10, camera_id="cam-1")) == 1


def test_record_detections_allows_same_object_after_dedup_window_expires():
    repository = InMemoryEventRepository()
    service = EventService(
        repository,
        track_ttl_seconds=3.0,
        track_match_iou=0.3,
        track_confirmation_hits=1,
    )
    frame = np.zeros((720, 1280, 3), dtype=np.uint8)
    detection = Detection(label="motorcycle", confidence=0.93, x1=100, y1=120, x2=220, y2=260)

    first = service.record_detections("cam-1", frame, [detection])
    service._active_tracks["cam-1"][0].last_seen_at = datetime.now(UTC) - timedelta(seconds=10)
    second = service.record_detections("cam-1", frame, [detection])

    assert len(second) == 1


def test_record_detections_keeps_same_track_when_bbox_jitters():
    repository = InMemoryEventRepository()
    service = EventService(
        repository,
        track_ttl_seconds=8.0,
        track_match_iou=0.2,
        track_confirmation_hits=1,
    )
    frame = np.zeros((720, 1280, 3), dtype=np.uint8)

    first = service.record_detections(
        "cam-1",
        frame,
        [Detection(label="motorcycle", confidence=0.93, x1=100, y1=120, x2=220, y2=260)],
    )
    second = service.record_detections(
        "cam-1",
        frame,
        [Detection(label="motorcycle", confidence=0.92, x1=108, y1=126, x2=228, y2=266)],
    )

    assert len(first) == 1
    assert second == []


def test_track_keeps_same_object_even_if_predicted_label_fluctuates():
    repository = InMemoryEventRepository()
    service = EventService(
        repository,
        track_ttl_seconds=8.0,
        track_match_iou=0.2,
        track_confirmation_hits=1,
    )
    frame = np.zeros((720, 1280, 3), dtype=np.uint8)

    first = service.record_detections(
        "cam-1",
        frame,
        [Detection(label="motorcycle", confidence=0.93, x1=100, y1=120, x2=220, y2=260)],
    )
    second = service.record_detections(
        "cam-1",
        frame,
        [Detection(label="car", confidence=0.92, x1=106, y1=124, x2=226, y2=264)],
    )
    third = service.record_detections(
        "cam-1",
        frame,
        [Detection(label="motorcycle", confidence=0.94, x1=109, y1=128, x2=229, y2=268)],
    )

    assert len(first) == 1
    assert second == []
    assert third == []
    assert len(service.list_events(limit=10, camera_id="cam-1")) == 1


def test_track_only_counts_after_confirmation_hits():
    repository = InMemoryEventRepository()
    service = EventService(repository, track_ttl_seconds=8.0, track_match_iou=0.2, track_confirmation_hits=3)
    frame = np.zeros((720, 1280, 3), dtype=np.uint8)
    detection = Detection(label="person", confidence=0.91, x1=100, y1=120, x2=220, y2=320)

    first = service.record_detections("cam-1", frame, [detection])
    second = service.record_detections("cam-1", frame, [detection])
    third = service.record_detections("cam-1", frame, [detection])

    assert first == []
    assert second == []
    assert len(third) == 1
