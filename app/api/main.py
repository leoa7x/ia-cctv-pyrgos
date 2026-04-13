from __future__ import annotations

import asyncio
from dataclasses import asdict
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse, Response, StreamingResponse
from fastapi.staticfiles import StaticFiles

from app.api.schemas import (
    AnalyticsSummaryResponse,
    CameraResponse,
    EventListResponse,
    EventResponse,
    HealthResponse,
)
from app.runtime import get_runtime
from app.webrtc import WebRTCAnswer, WebRTCOffer


def create_app() -> FastAPI:
    runtime = get_runtime()
    app = FastAPI(title="IA CCTV PYRGOS", version="0.1.0")
    web_dir = Path(__file__).resolve().parent.parent / "web"

    app.state.runtime = runtime
    app.state.peer_connections = set()
    app.mount("/assets", StaticFiles(directory=web_dir / "assets"), name="assets")

    @app.get("/", include_in_schema=False)
    def dashboard() -> FileResponse:
        return FileResponse(web_dir / "index.html")

    @app.get("/health", response_model=HealthResponse)
    def health() -> HealthResponse:
        storage_backend = app.state.runtime.event_service.repository.__class__.__name__
        return HealthResponse(
            storage_backend=storage_backend,
            database_configured=bool(app.state.runtime.settings.database_url),
        )

    @app.get("/api/cameras", response_model=list[CameraResponse])
    def list_cameras() -> list[CameraResponse]:
        return [CameraResponse.model_validate(asdict(app.state.runtime.camera_status))]

    @app.get("/api/events", response_model=EventListResponse)
    def list_events(
        limit: int = Query(default=50, ge=1, le=500),
        camera_id: str | None = None,
    ) -> EventListResponse:
        items = [
            EventResponse.model_validate(event)
            for event in app.state.runtime.event_service.list_events(
                limit=limit,
                camera_id=camera_id,
            )
        ]
        return EventListResponse(items=items, count=len(items))

    @app.get("/api/analytics/summary", response_model=AnalyticsSummaryResponse)
    def analytics_summary(
        camera_id: str | None = None,
        recent_window_minutes: int = Query(default=10, ge=1, le=1440),
    ) -> AnalyticsSummaryResponse:
        summary = app.state.runtime.event_service.analytics_summary(
            camera_id=camera_id,
            recent_window_minutes=recent_window_minutes,
        )
        return AnalyticsSummaryResponse(
            total_events=summary.total_events,
            counts_by_label=summary.counts_by_label,
            recent_counts_by_label=summary.recent_counts_by_label,
            recent_activity_count=summary.recent_activity_count,
            recent_window_minutes=summary.recent_window_minutes,
            latest_event=(
                EventResponse.model_validate(summary.latest_event)
                if summary.latest_event is not None
                else None
            ),
        )

    @app.get("/api/stream.mjpg")
    async def mjpeg_stream() -> StreamingResponse:
        from app.webrtc.rtsp_video import RTSPCamera
        import cv2

        camera = RTSPCamera(runtime.camera_status.stream_url, runtime=runtime)

        async def generate():
            try:
                while True:
                    frame = await asyncio.to_thread(camera.read)
                    ok, encoded = cv2.imencode(".jpg", frame)
                    if not ok:
                        runtime.camera_status.last_error = (
                            "No se pudo codificar el frame JPEG del stream MJPEG."
                        )
                        break
                    payload = encoded.tobytes()
                    yield (
                        b"--frame\r\n"
                        b"Content-Type: image/jpeg\r\n\r\n" + payload + b"\r\n"
                    )
                    await asyncio.sleep(0.03)
            except Exception as exc:
                runtime.camera_status.connected = False
                runtime.camera_status.last_error = str(exc)
            finally:
                camera.close()

        return StreamingResponse(
            generate(),
            media_type="multipart/x-mixed-replace; boundary=frame",
        )

    @app.get("/api/frame.jpg")
    async def jpeg_frame() -> Response:
        from app.webrtc.rtsp_video import RTSPCamera
        import cv2

        camera = RTSPCamera(runtime.camera_status.stream_url, runtime=runtime)
        try:
            frame = await asyncio.to_thread(camera.read)
            ok, encoded = cv2.imencode(".jpg", frame)
            if not ok:
                runtime.camera_status.last_error = (
                    "No se pudo codificar el frame JPEG del snapshot."
                )
                raise HTTPException(
                    status_code=500,
                    detail="No se pudo codificar el frame JPEG del snapshot.",
                )
            return Response(content=encoded.tobytes(), media_type="image/jpeg")
        except HTTPException:
            raise
        except Exception as exc:
            runtime.camera_status.connected = False
            runtime.camera_status.last_error = str(exc)
            raise HTTPException(status_code=503, detail=str(exc)) from exc
        finally:
            camera.close()

    @app.post("/api/webrtc/offer", response_model=WebRTCAnswer)
    async def webrtc_offer(offer: WebRTCOffer) -> WebRTCAnswer:
        try:
            from aiortc import RTCPeerConnection, RTCSessionDescription
        except ImportError as exc:
            raise HTTPException(
                status_code=503,
                detail="WebRTC no esta instalado en este entorno.",
            ) from exc

        from app.webrtc.rtsp_video import build_webrtc_video_track

        pc = RTCPeerConnection()
        app.state.peer_connections.add(pc)
        video_track = build_webrtc_video_track(
            runtime.camera_status.stream_url,
            runtime=runtime,
        )
        pc.addTrack(video_track)

        @pc.on("connectionstatechange")
        async def on_connectionstatechange():
            if pc.connectionState in {"failed", "closed", "disconnected"}:
                video_track.stop()
                await pc.close()
                app.state.peer_connections.discard(pc)

        try:
            await pc.setRemoteDescription(
                RTCSessionDescription(sdp=offer.sdp, type=offer.type)
            )
            answer = await pc.createAnswer()
            await pc.setLocalDescription(answer)
        except Exception as exc:
            video_track.stop()
            await pc.close()
            app.state.peer_connections.discard(pc)
            raise HTTPException(status_code=400, detail=f"Oferta WebRTC invalida: {exc}") from exc

        return WebRTCAnswer(
            sdp=pc.localDescription.sdp,
            type=pc.localDescription.type,
        )

    @app.on_event("shutdown")
    async def shutdown_event() -> None:
        for pc in list(app.state.peer_connections):
            await pc.close()
        app.state.peer_connections.clear()

    return app
