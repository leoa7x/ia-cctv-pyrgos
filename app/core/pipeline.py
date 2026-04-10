from __future__ import annotations

import time
from datetime import UTC, datetime

import cv2

from app.config import AppSettings
from app.detectors import NullDetector, RFDETRDetector
from app.runtime import get_runtime
from app.stream import IPCameraStream
from app.ui import OpenCVRenderer


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
            return RFDETRDetector(self.settings)
        raise ValueError(
            f"Backend de detector no soportado: {self.settings.detector_backend}"
        )

    def run(self) -> None:
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
                self.renderer.show(annotated)

                key = cv2.waitKey(1) & 0xFF
                if key in (27, ord("q")):
                    break
        except Exception as exc:
            self.runtime.camera_status.last_error = str(exc)
            raise
        finally:
            self.runtime.camera_status.connected = False
            self.stream.release()
            cv2.destroyAllWindows()
