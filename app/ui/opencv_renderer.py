from __future__ import annotations

import cv2
import numpy as np

from app.detectors.base import Detection


class OpenCVRenderer:
    def __init__(self, window_name: str, show_fps: bool = True):
        self.window_name = window_name
        self.show_fps = show_fps

    def render(self, frame: np.ndarray, detections: list[Detection], fps: float | None = None) -> np.ndarray:
        annotated = frame.copy()
        for det in detections:
            cv2.rectangle(annotated, (det.x1, det.y1), (det.x2, det.y2), (0, 200, 255), 2)
            label = f"{det.label} {det.confidence:.2f}"
            cv2.putText(
                annotated,
                label,
                (det.x1, max(20, det.y1 - 8)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.55,
                (0, 200, 255),
                2,
                cv2.LINE_AA,
            )

        if self.show_fps and fps is not None:
            cv2.putText(
                annotated,
                f"FPS: {fps:.1f}",
                (16, 28),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (40, 255, 120),
                2,
                cv2.LINE_AA,
            )
        return annotated

    def show(self, frame: np.ndarray) -> None:
        cv2.imshow(self.window_name, frame)
