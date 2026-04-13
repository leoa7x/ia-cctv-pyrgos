from __future__ import annotations

import os
import time

import cv2
import numpy as np


class IPCameraStream:
    def __init__(self, url: str):
        self.url = url
        self._capture: cv2.VideoCapture | None = None
        self._backend = cv2.CAP_FFMPEG if hasattr(cv2, "CAP_FFMPEG") else cv2.CAP_ANY

    def _create_capture(self) -> cv2.VideoCapture:
        # Prefer TCP for RTSP because the iPhone stream is more stable that way.
        os.environ.setdefault("OPENCV_FFMPEG_CAPTURE_OPTIONS", "rtsp_transport;tcp")
        capture = cv2.VideoCapture(self.url, self._backend)
        for prop_name, value in (
            ("CAP_PROP_BUFFERSIZE", 1),
            ("CAP_PROP_OPEN_TIMEOUT_MSEC", 5000),
            ("CAP_PROP_READ_TIMEOUT_MSEC", 5000),
        ):
            prop = getattr(cv2, prop_name, None)
            if prop is not None:
                capture.set(prop, value)
        return capture

    def _reopen(self) -> None:
        self.release()
        self._capture = self._create_capture()
        if not self._capture.isOpened():
            raise RuntimeError(f"No se pudo reabrir el stream: {self.url}")

    def open(self) -> None:
        if not self.url:
            raise ValueError("No se definio la URL del stream IP.")
        self._capture = self._create_capture()
        if not self._capture.isOpened():
            raise RuntimeError(f"No se pudo abrir el stream: {self.url}")

    def read(self) -> np.ndarray | None:
        if self._capture is None:
            raise RuntimeError("El stream no ha sido abierto.")
        for attempt in range(3):
            ok, frame = self._capture.read()
            if ok and frame is not None:
                return frame
            if attempt < 2:
                time.sleep(0.15)
                self._reopen()
        raise RuntimeError("No se pudo leer frame del stream IP tras varios reintentos.")

    def release(self) -> None:
        if self._capture is not None:
            self._capture.release()
            self._capture = None
