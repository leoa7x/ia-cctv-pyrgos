from __future__ import annotations

from functools import lru_cache

from app.config import load_settings
from app.domain import CameraStatus
from app.repositories import InMemoryEventRepository
from app.services import EventService, LiveDetectionService


class AppRuntime:
    def __init__(self):
        settings = load_settings()
        self.settings = settings
        repository = InMemoryEventRepository()
        self.event_service = EventService(repository)
        self.camera_status = CameraStatus(
            camera_id="iphone-main",
            stream_url=settings.stream_url,
            connected=False,
        )
        self.live_detection = LiveDetectionService(
            settings=settings,
            event_service=self.event_service,
            camera_id=self.camera_status.camera_id,
        )


@lru_cache(maxsize=1)
def get_runtime() -> AppRuntime:
    return AppRuntime()
