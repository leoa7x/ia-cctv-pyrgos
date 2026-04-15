from app.config.settings import load_settings
from fastapi.testclient import TestClient

from app.api import create_app
from app.runtime import get_runtime


def test_health_endpoint():
    load_settings.cache_clear()
    get_runtime.cache_clear()
    client = TestClient(create_app())
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["storage_backend"] == "InMemoryEventRepository"
    assert response.json()["database_configured"] is False


def test_events_endpoint_defaults_empty():
    load_settings.cache_clear()
    get_runtime.cache_clear()
    client = TestClient(create_app())
    response = client.get("/api/events")
    assert response.status_code == 200
    payload = response.json()
    assert payload["count"] == 0
    assert payload["items"] == []


def test_analytics_summary_endpoint_defaults_empty():
    load_settings.cache_clear()
    get_runtime.cache_clear()
    client = TestClient(create_app())
    response = client.get("/api/analytics/summary")
    assert response.status_code == 200
    payload = response.json()
    assert payload["total_events"] == 0
    assert payload["counts_by_label"] == {}
    assert payload["recent_counts_by_label"] == {}
    assert payload["recent_activity_count"] == 0
    assert payload["latest_event"] is None


def test_mjpeg_endpoint_exists():
    app = create_app()
    assert any(route.path == "/api/stream.mjpg" for route in app.routes)


def test_jpeg_frame_endpoint_exists():
    app = create_app()
    assert any(route.path == "/api/frame.jpg" for route in app.routes)


def test_webrtc_offer_returns_503_when_backend_not_installed():
    load_settings.cache_clear()
    get_runtime.cache_clear()
    client = TestClient(create_app())
    response = client.post(
        "/api/webrtc/offer",
        json={"sdp": "v=0", "type": "offer"},
    )
    assert response.status_code in {400, 503}


def test_ai_chat_returns_503_when_ollama_is_not_configured():
    load_settings.cache_clear()
    get_runtime.cache_clear()
    client = TestClient(create_app())
    response = client.post("/api/ai/chat", json={"question": "Que paso?"})
    assert response.status_code == 503
    assert "Ollama no esta configurado" in response.json()["detail"]


def test_ai_chat_endpoint_uses_local_ai_service():
    load_settings.cache_clear()
    get_runtime.cache_clear()
    app = create_app()
    client = TestClient(app)

    class StubLocalAI:
        def answer_question(self, question: str, camera_id: str | None, recent_window_minutes: int):
            assert question == "Resume la actividad"
            assert camera_id == "cam-1"
            assert recent_window_minutes == 15

            class Result:
                answer = "Se detectaron personas y carros."
                model = "qwen2.5:7b-instruct"
                host = "http://127.0.0.1:11434"

            return Result()

    app.state.runtime.local_ai = StubLocalAI()
    response = client.post(
        "/api/ai/chat",
        json={
            "question": "Resume la actividad",
            "camera_id": "cam-1",
            "recent_window_minutes": 15,
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["answer"] == "Se detectaron personas y carros."
    assert payload["model"] == "qwen2.5:7b-instruct"


def test_cameras_endpoint_returns_all_configured_cameras(monkeypatch):
    monkeypatch.setenv(
        "PYRGOS_CAMERAS",
        "cam-a|rtsp://127.0.0.1:8554/a|Entrada;cam-b|rtsp://127.0.0.1:8554/b|Drone",
    )
    load_settings.cache_clear()
    get_runtime.cache_clear()

    client = TestClient(create_app())
    response = client.get("/api/cameras")

    assert response.status_code == 200
    payload = response.json()
    assert len(payload) == 2
    assert payload[0]["camera_id"] == "cam-a"
    assert payload[1]["camera_id"] == "cam-b"
