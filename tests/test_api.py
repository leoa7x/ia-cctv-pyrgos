from fastapi.testclient import TestClient

from app.api import create_app


def test_health_endpoint():
    client = TestClient(create_app())
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_events_endpoint_defaults_empty():
    client = TestClient(create_app())
    response = client.get("/api/events")
    assert response.status_code == 200
    payload = response.json()
    assert payload["count"] == 0
    assert payload["items"] == []


def test_analytics_summary_endpoint_defaults_empty():
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
    client = TestClient(create_app())
    response = client.post(
        "/api/webrtc/offer",
        json={"sdp": "v=0", "type": "offer"},
    )
    assert response.status_code in {400, 503}
