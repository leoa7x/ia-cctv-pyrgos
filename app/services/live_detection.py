from __future__ import annotations

from dataclasses import dataclass
from threading import Lock
from warnings import warn

import numpy as np

from app.config import AppSettings
from app.detectors import NullDetector, RFDETRDetector
from app.detectors.base import Detection
from app.services import EventService


@dataclass(slots=True)
class DetectionSnapshot:
    detections: list[Detection]
    processed_frames: int = 0


class LiveDetectionService:
    def __init__(self, settings: AppSettings, event_service: EventService, camera_id: str):
        self.settings = settings
        self.event_service = event_service
        self.camera_id = camera_id
        self._detector = self._build_detector()
        self._lock = Lock()
        self._frame_count = 0
        self._last_snapshot = DetectionSnapshot(detections=[], processed_frames=0)
        self._last_signature: set[tuple[str, int, int, int, int]] = set()

    def _build_detector(self):
        if self.settings.detector_backend == "none":
            return NullDetector()
        if self.settings.detector_backend == "rfdetr":
            try:
                return RFDETRDetector(self.settings)
            except RuntimeError as exc:
                warn(
                    "RF-DETR no esta instalado. Se usa NullDetector hasta instalar el extra rfdetr.",
                    RuntimeWarning,
                    stacklevel=2,
                )
                return NullDetector()
        raise ValueError(
            f"Backend de detector no soportado: {self.settings.detector_backend}"
        )

    def process_frame(self, frame: np.ndarray) -> list[Detection]:
        with self._lock:
            self._frame_count += 1
            if self._frame_count % max(self.settings.detection_interval_frames, 1) != 0:
                return self._last_snapshot.detections

            detections = self._detector.predict(frame)
            filtered = self._dedupe(detections)
            self._last_snapshot = DetectionSnapshot(
                detections=filtered,
                processed_frames=self._frame_count,
            )
            if filtered:
                self.event_service.record_detections(
                    camera_id=self.camera_id,
                    frame=frame,
                    detections=filtered,
                    source=self.settings.detector_backend,
                )
            return filtered

    def latest(self) -> DetectionSnapshot:
        return self._last_snapshot

    def _dedupe(self, detections: list[Detection]) -> list[Detection]:
        filtered: list[Detection] = []
        new_signature: set[tuple[str, int, int, int, int]] = set()
        for detection in detections:
            signature = (
                detection.label,
                detection.x1 // 25,
                detection.y1 // 25,
                detection.x2 // 25,
                detection.y2 // 25,
            )
            if signature in self._last_signature or signature in new_signature:
                continue
            filtered.append(detection)
            new_signature.add(signature)
        self._last_signature = new_signature
        return filtered
