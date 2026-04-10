from __future__ import annotations

from dataclasses import asdict
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api.schemas import CameraResponse, EventListResponse, EventResponse, HealthResponse
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
        return HealthResponse()

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
