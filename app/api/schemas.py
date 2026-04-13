from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class HealthResponse(BaseModel):
    status: str = "ok"
    app_name: str = "IA CCTV PYRGOS"


class CameraResponse(BaseModel):
    camera_id: str
    stream_url: str
    connected: bool
    last_error: str = ""
    last_frame_at: datetime | None = None


class EventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    event_id: str
    camera_id: str
    label: str
    confidence: float
    bbox: tuple[int, int, int, int]
    frame_width: int
    frame_height: int
    source: str
    created_at: datetime


class EventListResponse(BaseModel):
    items: list[EventResponse]
    count: int = Field(ge=0)


class AnalyticsSummaryResponse(BaseModel):
    total_events: int = Field(ge=0)
    counts_by_label: dict[str, int]
    recent_counts_by_label: dict[str, int]
    recent_activity_count: int = Field(ge=0)
    recent_window_minutes: int = Field(ge=1)
    latest_event: EventResponse | None = None
