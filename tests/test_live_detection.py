import numpy as np

from app.config.settings import AppSettings
from app.detectors.base import Detection
from app.repositories import InMemoryEventRepository
from app.services.events import EventService
from app.services.live_detection import LiveDetectionService


class StubDetector:
    def __init__(self, detections):
        self.detections = detections

    def predict(self, frame):
        return self.detections


def test_live_detection_records_events_on_interval():
    settings = AppSettings(detector_backend="none", detection_interval_frames=2)
    repository = InMemoryEventRepository()
    event_service = EventService(repository)
    service = LiveDetectionService(settings, event_service, camera_id="cam-1")
    service._detector = StubDetector(
        [Detection(label="person", confidence=0.93, x1=1, y1=2, x2=10, y2=12)]
    )
    frame = np.zeros((100, 120, 3), dtype=np.uint8)

    first = service.process_frame(frame)
    second = service.process_frame(frame)

    assert first == []
    assert len(second) == 1
    stored = event_service.list_events(limit=10, camera_id="cam-1")
    assert len(stored) == 1
