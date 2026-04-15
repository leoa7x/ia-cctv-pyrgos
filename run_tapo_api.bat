@echo off
setlocal

cd /d C:\Users\ingel\OneDrive\Documentos\CODEX\ia-cctv-pyrgos

set PYRGOS_STREAM_URL=rtsp://127.0.0.1:8554/tapo_c200
set PYRGOS_STREAM_BACKEND=opencv
set PYRGOS_DETECTOR_BACKEND=rfdetr
set PYRGOS_CONFIDENCE=0.35
set PYRGOS_TARGET_CLASSES=person,motorcycle,car,bus,truck,dog,cat
set PYRGOS_DETECTION_INTERVAL_FRAMES=12
set PYRGOS_TRACK_CONFIRMATION_HITS=2
set PYRGOS_DATABASE_URL=sqlite:///C:/Users/ingel/OneDrive/Documentos/CODEX/ia-cctv-pyrgos/data/pyrgos.db
set PYRGOS_OLLAMA_HOST=http://127.0.0.1:11434
set PYRGOS_OLLAMA_MODEL=deepseek-r1:8b
set PYRGOS_OLLAMA_TIMEOUT_SECONDS=180
set PYRGOS_OLLAMA_RECENT_EVENTS_LIMIT=5

.venv\Scripts\python.exe -m uvicorn scripts.run_api:app --host 127.0.0.1 --port 8000
