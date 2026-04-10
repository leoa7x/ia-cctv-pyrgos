from __future__ import annotations

import cv2
import numpy as np


class IPCameraStream:
    def __init__(self, url: str):
        self.url = url
        self._capture: cv2.VideoCapture | None = None

    def open(self) -> None:
        if not self.url:
            raise ValueError("No se definio la URL del stream IP.")
        self._capture = cv2.VideoCapture(self.url)
        if not self._capture.isOpened():
            raise RuntimeError(f"No se pudo abrir el stream: {self.url}")

    def read(self) -> np.ndarray | None:
        if self._capture is None:
            raise RuntimeError("El stream no ha sido abierto.")
        ok, frame = self._capture.read()
        if not ok:
            return None
        return frame

    def release(self) -> None:
        if self._capture is not None:
            self._capture.release()
            self._capture = None
