from __future__ import annotations

import os
import shutil
import subprocess
import time
from concurrent.futures import Future, ThreadPoolExecutor
from concurrent.futures import TimeoutError as FutureTimeoutError
from threading import Event, Lock, Thread

import cv2
import numpy as np


class IPCameraStream:
    def __init__(self, url: str):
        self.url = url
        self._capture: cv2.VideoCapture | None = None
        self._backend = cv2.CAP_FFMPEG if hasattr(cv2, "CAP_FFMPEG") else cv2.CAP_ANY
        self._executor: ThreadPoolExecutor | None = None
        self._read_future: Future | None = None
        self._latest_frame: np.ndarray | None = None
        self._frame_sequence = 0
        self._lock = Lock()

    @property
    def frame_sequence(self) -> int:
        with self._lock:
            return self._frame_sequence

    def _create_capture(self) -> cv2.VideoCapture:
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

    def _submit_read(self) -> None:
        if self._capture is None or self._executor is None:
            return
        if self._read_future is None:
            self._read_future = self._executor.submit(self._capture.read)

    def _consume_future(self, timeout: float = 0.0):
        if self._read_future is None:
            return None
        try:
            ok, frame = self._read_future.result(timeout=timeout)
        except FutureTimeoutError:
            return None
        self._read_future = None
        return ok, frame

    def _reopen(self) -> None:
        if self._capture is not None:
            self._capture.release()
        self._capture = self._create_capture()
        if not self._capture.isOpened():
            raise RuntimeError(f"No se pudo reabrir el stream: {self.url}")
        self._read_future = None
        self._submit_read()

    def open(self) -> None:
        if not self.url:
            raise ValueError("No se definio la URL del stream IP.")
        self._capture = self._create_capture()
        if not self._capture.isOpened():
            raise RuntimeError(f"No se pudo abrir el stream: {self.url}")
        if self._executor is None:
            self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="pyrgos-rtsp")
        self._read_future = None
        self._submit_read()

    def read(self) -> np.ndarray | None:
        if self._capture is None:
            raise RuntimeError("El stream no ha sido abierto.")
        self._submit_read()
        result = self._consume_future(timeout=0.01)
        if result is not None:
            ok, frame = result
            if ok and frame is not None:
                with self._lock:
                    self._latest_frame = frame.copy()
                    self._frame_sequence += 1
                self._submit_read()
                return frame
            for attempt in range(2):
                if attempt > 0:
                    time.sleep(0.15)
                self._reopen()
                result = self._consume_future(timeout=0.2)
                if result is not None:
                    ok, frame = result
                    if ok and frame is not None:
                        with self._lock:
                            self._latest_frame = frame.copy()
                            self._frame_sequence += 1
                        self._submit_read()
                        return frame
            if self._latest_frame is not None:
                with self._lock:
                    return self._latest_frame.copy()
            raise RuntimeError("No se pudo leer frame del stream IP tras varios reintentos.")
        with self._lock:
            if self._latest_frame is None:
                return None
            return self._latest_frame.copy()

    def release(self) -> None:
        future = self._read_future
        self._read_future = None
        if future is not None:
            future.cancel()
        if self._capture is not None:
            self._capture.release()
            self._capture = None
        if self._executor is not None:
            self._executor.shutdown(wait=False, cancel_futures=True)
            self._executor = None


class FFmpegMJPEGStream:
    def __init__(self, url: str, ffmpeg_path: str = ""):
        self.url = url
        self.ffmpeg_path = ffmpeg_path
        self._process: subprocess.Popen | None = None
        self._reader_thread: Thread | None = None
        self._stop_event = Event()
        self._latest_frame: np.ndarray | None = None
        self._frame_sequence = 0
        self._lock = Lock()
        self._last_error = ""

    @property
    def frame_sequence(self) -> int:
        with self._lock:
            return self._frame_sequence

    def _resolve_ffmpeg(self) -> str:
        if self.ffmpeg_path:
            return self.ffmpeg_path
        discovered = shutil.which("ffmpeg")
        if discovered:
            return discovered
        fallback = (
            r"C:\Program Files\WindowsApps\Microsoft.PowerAutomateDesktop_11.2603.154.0_x64__8wekyb3d8bbwe"
            r"\dotnet\x64\ffmpeg\ffmpeg.exe"
        )
        if os.path.exists(fallback):
            return fallback
        raise RuntimeError(
            "No se encontro ffmpeg. Define PYRGOS_FFMPEG_PATH o instala ffmpeg en PATH."
        )

    def _build_command(self) -> list[str]:
        return [
            self._resolve_ffmpeg(),
            "-hide_banner",
            "-loglevel",
            "warning",
            "-rtsp_transport",
            "tcp",
            "-fflags",
            "nobuffer",
            "-flags",
            "low_delay",
            "-i",
            self.url,
            "-an",
            "-sn",
            "-c:v",
            "mjpeg",
            "-q:v",
            "5",
            "-f",
            "image2pipe",
            "-",
        ]

    def _reader_loop(self) -> None:
        assert self._process is not None and self._process.stdout is not None
        buffer = bytearray()
        while not self._stop_event.is_set():
            chunk = self._process.stdout.read(4096)
            if not chunk:
                if self._process.poll() is not None:
                    self._last_error = "ffmpeg termino mientras leia el stream."
                    break
                time.sleep(0.05)
                continue
            buffer.extend(chunk)
            while True:
                start = buffer.find(b"\xff\xd8")
                if start < 0:
                    if len(buffer) > 1024 * 1024:
                        buffer.clear()
                    break
                end = buffer.find(b"\xff\xd9", start + 2)
                if end < 0:
                    if start > 0:
                        del buffer[:start]
                    break
                frame_bytes = bytes(buffer[start : end + 2])
                del buffer[: end + 2]
                image = cv2.imdecode(np.frombuffer(frame_bytes, dtype=np.uint8), cv2.IMREAD_COLOR)
                if image is None:
                    continue
                with self._lock:
                    self._latest_frame = image
                    self._frame_sequence += 1

    def open(self) -> None:
        if not self.url:
            raise ValueError("No se definio la URL del stream IP.")
        command = self._build_command()
        self._stop_event.clear()
        self._latest_frame = None
        self._frame_sequence = 0
        self._last_error = ""
        self._process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            stdin=subprocess.DEVNULL,
            bufsize=0,
        )
        self._reader_thread = Thread(target=self._reader_loop, daemon=True, name="pyrgos-ffmpeg")
        self._reader_thread.start()

    def read(self) -> np.ndarray | None:
        deadline = time.time() + 5.0
        while time.time() < deadline:
            with self._lock:
                if self._latest_frame is not None:
                    return self._latest_frame.copy()
            if self._process is not None and self._process.poll() is not None:
                break
            time.sleep(0.03)
        if self._last_error:
            raise RuntimeError(self._last_error)
        raise RuntimeError("ffmpeg no produjo frames del stream en el tiempo esperado.")

    def release(self) -> None:
        self._stop_event.set()
        if self._process is not None and self._process.poll() is None:
            self._process.terminate()
            try:
                self._process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                self._process.kill()
        self._process = None
        if self._reader_thread is not None and self._reader_thread.is_alive():
            self._reader_thread.join(timeout=1)
        self._reader_thread = None
