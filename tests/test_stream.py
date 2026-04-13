import numpy as np

from app.stream.ip_camera import IPCameraStream
from app.stream.ip_camera import FFmpegMJPEGStream


class _FakeCapture:
    def __init__(self, opened: bool = True, reads=None):
        self._opened = opened
        self._reads = list(reads or [])
        self.released = False

    def isOpened(self) -> bool:
        return self._opened

    def read(self):
        if self._reads:
            return self._reads.pop(0)
        return False, None

    def set(self, *_args):
        return True

    def release(self) -> None:
        self.released = True


def test_ip_camera_stream_retries_and_recovers(monkeypatch):
    ok_frame = np.zeros((10, 10, 3), dtype=np.uint8)
    captures = iter(
        [
            _FakeCapture(reads=[(False, None)]),
            _FakeCapture(reads=[(True, ok_frame)]),
        ]
    )

    stream = IPCameraStream("rtsp://example")
    monkeypatch.setattr(stream, "_create_capture", lambda: next(captures))
    monkeypatch.setattr("app.stream.ip_camera.time.sleep", lambda *_args: None)

    stream.open()
    frame = stream.read()

    assert frame is not None
    assert frame.shape == (10, 10, 3)


def test_ip_camera_stream_raises_after_exhausting_retries(monkeypatch):
    captures = iter(
        [
            _FakeCapture(reads=[(False, None)]),
            _FakeCapture(reads=[(False, None)]),
            _FakeCapture(reads=[(False, None)]),
        ]
    )

    stream = IPCameraStream("rtsp://example")
    monkeypatch.setattr(stream, "_create_capture", lambda: next(captures))
    monkeypatch.setattr("app.stream.ip_camera.time.sleep", lambda *_args: None)

    stream.open()

    try:
        stream.read()
    except RuntimeError as exc:
        assert "No se pudo leer frame del stream IP" in str(exc)
    else:
        raise AssertionError("Se esperaba RuntimeError cuando el stream no se recupera.")


def test_ffmpeg_stream_uses_configured_binary():
    stream = FFmpegMJPEGStream(
        "rtsp://example/stream2",
        ffmpeg_path=r"C:\ffmpeg\bin\ffmpeg.exe",
    )

    command = stream._build_command()

    assert command[0] == r"C:\ffmpeg\bin\ffmpeg.exe"
    assert "-rtsp_transport" in command
    assert "tcp" in command
    assert "rtsp://example/stream2" in command
