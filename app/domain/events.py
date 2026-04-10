from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime


@dataclass(slots=True)
class DetectionEvent:
    camera_id: str
    label: str
    confidence: float
    bbox: tuple[int, int, int, int]
    frame_width: int
    frame_height: int
    source: str = "rfdetr"
    event_id: str = ""
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass(slots=True)
class CameraStatus:
    camera_id: str
    stream_url: str
    connected: bool
    last_frame_at: datetime | None = None
    last_error: str = ""
