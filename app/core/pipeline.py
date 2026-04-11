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
    video_fps: float
    inference_fps: float | None
    raw_detection_count: int
    filtered_detection_count: int
    raw_detection_labels: list[str]
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
        prev_inference_time: float | None = None
        smoothed_video_fps = 0.0
        smoothed_inference_fps: float | None = None

        try:
            while True:
                frame = self.stream.read()
                if frame is None:
                    raise RuntimeError("El stream se cerro o no devolvio mas frames.")
                self.runtime.camera_status.last_frame_at = datetime.now(UTC)

                frame_index += 1
                detections = []
                inference_fps: float | None = None
                if frame_index % self.settings.frame_skip == 0:
                    inference_started = time.perf_counter()
                    detections = self.detector.predict(frame)
                    inference_elapsed = max(time.perf_counter() - inference_started, 1e-6)
                    inference_fps = 1.0 / inference_elapsed
                    if prev_inference_time is None:
                        smoothed_inference_fps = inference_fps
                    else:
                        smoothed_inference_fps = (
                            (smoothed_inference_fps or inference_fps) * 0.8
                            + inference_fps * 0.2
                        )
                    prev_inference_time = time.perf_counter()
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
                video_fps = 1.0 / max(now - prev_time, 1e-6)
                prev_time = now
                if smoothed_video_fps == 0.0:
                    smoothed_video_fps = video_fps
                else:
                    smoothed_video_fps = smoothed_video_fps * 0.85 + video_fps * 0.15

                annotated = self.renderer.render(frame, detections, fps=smoothed_video_fps)
                events = self.runtime.event_service.list_events(limit=1)
                latest_event = events[0] if events else None
                raw_detection_count = getattr(self.detector, "last_raw_count", len(detections))
                filtered_detection_count = getattr(
                    self.detector, "last_filtered_count", len(detections)
                )
                raw_detection_labels = list(getattr(self.detector, "last_raw_labels", []))
                yield PipelineSnapshot(
                    frame=annotated,
                    detections=detections,
                    video_fps=smoothed_video_fps,
                    inference_fps=smoothed_inference_fps,
                    raw_detection_count=raw_detection_count,
                    filtered_detection_count=filtered_detection_count,
                    raw_detection_labels=raw_detection_labels,
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
