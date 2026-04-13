import numpy as np

from app.config.settings import AppSettings
from app.detectors import NullDetector
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
    event_service = EventService(repository, track_confirmation_hits=1)
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


def test_live_detection_falls_back_to_null_detector_when_rfdetr_is_missing(monkeypatch):
    settings = AppSettings(detector_backend="rfdetr")
    repository = InMemoryEventRepository()
    event_service = EventService(repository)

    def fail_to_build(_settings):
        raise RuntimeError("RF-DETR no esta instalado.")

    monkeypatch.setattr("app.services.live_detection.RFDETRDetector", fail_to_build)

    service = LiveDetectionService(settings, event_service, camera_id="cam-1")

    assert isinstance(service._detector, NullDetector)
