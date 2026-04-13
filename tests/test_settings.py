from app.config.settings import AppSettings, load_settings


def test_default_target_classes():
    settings = AppSettings()
    assert settings.detector_backend == "rfdetr"
    assert settings.stream_backend == "opencv"
    assert settings.detection_interval_frames == 45
    assert "person" in settings.target_classes
    assert "car" in settings.target_classes


def test_load_settings_accepts_database_url(monkeypatch):
    monkeypatch.setenv("PYRGOS_DATABASE_URL", "postgresql://user:pass@db:5432/pyrgos")
    load_settings.cache_clear()
    try:
        settings = load_settings()
    finally:
        load_settings.cache_clear()
    assert settings.database_url == "postgresql://user:pass@db:5432/pyrgos"
