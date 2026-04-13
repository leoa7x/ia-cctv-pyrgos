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


def test_rfdetr_detector_maps_known_coco_ids_using_dictionary_mapping():
    detector = RFDETRDetector.__new__(RFDETRDetector)
    detector.settings = AppSettings(
        detector_backend="rfdetr",
        confidence=0.2,
        target_classes=[],
    )
    detector._model = StubModel()
    detector._class_names = {84: "book"}
    detector.last_raw_count = 0
    detector.last_filtered_count = 0
    detector.last_raw_labels = []
    detector.last_raw_detections = []

    detections = detector.predict(np.zeros((20, 20, 3), dtype=np.uint8))

    assert len(detections) == 1
    assert detections[0].label == "book"
    assert detector.last_raw_labels == ["book"]


def test_rfdetr_detector_filters_implausible_small_vehicle_boxes():
    detector = RFDETRDetector.__new__(RFDETRDetector)
    detector.settings = AppSettings(
        detector_backend="rfdetr",
        confidence=0.2,
        target_classes=[],
    )
    detector._model = None

    keep = detector._passes_domain_filters(
        detection=type("D", (), {"label": "car", "confidence": 0.8, "x1": 100, "y1": 200, "x2": 260, "y2": 360})(),
        frame_width=1280,
        frame_height=720,
    )
    drop = detector._passes_domain_filters(
        detection=type("D", (), {"label": "car", "confidence": 0.8, "x1": 10, "y1": 20, "x2": 70, "y2": 60})(),
        frame_width=1280,
        frame_height=720,
    )

    assert keep is True
    assert drop is False


def test_rfdetr_detector_filters_low_confidence_truck_false_positives():
    detector = RFDETRDetector.__new__(RFDETRDetector)
    detector.settings = AppSettings(
        detector_backend="rfdetr",
        confidence=0.2,
        target_classes=[],
    )
    detector._model = None

    drop = detector._passes_domain_filters(
        detection=type("D", (), {"label": "truck", "confidence": 0.31, "x1": 120, "y1": 240, "x2": 520, "y2": 540})(),
        frame_width=1280,
        frame_height=720,
    )
    keep = detector._passes_domain_filters(
        detection=type("D", (), {"label": "truck", "confidence": 0.72, "x1": 120, "y1": 240, "x2": 520, "y2": 540})(),
        frame_width=1280,
        frame_height=720,
    )

    assert drop is False
    assert keep is True
