from __future__ import annotations

from dataclasses import asdict
from threading import Event
from typing import TYPE_CHECKING

import cv2

if TYPE_CHECKING:
    from app.core.pipeline import PipelineSnapshot, PyrgosPipeline


def launch_native_panel(pipeline: "PyrgosPipeline") -> int:
    try:
        from PySide6.QtCore import QObject, Qt, QThread, Signal
        from PySide6.QtGui import QImage, QPixmap
        from PySide6.QtWidgets import (
            QApplication,
            QGridLayout,
            QGroupBox,
            QHBoxLayout,
            QLabel,
            QMainWindow,
            QTableWidget,
            QTableWidgetItem,
            QVBoxLayout,
            QWidget,
        )
    except ImportError as exc:
        raise RuntimeError(
            "PySide6 no esta instalado. Instala el extra desktop para usar el panel nativo."
        ) from exc

    class PipelineWorker(QObject):
        snapshot_ready = Signal(object)
        failed = Signal(str)
        finished = Signal()

        def __init__(self, owned_pipeline: "PyrgosPipeline"):
            super().__init__()
            self.pipeline = owned_pipeline
            self.stop_event = Event()

        def run(self) -> None:
            try:
                for snapshot in self.pipeline.iter_snapshots(self.stop_event):
                    self.snapshot_ready.emit(snapshot)
                    if self.stop_event.is_set():
                        break
            except Exception as exc:
                self.failed.emit(str(exc))
            finally:
                self.finished.emit()

        def stop(self) -> None:
            self.stop_event.set()

    class NativeDashboard(QMainWindow):
        def __init__(self, owned_pipeline: "PyrgosPipeline"):
            super().__init__()
            self.pipeline = owned_pipeline
            self.runtime = owned_pipeline.runtime
            self.setWindowTitle("IA CCTV PYRGOS")
            self.resize(1440, 900)

            self.video_label = QLabel("Esperando video...")
            self.video_label.setAlignment(Qt.AlignCenter)
            self.video_label.setMinimumSize(960, 540)
            self.video_label.setStyleSheet(
                "background:#111814;color:#f5f1e8;border-radius:16px;padding:16px;"
            )

            self.camera_status = QLabel("Sin datos")
            self.camera_error = QLabel("Ninguno")
            self.camera_error.setWordWrap(True)
            self.metric_video_fps = QLabel("0.0")
            self.metric_inference_fps = QLabel("-")
            self.metric_events = QLabel("0")
            self.metric_label = QLabel("-")
            self.metric_confidence = QLabel("-")

            self.events_table = QTableWidget(0, 5)
            self.events_table.setHorizontalHeaderLabels(
                ["Hora", "Camara", "Clase", "Confianza", "BBox"]
            )
            self.events_table.horizontalHeader().setStretchLastSection(True)
            self.events_table.verticalHeader().setVisible(False)
            self.events_table.setEditTriggers(QTableWidget.NoEditTriggers)
            self.events_table.setSelectionBehavior(QTableWidget.SelectRows)

            left_col = QVBoxLayout()
            left_col.addWidget(self.video_label, stretch=1)

            right_col = QVBoxLayout()
            right_col.addWidget(self._build_camera_box())
            right_col.addWidget(self._build_metrics_box())
            right_col.addWidget(self._build_events_box(), stretch=1)

            root = QHBoxLayout()
            root.addLayout(left_col, stretch=3)
            root.addLayout(right_col, stretch=2)

            container = QWidget()
            container.setLayout(root)
            self.setCentralWidget(container)

            self.thread = QThread(self)
            self.worker = PipelineWorker(self.pipeline)
            self.worker.moveToThread(self.thread)
            self.thread.started.connect(self.worker.run)
            self.worker.snapshot_ready.connect(self._render_snapshot)
            self.worker.failed.connect(self._render_error)
            self.worker.finished.connect(self.thread.quit)
            self.thread.start()

        def _build_camera_box(self) -> QGroupBox:
            box = QGroupBox("Camara")
            layout = QGridLayout()
            layout.addWidget(QLabel("Estado"), 0, 0)
            layout.addWidget(self.camera_status, 0, 1)
            layout.addWidget(QLabel("Ultimo error"), 1, 0)
            layout.addWidget(self.camera_error, 1, 1)
            box.setLayout(layout)
            return box

        def _build_metrics_box(self) -> QGroupBox:
            box = QGroupBox("Metricas")
            layout = QGridLayout()
            layout.addWidget(QLabel("Video FPS"), 0, 0)
            layout.addWidget(self.metric_video_fps, 0, 1)
            layout.addWidget(QLabel("Inference FPS"), 1, 0)
            layout.addWidget(self.metric_inference_fps, 1, 1)
            layout.addWidget(QLabel("Eventos"), 2, 0)
            layout.addWidget(self.metric_events, 2, 1)
            layout.addWidget(QLabel("Ultima clase"), 3, 0)
            layout.addWidget(self.metric_label, 3, 1)
            layout.addWidget(QLabel("Ultima confianza"), 4, 0)
            layout.addWidget(self.metric_confidence, 4, 1)
            box.setLayout(layout)
            return box

        def _build_events_box(self) -> QGroupBox:
            box = QGroupBox("Eventos recientes")
            layout = QVBoxLayout()
            layout.addWidget(self.events_table)
            box.setLayout(layout)
            return box

        def _render_snapshot(self, snapshot: "PipelineSnapshot") -> None:
            frame = cv2.cvtColor(snapshot.frame, cv2.COLOR_BGR2RGB)
            height, width, channels = frame.shape
            image = QImage(
                frame.data,
                width,
                height,
                channels * width,
                QImage.Format_RGB888,
            )
            pixmap = QPixmap.fromImage(image).scaled(
                self.video_label.size(),
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation,
            )
            self.video_label.setPixmap(pixmap)

            status = asdict(self.runtime.camera_status)
            self.camera_status.setText("Conectada" if status["connected"] else "Sin conexion")
            self.camera_error.setText(status["last_error"] or "Ninguno")
            self.metric_video_fps.setText(f"{snapshot.video_fps:.1f}")
            self.metric_inference_fps.setText(
                "-"
                if snapshot.inference_fps is None
                else f"{snapshot.inference_fps:.1f}"
            )
            self.metric_events.setText(str(snapshot.event_count))
            self.metric_label.setText(snapshot.latest_event_label)
            self.metric_confidence.setText(
                "-"
                if snapshot.latest_event_confidence is None
                else f"{snapshot.latest_event_confidence * 100:.1f}%"
            )
            self._render_events()

        def _render_events(self) -> None:
            events = self.runtime.event_service.list_events(limit=20)
            self.events_table.setRowCount(len(events))
            for row, event in enumerate(events):
                self.events_table.setItem(row, 0, QTableWidgetItem(event.created_at.isoformat()))
                self.events_table.setItem(row, 1, QTableWidgetItem(event.camera_id))
                self.events_table.setItem(row, 2, QTableWidgetItem(event.label))
                self.events_table.setItem(
                    row, 3, QTableWidgetItem(f"{event.confidence * 100:.1f}%")
                )
                self.events_table.setItem(
                    row,
                    4,
                    QTableWidgetItem(
                        f"{event.bbox[0]}, {event.bbox[1]}, {event.bbox[2]}, {event.bbox[3]}"
                    ),
                )

        def _render_error(self, message: str) -> None:
            self.camera_status.setText("Error")
            self.camera_error.setText(message)

        def closeEvent(self, event) -> None:
            self.worker.stop()
            self.thread.quit()
            self.thread.wait(3000)
            super().closeEvent(event)

    app = QApplication.instance() or QApplication([])
    window = NativeDashboard(pipeline)
    window.show()
    return app.exec()
