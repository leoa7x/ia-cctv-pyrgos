from app.config import load_settings
from app.core import PyrgosPipeline
from app.ui import launch_native_panel


def main() -> None:
    settings = load_settings()
    if not settings.cameras:
        raise SystemExit(
            "Define PYRGOS_STREAM_URL o PYRGOS_CAMERAS antes de ejecutar."
        )
    if settings.detector_backend == "none":
        print("Iniciando en modo stream-only. La deteccion IA queda desactivada.")
    pipelines = [
        PyrgosPipeline(settings, camera_id=camera.camera_id, stream_url=camera.stream_url)
        for camera in settings.cameras
    ]
    try:
        launch_native_panel(pipelines)
    except RuntimeError as exc:
        print(f"{exc} Se usa el visor OpenCV como fallback.")
        for pipeline in pipelines:
            pipeline.run()


if __name__ == "__main__":
    main()
