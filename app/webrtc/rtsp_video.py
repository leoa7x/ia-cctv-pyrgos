from __future__ import annotations

import asyncio
from datetime import UTC, datetime

import cv2


class RTSPCamera:
    def __init__(self, stream_url: str, runtime=None):
        self.stream_url = stream_url
        self.runtime = runtime
        self.cap: cv2.VideoCapture | None = None

    def open(self) -> None:
        if self.cap is None:
            self.cap = cv2.VideoCapture(self.stream_url)
        if not self.cap.isOpened():
            raise RuntimeError("No se pudo abrir el stream RTSP para WebRTC.")

    def read(self):
        self.open()
        ok, frame = self.cap.read()
        if ok and frame is not None:
            self._update_runtime(frame)
            return frame
        self.cap.release()
        self.cap = cv2.VideoCapture(self.stream_url)
        ok, frame = self.cap.read()
        if not ok or frame is None:
            raise RuntimeError("No se pudo leer frame del stream RTSP para WebRTC.")
        self._update_runtime(frame)
        return frame

    def close(self) -> None:
        if self.cap is not None:
            self.cap.release()
            self.cap = None
        if self.runtime is not None:
            self.runtime.camera_status.connected = False

    def _update_runtime(self, frame) -> None:
        if self.runtime is None:
            return
        self.runtime.camera_status.connected = True
        self.runtime.camera_status.last_error = ""
        self.runtime.camera_status.last_frame_at = datetime.now(UTC)
        self.runtime.live_detection.process_frame(frame)


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
            frame = await asyncio.to_thread(self.camera.read)
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            video_frame = VideoFrame.from_ndarray(rgb, format="rgb24")
            video_frame.pts = pts
            video_frame.time_base = time_base
            return video_frame

        def stop(self) -> None:
            self.camera.close()
            super().stop()

    return RTSPVideoTrack(stream_url)
