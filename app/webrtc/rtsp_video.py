from __future__ import annotations

import asyncio
from datetime import UTC, datetime

import cv2

from app.ui import OpenCVRenderer


class RTSPCamera:
    def __init__(self, stream_url: str, runtime=None):
        self.stream_url = stream_url
        self.runtime = runtime
        self.cap: cv2.VideoCapture | None = None

    def open(self) -> None:
        if self.cap is None:
            backend = cv2.CAP_FFMPEG if hasattr(cv2, "CAP_FFMPEG") else cv2.CAP_ANY
            self.cap = cv2.VideoCapture(self.stream_url, backend)
        if not self.cap.isOpened():
            if self.runtime is not None:
                self.runtime.camera_status.connected = False
                self.runtime.camera_status.last_error = (
                    "No se pudo abrir el stream RTSP para WebRTC."
                )
            raise RuntimeError("No se pudo abrir el stream RTSP para WebRTC.")

    def read(self):
        self.open()
        ok, frame = self.cap.read()
        if ok and frame is not None:
            return self._update_runtime(frame)
        self.cap.release()
        backend = cv2.CAP_FFMPEG if hasattr(cv2, "CAP_FFMPEG") else cv2.CAP_ANY
        self.cap = cv2.VideoCapture(self.stream_url, backend)
        ok, frame = self.cap.read()
        if not ok or frame is None:
            if self.runtime is not None:
                self.runtime.camera_status.connected = False
                self.runtime.camera_status.last_error = (
                    "No se pudo leer frame del stream RTSP para WebRTC."
                )
            raise RuntimeError("No se pudo leer frame del stream RTSP para WebRTC.")
        return self._update_runtime(frame)

    def close(self) -> None:
        if self.cap is not None:
            self.cap.release()
            self.cap = None
        if self.runtime is not None:
            self.runtime.camera_status.connected = False

    def _update_runtime(self, frame):
        if self.runtime is None:
            return frame
        self.runtime.camera_status.connected = True
        self.runtime.camera_status.last_error = ""
        self.runtime.camera_status.last_frame_at = datetime.now(UTC)
        detections = self.runtime.live_detection.process_frame(frame)
        renderer = OpenCVRenderer(window_name="webrtc", show_fps=False)
        return renderer.render(frame, detections, fps=None)


def build_webrtc_video_track(stream_url: str, runtime=None):
    try:
        from aiortc import VideoStreamTrack
        from av import VideoFrame
    except ImportError as exc:
        raise RuntimeError(
            "WebRTC no esta instalado. Instala aiortc y av en este entorno."
        ) from exc

    class RTSPVideoTrack(VideoStreamTrack):
        def __init__(self, url: str):
            super().__init__()
            self.camera = RTSPCamera(url, runtime=runtime)

        async def recv(self):
            pts, time_base = await self.next_timestamp()
            try:
                frame = await asyncio.to_thread(self.camera.read)
            except Exception as exc:
                if runtime is not None:
                    runtime.camera_status.connected = False
                    runtime.camera_status.last_error = str(exc)
                raise
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            video_frame = VideoFrame.from_ndarray(rgb, format="rgb24")
            video_frame.pts = pts
            video_frame.time_base = time_base
            return video_frame

        def stop(self) -> None:
            self.camera.close()
            super().stop()

    return RTSPVideoTrack(stream_url)
