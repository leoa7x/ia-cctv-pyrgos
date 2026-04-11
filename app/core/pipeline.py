from __future__ import annotations

import time
from dataclasses import dataclass
from datetime import UTC, datetime
from threading import Event
from warnings import warn

import cv2
import numpy as np

from app.config import AppSettings
from app.detectors.base import Detection
from app.detectors import NullDetector, RFDETRDetector
from app.runtime import get_runtime
from app.stream import IPCameraStream
from app.ui import OpenCVRenderer


@dataclass(slots=True)
class PipelineSnapshot:
    frame: np.ndarray
    detections: list[Detection]
    fps: float
    processed_frames: int
    event_count: int
    latest_event_label: str
    latest_event_confidence: float | None


class PyrgosPipeline:
    def __init__(self, settings: AppSettings):
        self.settings = settings
        self.stream = IPCameraStream(settings.stream_url)
        self.detector = self._build_detector()
        self.renderer = OpenCVRenderer(settings.window_name, show_fps=settings.show_fps)
        self.runtime = get_runtime()

    def _build_detector(self):
        if self.settings.detector_backend == "none":
            return NullDetector()
        if self.settings.detector_backend == "rfdetr":
            try:
                return RFDETRDetector(self.settings)
            except RuntimeError:
                warn(
                    "RF-DETR no esta instalado. Se usa NullDetector hasta instalar el extra rfdetr.",
                    RuntimeWarning,
                    stacklevel=2,
                )
                return NullDetector()
        raise ValueError(
            f"Backend de detector no soportado: {self.settings.detector_backend}"
        )

    def iter_snapshots(self, stop_event: Event | None = None):
        self.stream.open()
        self.runtime.camera_status.connected = True
        self.runtime.camera_status.last_error = ""
        frame_index = 0
        prev_time = time.perf_counter()

        try:
            while True:
                frame = self.stream.read()
                if frame is None:
                    raise RuntimeError("El stream se cerro o no devolvio mas frames.")
                self.runtime.camera_status.last_frame_at = datetime.now(UTC)

                frame_index += 1
                detections = []
                if frame_index % self.settings.frame_skip == 0:
                    detections = self.detector.predict(frame)
                    if detections:
                        backend = (
                            self.settings.detector_backend
                            if self.settings.detector_backend != "none"
                            else "stream-only"
                        )
                        self.runtime.event_service.record_detections(
                            camera_id=self.runtime.camera_status.camera_id,
                            frame=frame,
                            detections=detections,
                            source=backend,
                        )

                now = time.perf_counter()
                fps = 1.0 / max(now - prev_time, 1e-6)
                prev_time = now

                annotated = self.renderer.render(frame, detections, fps=fps)
                events = self.runtime.event_service.list_events(limit=1)
                latest_event = events[0] if events else None
                yield PipelineSnapshot(
                    frame=annotated,
                    detections=detections,
                    fps=fps,
                    processed_frames=frame_index,
                    event_count=len(self.runtime.event_service.list_events(limit=500)),
                    latest_event_label=latest_event.label if latest_event else "-",
                    latest_event_confidence=latest_event.confidence if latest_event else None,
                )
                if stop_event is not None and stop_event.is_set():
                    break
        except Exception as exc:
            self.runtime.camera_status.last_error = str(exc)
            raise
        finally:
            self.runtime.camera_status.connected = False
            self.stream.release()

    def run(self) -> None:
        stop_event = Event()
        try:
            for snapshot in self.iter_snapshots(stop_event):
                self.renderer.show(snapshot.frame)
                key = cv2.waitKey(1) & 0xFF
                if key in (27, ord("q")):
                    break
        finally:
            cv2.destroyAllWindows()
