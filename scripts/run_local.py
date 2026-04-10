from app.config import load_settings
from app.core import PyrgosPipeline


def main() -> None:
    settings = load_settings()
    if not settings.stream_url:
        raise SystemExit(
            "Define PYRGOS_STREAM_URL con la URL del stream IP del iPhone antes de ejecutar."
        )
    if settings.detector_backend == "none":
        print("Iniciando en modo stream-only. La deteccion IA queda desactivada.")
    pipeline = PyrgosPipeline(settings)
    pipeline.run()


if __name__ == "__main__":
    main()
