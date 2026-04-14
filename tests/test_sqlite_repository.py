from pathlib import Path

from app.domain import DetectionEvent
from app.repositories import SQLiteEventRepository


def test_sqlite_repository_persists_and_lists_events(tmp_path: Path):
    db_path = tmp_path / "pyrgos.db"
    repository = SQLiteEventRepository(f"sqlite:///{db_path.as_posix()}")
    event = DetectionEvent(
        event_id="evt-1",
        camera_id="cam-1",
        label="person",
        confidence=0.91,
        bbox=(1, 2, 10, 20),
        frame_width=1280,
        frame_height=720,
    )

    repository.add(event)
    items = repository.list(limit=10, camera_id="cam-1")

    assert len(items) == 1
    assert items[0].event_id == "evt-1"
    assert items[0].label == "person"
