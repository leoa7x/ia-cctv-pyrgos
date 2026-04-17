# Current State

Fecha de referencia: 2026-04-16

## Estado operativo

El sistema ya funciona de punta a punta en Windows con esta ruta:

1. `go2rtc` como relay local para la Tapo C200
2. panel nativo como frontend principal
3. RF-DETR corriendo sobre la GPU RTX 3050
4. eventos y analitica persistidos en SQLite compartido
5. Ollama consultando esos eventos desde el panel
6. primer corte multipantalla en el panel nativo

## Flujo actual correcto

Orden de arranque:

1. [`run_go2rtc_tapo.bat`](/mnt/c/Users/ingel/OneDrive/Documentos/CODEX/ia-cctv-pyrgos/run_go2rtc_tapo.bat)
2. [`run_tapo_local.bat`](/mnt/c/Users/ingel/OneDrive/Documentos/CODEX/ia-cctv-pyrgos/run_tapo_local.bat)
3. opcional: [`run_tapo_api.bat`](/mnt/c/Users/ingel/OneDrive/Documentos/CODEX/ia-cctv-pyrgos/run_tapo_api.bat)

## Fuente de video actual

- camara: TP-Link Tapo C200
- RTSP real: `rtsp://analitica:C9p5au8naa@192.168.2.161:554/stream2`
- relay local: `rtsp://127.0.0.1:8554/tapo_c200`
- acceso validado desde WSL: `rtsp://192.168.2.60:8554/tapo_c200`

## Multipantalla

Ya existe una primera base multipantalla para el panel nativo.

Se configura con:

- `PYRGOS_CAMERAS`

Formato:

- `camera_id|rtsp_url|nombre_visible;camera_id|rtsp_url|nombre_visible`

Ejemplo:

- `tapo|rtsp://127.0.0.1:8554/tapo_c200|Tapo Principal;drone|rtsp://127.0.0.1:8554/drone_cam|Drone`

Archivo ejemplo:

- [`run_multicam_local.example.bat`](/mnt/c/Users/ingel/OneDrive/Documentos/CODEX/ia-cctv-pyrgos/run_multicam_local.example.bat)

Alcance actual:

- multipantalla en el panel nativo
- estado por camara
- eventos compartidos con `camera_id`
- analitica e IA sobre todas las camaras

Pendiente mas adelante:

- filtros por camara en la UI
- endpoints web de video por camara
- layouts operativos mas finos

## Persistencia actual

No se instalo PostgreSQL en esta maquina.

Para no bloquear el proyecto, la persistencia compartida actual es SQLite:

- DB local: `C:/Users/ingel/OneDrive/Documentos/CODEX/ia-cctv-pyrgos/data/pyrgos.db`
- DSN usado por scripts: `sqlite:///C:/Users/ingel/OneDrive/Documentos/CODEX/ia-cctv-pyrgos/data/pyrgos.db`

Esto permite que:

- panel nativo
- API local
- IA con Ollama

lean y escriban sobre la misma base.

## IA local

Ollama ya esta operativo en Windows y el modelo confirmado es:

- `deepseek-r1:8b`

Variables usadas:

- `PYRGOS_OLLAMA_HOST=http://127.0.0.1:11434`
- `PYRGOS_OLLAMA_MODEL=deepseek-r1:8b`

La IA ya responde consultas sobre eventos reales. Ya no esta vacia como al inicio.

## Lo que se afinó hoy

1. relay estable con `go2rtc` para evitar problemas RTSP directos de OpenCV
2. scripts `.bat` para no depender de recordar variables
3. tracking ligero para que el conteo no sea por frame
4. suavizado de clase por track
5. confirmacion de track antes de contar eventos
6. filtros de plausibilidad para reducir falsos `car` y `truck`
7. SQLite compartido para que panel, API e IA vean los mismos eventos

## Calibracion nocturna validada

En esta sesion se pudo por fin calibrar contra stream real desde WSL, no solo con tests.

Hallazgos operativos:

- el relay `go2rtc` si estaba bien; el bloqueo era que desde WSL no servia `127.0.0.1`
- para WSL, el stream valido quedo en `rtsp://192.168.2.60:8554/tapo_c200`
- en la escena nocturna del fondo se confirmo visualmente `4` motos y `1` carro

Ajustes que si quedaron:

- `car`: se relajo el filtro de `bottom_ratio` para no perder el carro lejano del fondo
- `person`: se rechazo una caja falsa pegada al horizonte sin tumbar la persona mas baja de la escena
- se dejo soporte para relabel de `motorcycle -> car` cuando la caja sea claramente ancha, pero no se forzo un recorte agresivo de motos porque en esta camara si hay varias motos reales al fondo

Resultado observado en la escena revisada:

- el `car` lejano vuelve a entrar de forma estable
- se elimina la `person` mas alta del horizonte
- se conservan las motos reales del fondo

Limite actual:

- queda una `person` residual mezclada cerca de una de las motos; si vuelve a molestar, el siguiente ajuste ya tendria que ser mas fino para no borrar detecciones validas

## Estado de calidad actual

Mejoras ya visibles:

- muchos menos falsos positivos que antes
- conteo mucho menos inflado
- menos saltos de clase dentro del mismo objeto
- IA respondiendo sobre datos persistidos

Todavia pendiente de afinacion:

- quedan algunos falsos positivos residuales
- el conteo aun puede desviarse un poco en escenas ambiguas
- la clasificacion `motorcycle/car/truck` todavia puede confundirse en algunos casos

## Siguiente foco recomendado

No abrir otro frente grande todavia.

El siguiente paso sensato es seguir con calibracion fina de deteccion:

- ajustar confianza
- decidir si vale pasar de `nano` a `small`
- seguir afinando reglas por clase

Solo despues de eso conviene volver a:

- analitica avanzada
- zonas
- permanencia
- cruces
- mejoras del prompt de IA

## Verificacion de codigo

Estado de test mas reciente:

- `11 passed` en `tests/test_rfdetr_detector.py`

## Commits importantes recientes

- `a97b668` Windows launch scripts for Tapo workflow
- `0c73767` Require confirmed tracks before counting events
- `105f1e5` Smooth object classes across active tracks
- `8197ecf` Filter implausible vehicle detections
- `202ef6d` Track objects to stabilize analytics counts
- `4be9dc0` Add ffmpeg stream backend for unstable RTSP cameras
- `e6a1579` Document go2rtc relay setup for Tapo camera
