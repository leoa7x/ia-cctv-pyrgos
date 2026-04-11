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
- registrar eventos recientes en memoria
- exponer API para salud, camaras, eventos y resumen analitico
- servir snapshots JPEG desde la API para diagnostico web

Estado probado en esta sesion:

- GPU detectada: `NVIDIA GeForce RTX 3050 Laptop GPU`
- PyTorch CUDA activo: `torch 2.5.1+cu121`
- tests: `12 passed`

## Arquitectura vigente

- `app/api`: API HTTP local
- `app/config`: configuracion y variables de entorno
- `app/core`: pipeline principal de captura, inferencia y render
- `app/detectors`: detectores y adaptadores de modelos
- `app/domain`: entidades de negocio
- `app/repositories`: persistencia en memoria
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
- `PYRGOS_WINDOW_NAME`: nombre del visor OpenCV de fallback
- `PYRGOS_DETECTOR_BACKEND`: `rfdetr` o `none`
- `PYRGOS_CONFIDENCE`: umbral de confianza
- `PYRGOS_TARGET_CLASSES`: clases objetivo separadas por coma
- `PYRGOS_MODEL_VARIANT`: `nano`, `small`, `medium` o `large`
- `PYRGOS_FRAME_SKIP`: salto de frames para visualizacion/procesamiento
- `PYRGOS_DETECTION_INTERVAL_FRAMES`: frecuencia de inferencia
- `PYRGOS_SHOW_FPS`: activa overlay de FPS en render OpenCV

## Arranque recomendado en Windows

### Panel nativo con deteccion GPU

```bat
cd /d C:\Users\ingel\OneDrive\Documentos\CODEX\ia-cctv-pyrgos
set PYRGOS_STREAM_URL=rtsp://192.168.2.182:8554/live.sdp
set PYRGOS_DETECTOR_BACKEND=rfdetr
.venv\Scripts\python.exe -m scripts.run_local
```

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

Esto deja la base lista para la siguiente capa: consultas con IA local sobre datos estructurados.

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
4. persistir eventos y analitica en PostgreSQL
5. montar una capa de IA local para consultas tipo:
   - que paso hoy
   - cuantas personas o carros se detectaron
   - hubo actividad inusual

## Historial reciente de direccion

Cambios relevantes ya incorporados en Git:

- activacion de GPU CUDA para RF-DETR
- panel nativo unificado con PySide6
- metricas separadas de video e inferencia
- snapshots JPEG para soporte web
- resumen analitico inicial por API
