import numpy as np

from app.config.settings import AppSettings
from app.detectors.rfdetr_detector import RFDETRDetector


class StubResults:
    def __init__(self):
        self.xyxy = np.array([[1, 2, 10, 12]])
        self.class_id = np.array([84])
        self.confidence = np.array([0.91])


class StubModel:
    def predict(self, frame, threshold):
        return StubResults()


def test_rfdetr_detector_falls_back_to_class_id_label_for_out_of_range_ids():
    detector = RFDETRDetector.__new__(RFDETRDetector)
    detector.settings = AppSettings(
        detector_backend="rfdetr",
        confidence=0.2,
        target_classes=[],
    )
    detector._model = StubModel()
    detector._class_names = ["person", "car"]
    detector.last_raw_count = 0
    detector.last_filtered_count = 0
    detector.last_raw_labels = []

    detections = detector.predict(np.zeros((20, 20, 3), dtype=np.uint8))

    assert len(detections) == 1
    assert detections[0].label == "class_84"
    assert detector.last_raw_labels == ["class_84"]
    assert len(detector.last_raw_detections) == 1
    assert detector.last_raw_detections[0].label == "class_84"
