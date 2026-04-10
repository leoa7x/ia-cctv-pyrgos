from app.config.settings import AppSettings


def test_default_target_classes():
    settings = AppSettings()
    assert settings.detector_backend == "rfdetr"
    assert settings.detection_interval_frames == 45
    assert "person" in settings.target_classes
    assert "car" in settings.target_classes
