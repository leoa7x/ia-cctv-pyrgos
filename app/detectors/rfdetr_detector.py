from __future__ import annotations

from typing import Any

import numpy as np

from app.config import AppSettings
from app.detectors.base import Detection


class RFDETRDetector:
    def __init__(self, settings: AppSettings):
        self.settings = settings
        self._model: Any | None = None
        self._class_names: dict[int, str] | None = None
        self.last_raw_count: int = 0
        self.last_filtered_count: int = 0
        self.last_raw_labels: list[str] = []
        self.last_raw_detections: list[Detection] = []
        self._load_model()

    def _load_model(self) -> None:
        try:
            from rfdetr import (
                RFDETRLarge,
                RFDETRMedium,
                RFDETRNano,
                RFDETRSmall,
            )
        except ImportError as exc:
            raise RuntimeError(
                "RF-DETR no esta instalado. Instala el extra del proyecto o el paquete rfdetr."
            ) from exc

        variants = {
            "nano": RFDETRNano,
            "small": RFDETRSmall,
            "medium": RFDETRMedium,
            "large": RFDETRLarge,
        }
        model_cls = variants.get(self.settings.model_variant)
        if model_cls is None:
            raise ValueError(f"Variante de modelo no soportada: {self.settings.model_variant}")

        self._model = model_cls()
        try:
            from rfdetr.assets.coco_classes import COCO_CLASSES

            self._class_names = dict(COCO_CLASSES)
        except Exception:
            self._class_names = None

    def predict(self, frame: np.ndarray) -> list[Detection]:
        if self._model is None:
            return []

        results = self._model.predict(frame, threshold=self.settings.confidence)
        detections: list[Detection] = []
        frame_height, frame_width = frame.shape[:2]
        xyxy = getattr(results, "xyxy", None)
        class_ids = getattr(results, "class_id", None)
        confidences = getattr(results, "confidence", None)

        if xyxy is None or class_ids is None or confidences is None:
            self.last_raw_count = 0
            self.last_filtered_count = 0
            self.last_raw_labels = []
            self.last_raw_detections = []
            return detections

        raw_labels: list[str] = []
        raw_detections: list[Detection] = []
        for box, class_id, confidence in zip(xyxy, class_ids, confidences):
            class_id_int = int(class_id)
            label = f"class_{class_id_int}"
            if self._class_names and class_id_int in self._class_names:
                candidate = str(self._class_names[class_id_int]).strip()
                if candidate:
                    label = candidate
            raw_labels.append(label)
            x1, y1, x2, y2 = [int(v) for v in box]
            raw_detection = Detection(
                label=label,
                confidence=float(confidence),
                x1=x1,
                y1=y1,
                x2=x2,
                y2=y2,
            )
            raw_detection = self._normalize_domain_label(
                detection=raw_detection,
                frame_width=frame_width,
                frame_height=frame_height,
            )
            raw_detections.append(raw_detection)
            if (
                self.settings.target_classes
                and raw_detection.label not in self.settings.target_classes
            ):
                continue
            if not self._passes_domain_filters(
                detection=raw_detection,
                frame_width=frame_width,
                frame_height=frame_height,
            ):
                continue
            detections.append(raw_detection)
        self.last_raw_count = len(raw_labels)
        self.last_filtered_count = len(detections)
        self.last_raw_labels = raw_labels[:8]
        self.last_raw_detections = raw_detections
        return detections

    def _normalize_domain_label(
        self,
        detection: Detection,
        frame_width: int,
        frame_height: int,
    ) -> Detection:
        if detection.label != "motorcycle":
            return detection

        width = max(detection.x2 - detection.x1, 1)
        height = max(detection.y2 - detection.y1, 1)
        area_ratio = (width * height) / max(frame_width * frame_height, 1)
        aspect_ratio = width / height

        # In this CCTV angle, distant cars are sometimes mislabeled as motorcycles.
        if aspect_ratio >= 1.8 and area_ratio >= 0.02:
            return Detection(
                label="car",
                confidence=detection.confidence,
                x1=detection.x1,
                y1=detection.y1,
                x2=detection.x2,
                y2=detection.y2,
            )
        return detection

    def _passes_domain_filters(
        self,
        detection: Detection,
        frame_width: int,
        frame_height: int,
    ) -> bool:
        width = max(detection.x2 - detection.x1, 1)
        height = max(detection.y2 - detection.y1, 1)
        area_ratio = (width * height) / max(frame_width * frame_height, 1)
        top_ratio = detection.y1 / max(frame_height, 1)
        bottom_ratio = detection.y2 / max(frame_height, 1)

        if detection.label == "person":
            if height / max(frame_height, 1) < 0.08 or bottom_ratio < 0.22:
                return False
            return detection.confidence >= max(self.settings.confidence, 0.28)

        if detection.label == "motorcycle":
            if area_ratio < 0.005:
                return False
            return detection.confidence >= max(self.settings.confidence, 0.30)

        if detection.label == "dog":
            if area_ratio < 0.003:
                return False
            return detection.confidence >= max(self.settings.confidence, 0.28)

        if detection.label == "cat":
            if area_ratio < 0.0025:
                return False
            return detection.confidence >= max(self.settings.confidence, 0.28)

        if detection.label == "car":
            if area_ratio < 0.015 or bottom_ratio < 0.26:
                return False
            return detection.confidence >= max(self.settings.confidence, 0.42)

        if detection.label == "bus":
            if area_ratio < 0.03 or top_ratio < 0.05 or bottom_ratio < 0.4:
                return False
            return detection.confidence >= max(self.settings.confidence, 0.55)

        if detection.label == "truck":
            if area_ratio < 0.025 or top_ratio < 0.05 or bottom_ratio < 0.4:
                return False
            return detection.confidence >= max(self.settings.confidence, 0.58)

        return True
