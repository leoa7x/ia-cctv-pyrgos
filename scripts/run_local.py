from app.config import load_settings
from app.core import PyrgosPipeline
from app.ui import launch_native_panel


def main() -> None:
    settings = load_settings()
    if not settings.stream_url:
        raise SystemExit(
            "Define PYRGOS_STREAM_URL con la URL del stream IP del iPhone antes de ejecutar."
        )
    if settings.detector_backend == "none":
        print("Iniciando en modo stream-only. La deteccion IA queda desactivada.")
    pipeline = PyrgosPipeline(settings)
    try:
        launch_native_panel(pipeline)
    except RuntimeError as exc:
        print(f"{exc} Se usa el visor OpenCV como fallback.")
        pipeline.run()


if __name__ == "__main__":
    main()
