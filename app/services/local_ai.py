from __future__ import annotations

from dataclasses import dataclass

import httpx

from app.config import AppSettings
from app.domain import DetectionEvent
from app.services.events import AnalyticsSummary, EventService


@dataclass(slots=True)
class AIChatResponse:
    answer: str
    model: str
    host: str
    prompt_context: str


class LocalAIService:
    def __init__(self, settings: AppSettings, event_service: EventService):
        self.settings = settings
        self.event_service = event_service

    @property
    def configured(self) -> bool:
        return bool(self.settings.ollama_host and self.settings.ollama_model)

    def answer_question(
        self,
        question: str,
        camera_id: str | None = None,
        recent_window_minutes: int = 10,
    ) -> AIChatResponse:
        if not self.configured:
            raise RuntimeError(
                "Ollama no esta configurado. Define PYRGOS_OLLAMA_HOST y PYRGOS_OLLAMA_MODEL."
            )

        summary = self.event_service.analytics_summary(
            camera_id=camera_id,
            recent_window_minutes=recent_window_minutes,
        )
        recent_events = self.event_service.list_events(
            limit=self.settings.ollama_recent_events_limit,
            camera_id=camera_id,
        )
        prompt_context = self._build_prompt_context(
            summary=summary,
            recent_events=recent_events,
            camera_id=camera_id,
            question=question,
        )
        answer = self._query_ollama(prompt_context)
        return AIChatResponse(
            answer=answer,
            model=self.settings.ollama_model,
            host=self.settings.ollama_host,
            prompt_context=prompt_context,
        )

    def _build_prompt_context(
        self,
        summary: AnalyticsSummary,
        recent_events: list[DetectionEvent],
        camera_id: str | None,
        question: str,
    ) -> str:
        counts_text = self._format_counts(summary.counts_by_label)
        recent_counts_text = self._format_counts(summary.recent_counts_by_label)
        latest_event_text = self._format_event(summary.latest_event)
        recent_events_text = "\n".join(self._format_event(event) for event in recent_events[:10])
        if not recent_events_text:
            recent_events_text = "- sin eventos recientes"

        return (
            "Eres un asistente local para CCTV.\n"
            "Responde solo con base en los datos estructurados entregados.\n"
            "Si falta informacion, dilo explicitamente.\n"
            "No inventes eventos ni objetos que no aparezcan en los datos.\n\n"
            "Responde breve y operativamente, en maximo 4 lineas.\n\n"
            f"Camara consultada: {camera_id or 'todas'}\n"
            f"Ventana reciente: {summary.recent_window_minutes} minutos\n"
            f"Total de eventos: {summary.total_events}\n"
            f"Conteos por clase: {counts_text}\n"
            f"Conteos recientes por clase: {recent_counts_text}\n"
            f"Actividad reciente: {summary.recent_activity_count}\n"
            f"Ultimo evento: {latest_event_text}\n"
            f"Eventos recientes clave:\n{recent_events_text}\n\n"
            f"Pregunta del operador: {question}\n"
        )

    def _query_ollama(self, prompt: str) -> str:
        endpoint = self.settings.ollama_host.rstrip("/") + "/api/generate"
        with httpx.Client(timeout=self.settings.ollama_timeout_seconds) as client:
            response = client.post(
                endpoint,
                json={
                    "model": self.settings.ollama_model,
                    "prompt": prompt,
                    "stream": False,
                },
            )
        response.raise_for_status()
        payload = response.json()
        answer = payload.get("response", "").strip()
        if not answer:
            raise RuntimeError("Ollama respondio sin texto util.")
        return answer

    @staticmethod
    def _format_counts(counts: dict[str, int]) -> str:
        if not counts:
            return "sin datos"
        return ", ".join(f"{label}:{count}" for label, count in sorted(counts.items()))

    @staticmethod
    def _format_event(event: DetectionEvent | None) -> str:
        if event is None:
            return "sin eventos"
        timestamp = event.created_at.isoformat(timespec="seconds")
        return (
            f"{timestamp} | camara={event.camera_id} | clase={event.label} | "
            f"conf={event.confidence:.2f} | bbox={event.bbox}"
        )
