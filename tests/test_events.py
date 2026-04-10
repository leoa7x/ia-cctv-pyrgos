import numpy as np

from app.detectors.base import Detection
from app.repositories import InMemoryEventRepository
from app.services import EventService


def test_record_detections_creates_events():
    repository = InMemoryEventRepository()
    service = EventService(repository)
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
