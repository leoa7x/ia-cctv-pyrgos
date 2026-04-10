import os
from functools import lru_cache
from dataclasses import dataclass, field


@dataclass(slots=True)
class AppSettings:
    stream_url: str = ""
    window_name: str = "IA CCTV PYRGOS"
    detector_backend: str = "rfdetr"
    confidence: float = 0.5
    model_variant: str = "medium"
    target_classes: list[str] = field(
        default_factory=lambda: ["person", "car", "motorcycle", "bus", "truck"]
    )
    frame_skip: int = 1
    detection_interval_frames: int = 45
    show_fps: bool = True


@lru_cache(maxsize=1)
def load_settings() -> AppSettings:
    raw_classes = os.getenv("PYRGOS_TARGET_CLASSES", "person,car,motorcycle,bus,truck")
    target_classes = [item.strip() for item in raw_classes.split(",") if item.strip()]
    return AppSettings(
        stream_url=os.getenv("PYRGOS_STREAM_URL", "").strip(),
        window_name=os.getenv("PYRGOS_WINDOW_NAME", "IA CCTV PYRGOS").strip(),
        detector_backend=os.getenv("PYRGOS_DETECTOR_BACKEND", "rfdetr").strip().lower(),
        confidence=float(os.getenv("PYRGOS_CONFIDENCE", "0.5")),
        model_variant=os.getenv("PYRGOS_MODEL_VARIANT", "medium").strip().lower(),
        target_classes=target_classes,
        frame_skip=int(os.getenv("PYRGOS_FRAME_SKIP", "1")),
        detection_interval_frames=int(os.getenv("PYRGOS_DETECTION_INTERVAL_FRAMES", "45")),
        show_fps=os.getenv("PYRGOS_SHOW_FPS", "true").strip().lower() in {"1", "true", "yes"},
    )
