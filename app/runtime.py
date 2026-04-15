from __future__ import annotations

from functools import lru_cache

from app.config import load_settings
from app.domain import CameraStatus
from app.repositories import InMemoryEventRepository, PostgresEventRepository, SQLiteEventRepository
from app.services import EventService, LiveDetectionService, LocalAIService


class AppRuntime:
    def __init__(self):
        settings = load_settings()
        self.settings = settings
        if settings.database_url:
            if settings.database_url.startswith("sqlite:///"):
                repository = SQLiteEventRepository(settings.database_url)
            else:
                repository = PostgresEventRepository(settings.database_url)
        else:
            repository = InMemoryEventRepository()
        self.event_service = EventService(
            repository,
            track_ttl_seconds=settings.track_ttl_seconds,
            track_match_iou=settings.track_match_iou,
            track_center_distance_ratio=settings.track_center_distance_ratio,
            track_confirmation_hits=settings.track_confirmation_hits,
        )
        self.local_ai = LocalAIService(settings=settings, event_service=self.event_service)
        self.camera_statuses = {
            camera.camera_id: CameraStatus(
                camera_id=camera.camera_id,
                stream_url=camera.stream_url,
                connected=False,
            )
            for camera in settings.cameras
        }
        if not self.camera_statuses:
            fallback_id = "cam-1"
            self.camera_statuses[fallback_id] = CameraStatus(
                camera_id=fallback_id,
                stream_url=settings.stream_url,
                connected=False,
            )
        self.live_detection_by_camera = {
            camera_id: LiveDetectionService(
                settings=settings,
                event_service=self.event_service,
                camera_id=camera_id,
            )
            for camera_id in self.camera_statuses
        }

    @property
    def camera_status(self) -> CameraStatus:
        return next(iter(self.camera_statuses.values()))

    @property
    def live_detection(self) -> LiveDetectionService:
        return next(iter(self.live_detection_by_camera.values()))

    def get_camera_status(self, camera_id: str) -> CameraStatus:
        return self.camera_statuses[camera_id]

    def list_camera_statuses(self) -> list[CameraStatus]:
        return list(self.camera_statuses.values())


@lru_cache(maxsize=1)
def get_runtime() -> AppRuntime:
    return AppRuntime()
