# IA CCTV PYRGOS

Sistema local de vision para CCTV orientado a:

- consumir video RTSP desde una camara IP
- ejecutar deteccion en vivo con RF-DETR
- visualizar cajas, clase y confianza en tiempo real
- registrar eventos estructurados para analitica
- preparar una capa futura de IA local sobre esos eventos

## Objetivo actual

El objetivo operativo del proyecto ya no es una web como frontend principal. La decision tomada fue:

- frontend principal: panel nativo unificado
- frontend secundario: API/web local para estado, pruebas y soporte
- foco tecnico: `RTSP -> deteccion -> eventos -> analitica -> IA local`

## Estado actual

Actualmente el proyecto ya puede:

- abrir el RTSP del iPhone
- correr RF-DETR en la GPU NVIDIA del equipo
- mostrar video en vivo con cajas y etiquetas en un panel nativo
- mostrar metricas separadas de `Video FPS` e `Inference FPS`
- registrar eventos recientes en memoria o PostgreSQL
- exponer API para salud, camaras, eventos y resumen analitico
- servir snapshots JPEG desde la API para diagnostico web

Estado probado en esta sesion:

- GPU detectada: `NVIDIA GeForce RTX 3050 Laptop GPU`
- PyTorch CUDA activo: `torch 2.5.1+cu121`
- Ollama operativo con `deepseek-r1:8b`
- relay local con `go2rtc` para Tapo C200
- persistencia compartida local con SQLite
- primer soporte multipantalla en panel nativo
- tests: `33 passed`

## Arquitectura vigente

- `app/api`: API HTTP local
- `app/config`: configuracion y variables de entorno
- `app/core`: pipeline principal de captura, inferencia y render
- `app/detectors`: detectores y adaptadores de modelos
- `app/domain`: entidades de negocio
- `app/repositories`: persistencia en memoria y PostgreSQL
- `app/services`: eventos y analitica
- `app/stream`: lectura RTSP
- `app/ui`: panel nativo y render OpenCV
- `scripts`: comandos de arranque

## Frontend principal

El frontend principal es el panel nativo lanzado por:

```bash
python -m scripts.run_local
```

Ese panel muestra:

- video en vivo
- cajas de deteccion
- clase y confianza
- eventos recientes
- estado de camara
- `Video FPS`
- `Inference FPS`
- chat local para consultar la actividad reciente via Ollama

Si `PySide6` no esta disponible, el proyecto cae a un visor OpenCV como fallback.

## Frontend web

La capa web queda como soporte local, no como experiencia principal de operacion.

Sirve para:

- `/health`
- `/api/cameras`
- `/api/events`
- `/api/analytics/summary`
- `/api/frame.jpg`

Notas:

- la web no es el camino principal para video en vivo
- WebRTC sigue pendiente porque `aiortc/av` no quedaron operativos en este entorno Windows
- los snapshots JPEG si funcionan como diagnostico

## Variables de entorno

- `PYRGOS_STREAM_URL`: URL RTSP de la camara
- `PYRGOS_CAMERAS`: lista de camaras en formato `camera_id|rtsp_url|nombre;camera_id|rtsp_url|nombre`
- `PYRGOS_STREAM_BACKEND`: `opencv` o `ffmpeg`
- `PYRGOS_FFMPEG_PATH`: ruta de `ffmpeg.exe` cuando se usa backend `ffmpeg`
- `PYRGOS_WINDOW_NAME`: nombre del visor OpenCV de fallback
- `PYRGOS_DETECTOR_BACKEND`: `rfdetr` o `none`
- `PYRGOS_CONFIDENCE`: umbral de confianza
- `PYRGOS_DATABASE_URL`: cadena de conexion PostgreSQL
- `PYRGOS_TARGET_CLASSES`: clases objetivo separadas por coma
- `PYRGOS_MODEL_VARIANT`: `nano`, `small`, `medium` o `large`
- `PYRGOS_FRAME_SKIP`: salto de frames para visualizacion/procesamiento
- `PYRGOS_DETECTION_INTERVAL_FRAMES`: frecuencia de inferencia
- `PYRGOS_SHOW_FPS`: activa overlay de FPS en render OpenCV

Archivo base recomendado:

- copiar `.env.example` a `.env` y ajustar segun el entorno

Variables para IA local:

- `PYRGOS_OLLAMA_HOST` o `OLLAMA_HOST`
- `PYRGOS_OLLAMA_MODEL` o `OLLAMA_MODEL`
- `PYRGOS_OLLAMA_TIMEOUT_SECONDS`
- `PYRGOS_OLLAMA_RECENT_EVENTS_LIMIT`

## Arranque recomendado en Windows

### Panel nativo con deteccion GPU

```bat
cd /d C:\Users\ingel\OneDrive\Documentos\CODEX\ia-cctv-pyrgos
set PYRGOS_STREAM_URL=rtsp://192.168.2.182:8554/live.sdp
set PYRGOS_DETECTOR_BACKEND=rfdetr
.venv\Scripts\python.exe -m scripts.run_local
```

### Panel nativo usando ingestión por ffmpeg

Ruta recomendada para camaras que VLC abre bien pero OpenCV no decodifica estable.

```bat
cd /d C:\Users\ingel\OneDrive\Documentos\CODEX\ia-cctv-pyrgos
set PYRGOS_STREAM_URL=rtsp://analitica:C9p5au8naa@192.168.2.161:554/stream2
set PYRGOS_STREAM_BACKEND=ffmpeg
set PYRGOS_FFMPEG_PATH=C:\Program Files\WindowsApps\Microsoft.PowerAutomateDesktop_11.2603.154.0_x64__8wekyb3d8bbwe\dotnet\x64\ffmpeg\ffmpeg.exe
set PYRGOS_DETECTOR_BACKEND=rfdetr
set PYRGOS_OLLAMA_HOST=http://127.0.0.1:11434
set PYRGOS_OLLAMA_MODEL=deepseek-r1:8b
.venv\Scripts\python.exe -m scripts.run_local
```

### Arranque rapido en Windows para la Tapo via go2rtc

Si ya dejaste `go2rtc.exe` en `C:\Users\ingel\OneDrive\Documentos\CODEX\go2rtc`, usa estos scripts del repo:

- [`run_go2rtc_tapo.bat`](/mnt/c/Users/ingel/OneDrive/Documentos/CODEX/ia-cctv-pyrgos/run_go2rtc_tapo.bat)
- [`run_tapo_local.bat`](/mnt/c/Users/ingel/OneDrive/Documentos/CODEX/ia-cctv-pyrgos/run_tapo_local.bat)
- [`run_tapo_api.bat`](/mnt/c/Users/ingel/OneDrive/Documentos/CODEX/ia-cctv-pyrgos/run_tapo_api.bat)

Orden recomendado:

1. ejecutar `run_go2rtc_tapo.bat`
2. ejecutar `run_tapo_local.bat`
3. opcional: ejecutar `run_tapo_api.bat`

### Multipantalla en panel nativo

Si quieres abrir varias fuentes en una sola ventana, usa `PYRGOS_CAMERAS`.

Formato:

```bat
set "PYRGOS_CAMERAS=tapo|rtsp://127.0.0.1:8554/tapo_c200|Tapo Principal;drone|rtsp://127.0.0.1:8554/drone_cam|Drone"
```

Ejemplo de arranque:

```bat
cd /d C:\Users\ingel\OneDrive\Documentos\CODEX\ia-cctv-pyrgos
set "PYRGOS_CAMERAS=tapo|rtsp://127.0.0.1:8554/tapo_c200|Tapo Principal;drone|rtsp://127.0.0.1:8554/drone_cam|Drone"
set PYRGOS_STREAM_BACKEND=opencv
set PYRGOS_DETECTOR_BACKEND=rfdetr
set PYRGOS_DATABASE_URL=sqlite:///C:/Users/ingel/OneDrive/Documentos/CODEX/ia-cctv-pyrgos/data/pyrgos.db
set PYRGOS_OLLAMA_HOST=http://127.0.0.1:11434
set PYRGOS_OLLAMA_MODEL=deepseek-r1:8b
.venv\Scripts\python.exe -m scripts.run_local
```

Tambien deje un ejemplo editable:

- [`run_multicam_local.example.bat`](/mnt/c/Users/ingel/OneDrive/Documentos/CODEX/ia-cctv-pyrgos/run_multicam_local.example.bat)

### Variante mas ligera para priorizar fluidez

```bat
cd /d C:\Users\ingel\OneDrive\Documentos\CODEX\ia-cctv-pyrgos
set PYRGOS_STREAM_URL=rtsp://192.168.2.182:8554/live.sdp
set PYRGOS_DETECTOR_BACKEND=rfdetr
set PYRGOS_MODEL_VARIANT=nano
set PYRGOS_CONFIDENCE=0.45
.venv\Scripts\python.exe -m scripts.run_local
```

### API local

```bat
cd /d C:\Users\ingel\OneDrive\Documentos\CODEX\ia-cctv-pyrgos
set PYRGOS_STREAM_URL=rtsp://192.168.2.182:8554/live.sdp
set PYRGOS_DETECTOR_BACKEND=rfdetr
.venv\Scripts\python.exe -m uvicorn scripts.run_api:app --host 127.0.0.1 --port 8000
```

## Instalacion

### Entorno base

```bash
pip install -e .[dev]
```

### Panel nativo

```bash
pip install -e .[dev,desktop]
```

### RF-DETR

```bash
pip install -e .[rfdetr]
```

Importante:

- en este proyecto se termino instalando PyTorch CUDA en Windows manualmente para activar la RTX 3050
- si el entorno vuelve a quedar en CPU, revisar `torch.cuda.is_available()`

## Analitica disponible

Ya existe una primera capa de analitica basada en eventos:

- total de eventos
- conteo por clase
- actividad reciente por ventana de tiempo
- ultimo evento detectado

Endpoint:

- `GET /api/analytics/summary`

Salud operativa:

- `GET /health`
- ahora indica tambien si el runtime esta usando memoria o PostgreSQL
- `POST /api/ai/chat`

Esto deja la base lista para la siguiente capa: consultas con IA local sobre datos estructurados.

## Persistencia y contenedores

La base del proyecto ya puede persistir eventos en PostgreSQL cuando `PYRGOS_DATABASE_URL` esta configurado.

Si no se define, el sistema sigue usando repositorio en memoria para desarrollo rapido.

Para Windows local, la ruta mas pragmatica ahora es SQLite compartido:

```text
sqlite:///C:/Users/ingel/OneDrive/Documentos/CODEX/ia-cctv-pyrgos/data/pyrgos.db
```

Eso permite que panel nativo, API e IA consulten la misma base sin instalar PostgreSQL.

### Levantar PostgreSQL y API con Docker Compose

```bash
docker compose up --build
```

Servicios incluidos:

- `postgres`: base de datos persistente para eventos
- `api`: FastAPI conectada a PostgreSQL

Conexion interna por defecto:

```text
postgresql://pyrgos:pyrgos@postgres:5432/pyrgos
```

Ejemplo para desarrollo local fuera de Docker:

```bash
export PYRGOS_DATABASE_URL=postgresql://pyrgos:pyrgos@127.0.0.1:5432/pyrgos
```

Ejemplo local sin PostgreSQL:

```bat
set PYRGOS_DATABASE_URL=sqlite:///C:/Users/ingel/OneDrive/Documentos/CODEX/ia-cctv-pyrgos/data/pyrgos.db
```

Si el servicio esta levantado correctamente, `GET /health` deberia mostrar:

```json
{
  "status": "ok",
  "app_name": "IA CCTV PYRGOS",
  "storage_backend": "PostgresEventRepository",
  "database_configured": true
}
```

## IA local con Ollama

Ya existe una primera integracion para consultas locales sobre eventos y analitica.

Endpoint:

- `POST /api/ai/chat`

Ejemplo:

```json
{
  "question": "Que paso en los ultimos 10 minutos?",
  "camera_id": "iphone-main",
  "recent_window_minutes": 10
}
```

La respuesta se construye sobre:

- resumen analitico actual
- conteos por clase
- conteos recientes
- ultimos eventos registrados

La IA no consume video crudo. Consume datos estructurados.

## Estado documentado

Resumen operativo actualizado:

- [`CURRENT_STATE.md`](/mnt/c/Users/ingel/OneDrive/Documentos/CODEX/ia-cctv-pyrgos/CURRENT_STATE.md)

## go2rtc para camaras RTSP conflictivas

Cuando VLC abre una camara pero `OpenCV` o el backend RTSP directo no son estables, la ruta recomendada es usar `go2rtc` como relay local.

Configuracion base incluida:

- [`go2rtc.yaml.example`](/mnt/c/Users/ingel/OneDrive/Documentos/CODEX/ia-cctv-pyrgos/go2rtc.yaml.example)

La sintaxis esta basada en la documentacion oficial de go2rtc:

- https://go2rtc.org/internal/rtsp/
- https://github.com/AlexxIT/go2rtc

Para la Tapo C200 de este proyecto:

```yaml
streams:
  tapo_c200:
    - rtsp://analitica:C9p5au8naa@192.168.2.161:554/stream2
```

Una vez corriendo go2rtc, el proyecto puede consumir este relay local:

```text
rtsp://127.0.0.1:8554/tapo_c200
```

Arranque recomendado del panel usando relay local:

```bat
cd /d C:\Users\ingel\OneDrive\Documentos\CODEX\ia-cctv-pyrgos
set PYRGOS_STREAM_URL=rtsp://127.0.0.1:8554/tapo_c200
set PYRGOS_STREAM_BACKEND=opencv
set PYRGOS_DETECTOR_BACKEND=rfdetr
set PYRGOS_OLLAMA_HOST=http://127.0.0.1:11434
set PYRGOS_OLLAMA_MODEL=deepseek-r1:8b
.venv\Scripts\python.exe -m scripts.run_local
```

## Decision tecnica tomada

Para no perder el rumbo, el proyecto queda orientado asi:

1. panel nativo unificado como producto operativo principal
2. API/eventos/analitica como capa de soporte
3. web local como herramienta secundaria
4. IA local futura sobre eventos y analitica, no sobre video crudo

## Proximos pasos recomendados

1. integrar el resumen analitico dentro del panel nativo
2. desacoplar aun mas captura, render e inferencia para mejorar sensacion de fluidez
3. agregar analitica operativa real:
   - conteos por clase
   - actividad por intervalos
   - permanencia
   - zonas y cruces
4. integrar el chat de IA local en el panel nativo
5. enriquecer el contexto que recibe Ollama con:
   - zonas
   - permanencia
   - cruces
   - ventanas historicas
6. separar servicios de vision, API y LLM local para crecer sin convertir esto en un monolito inmanejable

## Historial reciente de direccion

Cambios relevantes ya incorporados en Git:

- activacion de GPU CUDA para RF-DETR
- panel nativo unificado con PySide6
- metricas separadas de video e inferencia
- snapshots JPEG para soporte web
- resumen analitico inicial por API
- backend alterno de stream via `ffmpeg` para RTSP conflictivos
