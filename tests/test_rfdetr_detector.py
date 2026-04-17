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


def test_rfdetr_detector_accepts_distant_but_large_car_box():
    detector = RFDETRDetector.__new__(RFDETRDetector)
    detector.settings = AppSettings(
        detector_backend="rfdetr",
        confidence=0.2,
        target_classes=[],
    )
    detector._model = None

    keep = detector._passes_domain_filters(
        detection=type("D", (), {"label": "car", "confidence": 0.95, "x1": 117, "y1": 28, "x2": 301, "y2": 106})(),
        frame_width=640,
        frame_height=360,
    )

    assert keep is True


def test_rfdetr_detector_rejects_high_horizon_person_box():
    detector = RFDETRDetector.__new__(RFDETRDetector)
    detector.settings = AppSettings(
        detector_backend="rfdetr",
        confidence=0.2,
        target_classes=[],
    )
    detector._model = None

    drop = detector._passes_domain_filters(
        detection=type("D", (), {"label": "person", "confidence": 0.46, "x1": 371, "y1": 22, "x2": 410, "y2": 71})(),
        frame_width=640,
        frame_height=360,
    )

    assert drop is False


def test_rfdetr_detector_accepts_lower_person_box():
    detector = RFDETRDetector.__new__(RFDETRDetector)
    detector.settings = AppSettings(
        detector_backend="rfdetr",
        confidence=0.2,
        target_classes=[],
    )
    detector._model = None

    keep = detector._passes_domain_filters(
        detection=type("D", (), {"label": "person", "confidence": 0.51, "x1": 53, "y1": 46, "x2": 106, "y2": 91})(),
        frame_width=640,
        frame_height=360,
    )

    assert keep is True


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


def test_rfdetr_detector_accepts_reasonable_dog_detection():
    detector = RFDETRDetector.__new__(RFDETRDetector)
    detector.settings = AppSettings(
        detector_backend="rfdetr",
        confidence=0.2,
        target_classes=[],
    )
    detector._model = None

    keep = detector._passes_domain_filters(
        detection=type("D", (), {"label": "dog", "confidence": 0.44, "x1": 180, "y1": 250, "x2": 320, "y2": 430})(),
        frame_width=1280,
        frame_height=720,
    )

    assert keep is True


def test_rfdetr_detector_rejects_tiny_cat_detection():
    detector = RFDETRDetector.__new__(RFDETRDetector)
    detector.settings = AppSettings(
        detector_backend="rfdetr",
        confidence=0.2,
        target_classes=[],
    )
    detector._model = None

    drop = detector._passes_domain_filters(
        detection=type("D", (), {"label": "cat", "confidence": 0.44, "x1": 10, "y1": 10, "x2": 35, "y2": 35})(),
        frame_width=1280,
        frame_height=720,
    )

    assert drop is False


def test_rfdetr_detector_relabels_wide_motorcycle_box_as_car():
    detector = RFDETRDetector.__new__(RFDETRDetector)
    relabeled = detector._normalize_domain_label(
        detection=type(
            "D",
            (),
            {"label": "motorcycle", "confidence": 0.81, "x1": 100, "y1": 40, "x2": 280, "y2": 120},
        )(),
        frame_width=640,
        frame_height=360,
    )

    assert relabeled.label == "car"


def test_rfdetr_detector_keeps_compact_motorcycle_box_as_motorcycle():
    detector = RFDETRDetector.__new__(RFDETRDetector)
    kept = detector._normalize_domain_label(
        detection=type(
            "D",
            (),
            {"label": "motorcycle", "confidence": 0.81, "x1": 334, "y1": 23, "x2": 413, "y2": 90},
        )(),
        frame_width=640,
        frame_height=360,
    )

    assert kept.label == "motorcycle"
