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


def test_webrtc_offer_returns_503_when_backend_not_installed():
    client = TestClient(create_app())
    response = client.post(
        "/api/webrtc/offer",
        json={"sdp": "v=0", "type": "offer"},
    )
    assert response.status_code in {400, 503}
