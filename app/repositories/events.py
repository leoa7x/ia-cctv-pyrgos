from __future__ import annotations

from collections import deque
from datetime import UTC, datetime
from threading import Lock
from typing import Protocol

from app.domain import DetectionEvent


class EventRepository(Protocol):
    def add(self, event: DetectionEvent) -> DetectionEvent:
        ...

    def list(self, limit: int = 50, camera_id: str | None = None) -> list[DetectionEvent]:
        ...


class InMemoryEventRepository:
    def __init__(self, max_events: int = 1000):
        self._events: deque[DetectionEvent] = deque(maxlen=max_events)
        self._lock = Lock()

    def add(self, event: DetectionEvent) -> DetectionEvent:
        with self._lock:
            self._events.appendleft(event)
        return event

    def list(self, limit: int = 50, camera_id: str | None = None) -> list[DetectionEvent]:
        with self._lock:
            events = list(self._events)
        if camera_id:
            events = [event for event in events if event.camera_id == camera_id]
        return events[:limit]


class PostgresEventRepository:
    def __init__(self, dsn: str):
        try:
            import psycopg
        except ImportError as exc:
            raise RuntimeError(
                "psycopg no esta instalado. Instala las dependencias base del proyecto."
            ) from exc
        self._psycopg = psycopg
        self._dsn = dsn
        self._ensure_schema()

    def _connect(self):
        return self._psycopg.connect(self._dsn)

    def _ensure_schema(self) -> None:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS detection_events (
                        event_id TEXT PRIMARY KEY,
                        camera_id TEXT NOT NULL,
                        label TEXT NOT NULL,
                        confidence DOUBLE PRECISION NOT NULL,
                        bbox_x1 INTEGER NOT NULL,
                        bbox_y1 INTEGER NOT NULL,
                        bbox_x2 INTEGER NOT NULL,
                        bbox_y2 INTEGER NOT NULL,
                        frame_width INTEGER NOT NULL,
                        frame_height INTEGER NOT NULL,
                        source TEXT NOT NULL,
                        created_at TIMESTAMPTZ NOT NULL
                    );
                    CREATE INDEX IF NOT EXISTS idx_detection_events_created_at
                    ON detection_events (created_at DESC);
                    CREATE INDEX IF NOT EXISTS idx_detection_events_camera_id
                    ON detection_events (camera_id);
                    CREATE INDEX IF NOT EXISTS idx_detection_events_label
                    ON detection_events (label);
                    """
                )
            conn.commit()

    def add(self, event: DetectionEvent) -> DetectionEvent:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO detection_events (
                        event_id,
                        camera_id,
                        label,
                        confidence,
                        bbox_x1,
                        bbox_y1,
                        bbox_x2,
                        bbox_y2,
                        frame_width,
                        frame_height,
                        source,
                        created_at
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (event_id) DO NOTHING
                    """,
                    (
                        event.event_id,
                        event.camera_id,
                        event.label,
                        event.confidence,
                        event.bbox[0],
                        event.bbox[1],
                        event.bbox[2],
                        event.bbox[3],
                        event.frame_width,
                        event.frame_height,
                        event.source,
                        event.created_at,
                    ),
                )
            conn.commit()
        return event

    def list(self, limit: int = 50, camera_id: str | None = None) -> list[DetectionEvent]:
        query = """
            SELECT
                event_id,
                camera_id,
                label,
                confidence,
                bbox_x1,
                bbox_y1,
                bbox_x2,
                bbox_y2,
                frame_width,
                frame_height,
                source,
                created_at
            FROM detection_events
        """
        params: list[object] = []
        if camera_id:
            query += " WHERE camera_id = %s"
            params.append(camera_id)
        query += " ORDER BY created_at DESC LIMIT %s"
        params.append(limit)

        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(query, params)
                rows = cur.fetchall()

        events: list[DetectionEvent] = []
        for row in rows:
            created_at = row[11]
            if created_at.tzinfo is None:
                created_at = created_at.replace(tzinfo=UTC)
            events.append(
                DetectionEvent(
                    event_id=row[0],
                    camera_id=row[1],
                    label=row[2],
                    confidence=float(row[3]),
                    bbox=(int(row[4]), int(row[5]), int(row[6]), int(row[7])),
                    frame_width=int(row[8]),
                    frame_height=int(row[9]),
                    source=row[10],
                    created_at=created_at,
                )
            )
        return events
