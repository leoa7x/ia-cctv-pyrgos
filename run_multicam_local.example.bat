@echo off
setlocal

cd /d C:\Users\ingel\OneDrive\Documentos\CODEX\ia-cctv-pyrgos

rem Formato: camera_id|rtsp_url|nombre_visible;camera_id|rtsp_url|nombre_visible
set "PYRGOS_CAMERAS=tapo|rtsp://127.0.0.1:8554/tapo_c200|Tapo Principal;drone|rtsp://127.0.0.1:8554/drone_cam|Drone"
set PYRGOS_STREAM_BACKEND=opencv
set PYRGOS_DETECTOR_BACKEND=rfdetr
set PYRGOS_DATABASE_URL=sqlite:///C:/Users/ingel/OneDrive/Documentos/CODEX/ia-cctv-pyrgos/data/pyrgos.db
set PYRGOS_OLLAMA_HOST=http://127.0.0.1:11434
set PYRGOS_OLLAMA_MODEL=deepseek-r1:8b
set PYRGOS_OLLAMA_TIMEOUT_SECONDS=180
set PYRGOS_OLLAMA_RECENT_EVENTS_LIMIT=5

.venv\Scripts\python.exe -m scripts.run_local
