import numpy as np

from app.config import AppSettings
from app.detectors.base import Detection
from app.repositories import InMemoryEventRepository
from app.services import EventService, LocalAIService


def test_local_ai_builds_context_from_events():
    repository = InMemoryEventRepository()
    event_service = EventService(repository, track_confirmation_hits=1)
    frame = np.zeros((720, 1280, 3), dtype=np.uint8)
    event_service.record_detections(
        "cam-1",
        frame,
        [
            Detection(label="person", confidence=0.91, x1=10, y1=20, x2=100, y2=200),
            Detection(label="car", confidence=0.88, x1=50, y1=80, x2=220, y2=260),
        ],
    )
    service = LocalAIService(
        settings=AppSettings(
            ollama_host="http://127.0.0.1:11434",
            ollama_model="qwen2.5:7b-instruct",
        ),
        event_service=event_service,
    )

    captured_prompt: dict[str, str] = {}

    def fake_query(prompt: str) -> str:
        captured_prompt["value"] = prompt
        return "Hubo una persona y un carro."

    service._query_ollama = fake_query  # type: ignore[method-assign]
    response = service.answer_question("Que paso hace poco?", camera_id="cam-1")

    assert "Conteos por clase: car:1, person:1" in captured_prompt["value"]
    assert "Pregunta del operador: Que paso hace poco?" in captured_prompt["value"]
    assert response.answer == "Hubo una persona y un carro."


def test_local_ai_requires_configuration():
    service = LocalAIService(settings=AppSettings(), event_service=EventService(InMemoryEventRepository()))

    try:
        service.answer_question("Que paso?")
    except RuntimeError as exc:
        assert "Ollama no esta configurado" in str(exc)
    else:
        raise AssertionError("Se esperaba RuntimeError cuando Ollama no esta configurado.")
