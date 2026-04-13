from app.runtime import AppRuntime


def test_runtime_uses_in_memory_repository_when_database_url_missing(monkeypatch):
    monkeypatch.delenv("PYRGOS_DATABASE_URL", raising=False)
    monkeypatch.delenv("DATABASE_URL", raising=False)
    runtime = AppRuntime()
    assert runtime.settings.database_url == ""
    assert runtime.event_service.repository.__class__.__name__ == "InMemoryEventRepository"

