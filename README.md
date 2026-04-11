# IA CCTV PYRGOS

Aplicacion de vision para CCTV sobre stream IP. El primer objetivo es usar un iPhone como camara IP, leer el stream desde un PC y ejecutar deteccion en vivo de personas, carros, motos, buses y camiones.

## Objetivo inicial

- leer stream IP del iPhone
- ejecutar deteccion en tiempo real
- visualizar cajas y etiquetas
- dejar base lista para eventos, alertas y grabacion

## Arquitectura

- `app/api`: API HTTP para salud, camaras y eventos
- `app/config`: configuracion del sistema
- `app/core`: pipeline principal
- `app/detectors`: detectores y adaptadores de modelos
- `app/domain`: entidades de negocio
- `app/repositories`: persistencia de eventos
- `app/services`: logica de eventos y orquestacion
- `app/stream`: lectura de stream IP
- `app/ui`: render OpenCV
- `scripts`: comandos de arranque

## Estado actual

Base del proyecto preparada para:

- configurar URL de stream
- seleccionar clases objetivo
- conectar detector RF-DETR
- mostrar video procesado con OpenCV
- exponer API FastAPI de salud, camaras y eventos
- exponer dashboard web local
- dejar base lista para dashboard y consultas con LLM

## Variables de entorno

- `PYRGOS_STREAM_URL`: URL del stream IP del iPhone
- `PYRGOS_WINDOW_NAME`: nombre de la ventana OpenCV
- `PYRGOS_DETECTOR_BACKEND`: `rfdetr` o `none`
- `PYRGOS_CONFIDENCE`: umbral minimo de confianza
- `PYRGOS_TARGET_CLASSES`: clases separadas por coma
- `PYRGOS_MODEL_VARIANT`: variante del modelo RF-DETR

## Arranque principal

```bash
python -m scripts.run_local
```

El arranque principal ahora abre un panel nativo unificado para:

- video en vivo
- cajas de deteccion y etiquetas
- eventos recientes
- metricas operativas

Para usar el panel nativo instala tambien el extra `desktop`:

```bash
pip install -e .[dev,desktop]
```

Modo API:

```bash
uvicorn scripts.run_api:app --reload
```

## Prueba rapida en Windows

Para probar sin instalar RF-DETR todavia, arranca en modo `stream-only`:

```bat
cd /d C:\Users\ingel\OneDrive\Documentos\CODEX\ia-cctv-pyrgos
py -3.12 -m venv .venv
.venv\Scripts\python -m pip install -e .[dev]
set PYRGOS_STREAM_URL=rtsp://192.168.2.182:8554/live.sdp
set PYRGOS_DETECTOR_BACKEND=none
.venv\Scripts\python -m uvicorn scripts.run_api:app --host 127.0.0.1 --port 8000
```

Luego abre:

- `http://127.0.0.1:8000/`
- `http://127.0.0.1:8000/health`

Si quieres ejecutar la ventana OpenCV en vez de la API:

```bat
set PYRGOS_STREAM_URL=rtsp://192.168.2.182:8554/live.sdp
set PYRGOS_DETECTOR_BACKEND=none
.venv\Scripts\python -m scripts.run_local
```

Endpoints iniciales:

- `GET /`
- `GET /health`
- `GET /api/cameras`
- `GET /api/events`

Dashboard:

- `GET /` sirve una interfaz web local para estado de camara y eventos
- el video web ahora usa WebRTC de baja latencia
- la fuente original sigue siendo RTSP
- se requiere instalar `aiortc` y `av` en el entorno que corra el backend

## Siguiente paso practico

1. terminar instalacion CPU de RF-DETR
2. registrar detecciones reales como eventos
3. persistir eventos en PostgreSQL
4. agregar dashboard web y capa Ollama para consultas
