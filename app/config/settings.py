import os
from functools import lru_cache
from dataclasses import dataclass, field


@dataclass(slots=True)
class AppSettings:
    stream_url: str = ""
    stream_backend: str = "opencv"
    ffmpeg_path: str = ""
    window_name: str = "IA CCTV PYRGOS"
    detector_backend: str = "rfdetr"
    database_url: str = ""
    ollama_host: str = ""
    ollama_model: str = ""
    confidence: float = 0.5
    model_variant: str = "medium"
    target_classes: list[str] = field(
        default_factory=lambda: ["person", "car", "motorcycle", "bus", "truck"]
    )
    frame_skip: int = 1
    detection_interval_frames: int = 45
    track_ttl_seconds: float = 8.0
    track_match_iou: float = 0.3
    track_center_distance_ratio: float = 0.12
    track_confirmation_hits: int = 3
    show_fps: bool = True
    debug_detections: bool = False


@lru_cache(maxsize=1)
def load_settings() -> AppSettings:
    raw_classes = os.getenv("PYRGOS_TARGET_CLASSES", "person,car,motorcycle,bus,truck")
    target_classes = [item.strip() for item in raw_classes.split(",") if item.strip()]
    return AppSettings(
        stream_url=os.getenv("PYRGOS_STREAM_URL", "").strip(),
        stream_backend=os.getenv("PYRGOS_STREAM_BACKEND", "opencv").strip().lower(),
        ffmpeg_path=os.getenv("PYRGOS_FFMPEG_PATH", "").strip(),
        window_name=os.getenv("PYRGOS_WINDOW_NAME", "IA CCTV PYRGOS").strip(),
        detector_backend=os.getenv("PYRGOS_DETECTOR_BACKEND", "rfdetr").strip().lower(),
        database_url=os.getenv("PYRGOS_DATABASE_URL", os.getenv("DATABASE_URL", "")).strip(),
        ollama_host=os.getenv("PYRGOS_OLLAMA_HOST", os.getenv("OLLAMA_HOST", "")).strip(),
        ollama_model=os.getenv("PYRGOS_OLLAMA_MODEL", os.getenv("OLLAMA_MODEL", "")).strip(),
        confidence=float(os.getenv("PYRGOS_CONFIDENCE", "0.5")),
        model_variant=os.getenv("PYRGOS_MODEL_VARIANT", "medium").strip().lower(),
        target_classes=target_classes,
        frame_skip=int(os.getenv("PYRGOS_FRAME_SKIP", "1")),
        detection_interval_frames=int(os.getenv("PYRGOS_DETECTION_INTERVAL_FRAMES", "45")),
        track_ttl_seconds=float(os.getenv("PYRGOS_TRACK_TTL_SECONDS", "8.0")),
        track_match_iou=float(os.getenv("PYRGOS_TRACK_MATCH_IOU", "0.3")),
        track_center_distance_ratio=float(
            os.getenv("PYRGOS_TRACK_CENTER_DISTANCE_RATIO", "0.12")
        ),
        track_confirmation_hits=int(os.getenv("PYRGOS_TRACK_CONFIRMATION_HITS", "3")),
        show_fps=os.getenv("PYRGOS_SHOW_FPS", "true").strip().lower() in {"1", "true", "yes"},
        debug_detections=os.getenv("PYRGOS_DEBUG_DETECTIONS", "false").strip().lower()
        in {"1", "true", "yes"},
    )
