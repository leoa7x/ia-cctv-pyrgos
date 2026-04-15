from __future__ import annotations

from dataclasses import asdict, dataclass
from threading import Event
from typing import TYPE_CHECKING

import cv2

if TYPE_CHECKING:
    from app.core.pipeline import PipelineSnapshot, PyrgosPipeline


def launch_native_panel(pipelines: list["PyrgosPipeline"] | "PyrgosPipeline") -> int:
    try:
        import shiboken6
        from PySide6.QtCore import QObject, Qt, QThread, Signal
        from PySide6.QtGui import QImage, QPixmap
        from PySide6.QtWidgets import (
            QApplication,
            QGridLayout,
            QGroupBox,
            QHBoxLayout,
            QLabel,
            QLineEdit,
            QMainWindow,
            QPushButton,
            QTableWidget,
            QTableWidgetItem,
            QTextEdit,
            QVBoxLayout,
            QWidget,
        )
    except ImportError as exc:
        raise RuntimeError(
            "PySide6 no esta instalado. Instala el extra desktop para usar el panel nativo."
        ) from exc

    pipeline_list = pipelines if isinstance(pipelines, list) else [pipelines]
    if not pipeline_list:
        raise RuntimeError("No hay pipelines configurados para abrir el panel nativo.")

    @dataclass(slots=True)
    class CameraWidgets:
        camera_id: str
        group: QGroupBox
        video_label: QLabel
        status_label: QLabel
        error_label: QLabel
        video_fps_label: QLabel
        inference_fps_label: QLabel
        events_label: QLabel
        label_label: QLabel
        confidence_label: QLabel
        debug_raw_label: QLabel
        debug_filtered_label: QLabel
        debug_labels_label: QLabel

    class PipelineWorker(QObject):
        snapshot_ready = Signal(object)
        failed = Signal(str, str)
        finished = Signal(str)

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
                self.failed.emit(self.pipeline.camera_id, str(exc))
            finally:
                self.finished.emit(self.pipeline.camera_id)

        def stop(self) -> None:
            self.stop_event.set()

    class AIWorker(QObject):
        answered = Signal(str)
        failed = Signal(str)
        finished = Signal()

        def __init__(
            self,
            local_ai_service,
            question: str,
            camera_id: str | None,
            recent_window_minutes: int,
        ):
            super().__init__()
            self.local_ai_service = local_ai_service
            self.question = question
            self.camera_id = camera_id
            self.recent_window_minutes = recent_window_minutes

        def run(self) -> None:
            try:
                result = self.local_ai_service.answer_question(
                    question=self.question,
                    camera_id=self.camera_id,
                    recent_window_minutes=self.recent_window_minutes,
                )
                self.answered.emit(result.answer)
            except Exception as exc:
                self.failed.emit(str(exc))
            finally:
                self.finished.emit()

    class NativeDashboard(QMainWindow):
        def __init__(self, owned_pipelines: list["PyrgosPipeline"]):
            super().__init__()
            self.pipelines = owned_pipelines
            self.runtime = owned_pipelines[0].runtime
            self._closing = False
            self.ai_thread = None
            self.ai_worker = None
            self.camera_widgets: dict[str, CameraWidgets] = {}
            self.threads: dict[str, QThread] = {}
            self.workers: dict[str, PipelineWorker] = {}

            self.setWindowTitle(f"IA CCTV PYRGOS - {len(owned_pipelines)} camaras")
            self.resize(1680, 980)

            self.analytics_recent = QLabel("0")
            self.analytics_window = QLabel("10 min")
            self.analytics_counts_total = QLabel("-")
            self.analytics_counts_total.setWordWrap(True)
            self.analytics_counts_recent = QLabel("-")
            self.analytics_counts_recent.setWordWrap(True)
            self.ai_status = QLabel("Ollama no configurado")
            self.ai_status.setWordWrap(True)
            self.ai_history = QTextEdit()
            self.ai_history.setReadOnly(True)
            self.ai_history.setPlaceholderText("Las respuestas del chat local apareceran aqui.")
            self.ai_question = QLineEdit()
            self.ai_question.setPlaceholderText("Pregunta a la IA local sobre todas las camaras...")
            self.ai_send_button = QPushButton("Preguntar")
            self.ai_send_button.clicked.connect(self._send_ai_question)
            self.ai_question.returnPressed.connect(self._send_ai_question)

            self.events_table = QTableWidget(0, 5)
            self.events_table.setHorizontalHeaderLabels(
                ["Hora", "Camara", "Clase", "Confianza", "BBox"]
            )
            self.events_table.horizontalHeader().setStretchLastSection(True)
            self.events_table.verticalHeader().setVisible(False)
            self.events_table.setEditTriggers(QTableWidget.NoEditTriggers)
            self.events_table.setSelectionBehavior(QTableWidget.SelectRows)

            left_col = QVBoxLayout()
            left_col.addLayout(self._build_camera_grid(), stretch=1)

            right_col = QVBoxLayout()
            right_col.addWidget(self._build_analytics_box())
            right_col.addWidget(self._build_ai_box())
            right_col.addWidget(self._build_events_box(), stretch=1)

            root = QHBoxLayout()
            root.addLayout(left_col, stretch=3)
            root.addLayout(right_col, stretch=2)

            container = QWidget()
            container.setLayout(root)
            self.setCentralWidget(container)

            app.aboutToQuit.connect(self._shutdown_threads)
            self._start_pipeline_threads()

        def _build_camera_grid(self):
            layout = QGridLayout()
            columns = 2 if len(self.pipelines) > 1 else 1
            for index, pipeline in enumerate(self.pipelines):
                widgets = self._create_camera_widgets(pipeline.camera_id)
                self.camera_widgets[pipeline.camera_id] = widgets
                row = index // columns
                col = index % columns
                layout.addWidget(widgets.group, row, col)
            return layout

        def _create_camera_widgets(self, camera_id: str) -> CameraWidgets:
            group = QGroupBox(f"Camara {camera_id}")
            group_layout = QVBoxLayout()

            video_label = QLabel("Esperando video...")
            video_label.setAlignment(Qt.AlignCenter)
            video_label.setMinimumSize(640, 360)
            video_label.setStyleSheet(
                "background:#111814;color:#f5f1e8;border-radius:16px;padding:16px;"
            )
            group_layout.addWidget(video_label)

            status_label = QLabel("Sin datos")
            error_label = QLabel("Ninguno")
            error_label.setWordWrap(True)
            video_fps_label = QLabel("0.0")
            inference_fps_label = QLabel("-")
            events_label = QLabel("0")
            label_label = QLabel("-")
            confidence_label = QLabel("-")
            debug_raw_label = QLabel("0")
            debug_filtered_label = QLabel("0")
            debug_labels_label = QLabel("-")
            debug_labels_label.setWordWrap(True)

            metrics = QGridLayout()
            metrics.addWidget(QLabel("Estado"), 0, 0)
            metrics.addWidget(status_label, 0, 1)
            metrics.addWidget(QLabel("Ultimo error"), 1, 0)
            metrics.addWidget(error_label, 1, 1)
            metrics.addWidget(QLabel("Video FPS"), 2, 0)
            metrics.addWidget(video_fps_label, 2, 1)
            metrics.addWidget(QLabel("Inference FPS"), 3, 0)
            metrics.addWidget(inference_fps_label, 3, 1)
            metrics.addWidget(QLabel("Eventos"), 4, 0)
            metrics.addWidget(events_label, 4, 1)
            metrics.addWidget(QLabel("Ultima clase"), 5, 0)
            metrics.addWidget(label_label, 5, 1)
            metrics.addWidget(QLabel("Ultima confianza"), 6, 0)
            metrics.addWidget(confidence_label, 6, 1)
            metrics.addWidget(QLabel("Crudas"), 7, 0)
            metrics.addWidget(debug_raw_label, 7, 1)
            metrics.addWidget(QLabel("Filtradas"), 8, 0)
            metrics.addWidget(debug_filtered_label, 8, 1)
            metrics.addWidget(QLabel("Etiquetas"), 9, 0)
            metrics.addWidget(debug_labels_label, 9, 1)
            group_layout.addLayout(metrics)

            group.setLayout(group_layout)
            return CameraWidgets(
                camera_id=camera_id,
                group=group,
                video_label=video_label,
                status_label=status_label,
                error_label=error_label,
                video_fps_label=video_fps_label,
                inference_fps_label=inference_fps_label,
                events_label=events_label,
                label_label=label_label,
                confidence_label=confidence_label,
                debug_raw_label=debug_raw_label,
                debug_filtered_label=debug_filtered_label,
                debug_labels_label=debug_labels_label,
            )

        def _build_events_box(self) -> QGroupBox:
            box = QGroupBox("Eventos recientes")
            layout = QVBoxLayout()
            layout.addWidget(self.events_table)
            box.setLayout(layout)
            return box

        def _build_analytics_box(self) -> QGroupBox:
            box = QGroupBox("Analitica global")
            layout = QGridLayout()
            layout.addWidget(QLabel("Actividad reciente"), 0, 0)
            layout.addWidget(self.analytics_recent, 0, 1)
            layout.addWidget(QLabel("Ventana"), 1, 0)
            layout.addWidget(self.analytics_window, 1, 1)
            layout.addWidget(QLabel("Conteo total"), 2, 0)
            layout.addWidget(self.analytics_counts_total, 2, 1)
            layout.addWidget(QLabel("Conteo reciente"), 3, 0)
            layout.addWidget(self.analytics_counts_recent, 3, 1)
            box.setLayout(layout)
            return box

        def _build_ai_box(self) -> QGroupBox:
            box = QGroupBox("IA local")
            layout = QVBoxLayout()
            layout.addWidget(self.ai_status)
            layout.addWidget(self.ai_history)
            question_row = QHBoxLayout()
            question_row.addWidget(self.ai_question, stretch=1)
            question_row.addWidget(self.ai_send_button)
            layout.addLayout(question_row)
            box.setLayout(layout)
            return box

        def _start_pipeline_threads(self) -> None:
            for pipeline in self.pipelines:
                thread = QThread(self)
                worker = PipelineWorker(pipeline)
                worker.moveToThread(thread)
                thread.started.connect(worker.run)
                worker.snapshot_ready.connect(self._render_snapshot)
                worker.failed.connect(self._render_error)
                worker.finished.connect(thread.quit)
                thread.finished.connect(thread.deleteLater)
                thread.start()
                self.threads[pipeline.camera_id] = thread
                self.workers[pipeline.camera_id] = worker

        def _render_snapshot(self, snapshot: "PipelineSnapshot") -> None:
            if self._closing:
                return
            widgets = self.camera_widgets[snapshot.camera_id]
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
                widgets.video_label.size(),
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation,
            )
            widgets.video_label.setPixmap(pixmap)

            status = asdict(self.runtime.get_camera_status(snapshot.camera_id))
            widgets.status_label.setText("Conectada" if status["connected"] else "Sin conexion")
            widgets.error_label.setText(status["last_error"] or "Ninguno")
            widgets.video_fps_label.setText(f"{snapshot.video_fps:.1f}")
            widgets.inference_fps_label.setText(
                "-" if snapshot.inference_fps is None else f"{snapshot.inference_fps:.1f}"
            )
            widgets.events_label.setText(str(snapshot.event_count))
            widgets.label_label.setText(snapshot.latest_event_label)
            widgets.confidence_label.setText(
                "-"
                if snapshot.latest_event_confidence is None
                else f"{snapshot.latest_event_confidence * 100:.1f}%"
            )
            widgets.debug_raw_label.setText(str(snapshot.raw_detection_count))
            widgets.debug_filtered_label.setText(str(snapshot.filtered_detection_count))
            widgets.debug_labels_label.setText(
                ", ".join(str(label) for label in snapshot.raw_detection_labels)
                if snapshot.raw_detection_labels
                else "-"
            )
            self._render_analytics()
            self._render_events()
            self._render_ai_status()

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

        def _render_analytics(self) -> None:
            summary = self.runtime.event_service.analytics_summary(recent_window_minutes=10)
            self.analytics_recent.setText(str(summary.recent_activity_count))
            self.analytics_window.setText(f"{summary.recent_window_minutes} min")
            self.analytics_counts_total.setText(self._format_counts(summary.counts_by_label))
            self.analytics_counts_recent.setText(
                self._format_counts(summary.recent_counts_by_label)
            )

        def _format_counts(self, counts: dict[str, int]) -> str:
            if not counts:
                return "-"
            parts = [
                f"{label}: {count}"
                for label, count in sorted(counts.items(), key=lambda item: (-item[1], item[0]))
            ]
            return " | ".join(parts)

        def _render_ai_status(self) -> None:
            if self.runtime.local_ai.configured:
                self.ai_status.setText(
                    "Ollama listo "
                    f"({self.runtime.settings.ollama_model} @ {self.runtime.settings.ollama_host})"
                )
                self.ai_send_button.setEnabled(self.ai_thread is None)
                self.ai_question.setEnabled(True)
            else:
                self.ai_status.setText(
                    "Ollama no configurado. Define PYRGOS_OLLAMA_HOST y PYRGOS_OLLAMA_MODEL."
                )
                self.ai_send_button.setEnabled(False)
                self.ai_question.setEnabled(False)

        def _send_ai_question(self) -> None:
            question = self.ai_question.text().strip()
            if not question or self.ai_thread is not None:
                return
            self.ai_history.append(f"Operador: {question}")
            self.ai_history.append("IA: pensando...")
            self.ai_send_button.setEnabled(False)
            self.ai_question.clear()

            self.ai_thread = QThread(self)
            self.ai_worker = AIWorker(
                local_ai_service=self.runtime.local_ai,
                question=question,
                camera_id=None,
                recent_window_minutes=10,
            )
            self.ai_worker.moveToThread(self.ai_thread)
            self.ai_thread.started.connect(self.ai_worker.run)
            self.ai_worker.answered.connect(self._render_ai_answer)
            self.ai_worker.failed.connect(self._render_ai_error)
            self.ai_worker.finished.connect(self.ai_thread.quit)
            self.ai_worker.finished.connect(self.ai_worker.deleteLater)
            self.ai_thread.finished.connect(self._cleanup_ai_thread)
            self.ai_thread.start()

        def _render_ai_answer(self, answer: str) -> None:
            if self._closing:
                return
            self._replace_last_ai_line(f"IA: {answer}")

        def _render_ai_error(self, message: str) -> None:
            if self._closing:
                return
            self._replace_last_ai_line(f"IA: error - {message}")

        def _replace_last_ai_line(self, text: str) -> None:
            lines = self.ai_history.toPlainText().splitlines()
            if lines and lines[-1] == "IA: pensando...":
                lines[-1] = text
                self.ai_history.setPlainText("\n".join(lines))
            else:
                self.ai_history.append(text)
            cursor = self.ai_history.textCursor()
            cursor.movePosition(cursor.MoveOperation.End)
            self.ai_history.setTextCursor(cursor)

        def _cleanup_ai_thread(self) -> None:
            if self.ai_thread is not None and shiboken6.isValid(self.ai_thread):
                self.ai_thread.deleteLater()
            self.ai_thread = None
            self.ai_worker = None
            self.ai_send_button.setEnabled(self.runtime.local_ai.configured)

        def _render_error(self, camera_id: str, message: str) -> None:
            if self._closing:
                return
            widgets = self.camera_widgets.get(camera_id)
            if widgets is None:
                return
            widgets.status_label.setText("Error")
            widgets.error_label.setText(message)

        def _shutdown_threads(self) -> None:
            if self._closing:
                return
            self._closing = True
            for worker in self.workers.values():
                if worker is not None:
                    worker.stop()
            for thread in self.threads.values():
                if (
                    thread is not None
                    and shiboken6.isValid(thread)
                    and thread.isRunning()
                ):
                    thread.quit()
                    if not thread.wait(5000):
                        thread.terminate()
                        thread.wait(2000)
            if self.ai_thread is not None and shiboken6.isValid(self.ai_thread):
                self.ai_thread.quit()
                if not self.ai_thread.wait(5000):
                    self.ai_thread.terminate()
                    self.ai_thread.wait(2000)

        def closeEvent(self, event) -> None:
            self._shutdown_threads()
            super().closeEvent(event)

    app = QApplication.instance() or QApplication([])
    window = NativeDashboard(pipeline_list)
    window.show()
    return app.exec()
