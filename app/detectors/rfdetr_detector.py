from __future__ import annotations

from typing import Any

import numpy as np

from app.config import AppSettings
from app.detectors.base import Detection


class RFDETRDetector:
    def __init__(self, settings: AppSettings):
        self.settings = settings
        self._model: Any | None = None
        self._class_names: list[str] | None = None
        self.last_raw_count: int = 0
        self.last_filtered_count: int = 0
        self.last_raw_labels: list[str] = []
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

            self._class_names = list(COCO_CLASSES)
        except Exception:
            self._class_names = None

    def predict(self, frame: np.ndarray) -> list[Detection]:
        if self._model is None:
            return []

        results = self._model.predict(frame, threshold=self.settings.confidence)
        detections: list[Detection] = []
        xyxy = getattr(results, "xyxy", None)
        class_ids = getattr(results, "class_id", None)
        confidences = getattr(results, "confidence", None)

        if xyxy is None or class_ids is None or confidences is None:
            self.last_raw_count = 0
            self.last_filtered_count = 0
            self.last_raw_labels = []
            return detections

        raw_labels: list[str] = []
        for box, class_id, confidence in zip(xyxy, class_ids, confidences):
            label = str(class_id)
            if self._class_names and int(class_id) < len(self._class_names):
                label = self._class_names[int(class_id)]
            raw_labels.append(label)
            if self.settings.target_classes and label not in self.settings.target_classes:
                continue
            x1, y1, x2, y2 = [int(v) for v in box]
            detections.append(
                Detection(
                    label=label,
                    confidence=float(confidence),
                    x1=x1,
                    y1=y1,
                    x2=x2,
                    y2=y2,
                )
            )
        self.last_raw_count = len(raw_labels)
        self.last_filtered_count = len(detections)
        self.last_raw_labels = raw_labels[:8]
        return detections
