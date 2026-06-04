# FutBotMX

Pipeline de vision por computadora para analizar videos de futbol robotico usando SAM 3, tracking, deteccion de eventos y visualizaciones ligeras.

Este repositorio esta configurado para trabajo en dos equipos:

- Escritorio Windows: desarrollo, documentacion, eventos, revision de CSV/JSON y entregables.
- Laptop MSI Ubuntu con RTX 4050: inferencia SAM 3, segmentacion, tracking pesado, overlays y benchmarks.

La documentacion base esta en `FutBotMX_documentacion_markdown/`.

## Estado actual

- Nivel 1 validado con SAM 3 real, ROI, ByteTrack, eventos y evidencia ligera.
- Nivel 2 cerrado con gate tecnico reproducible.
- Nivel 3 iniciado de forma controlada con readiness `10 pass`, `0 fail`.
- Estructura base del repositorio creada y usada en laptop MSI/escritorio.
- Dependencias de escritorio definidas en `requirements-dev.txt`.
- Dependencias GPU definidas en `requirements-gpu.txt`.
- Configuracion Nivel 2 en `configs/default.yaml`.
- Python 3.12.10 instalado para este escritorio.
- Entorno virtual `.venv` creado con dependencias de desarrollo.
- Ingesta, SAM 3, tracking, eventos, metricas Nivel 2 y visualizaciones implementadas.
- Videos completos, checkpoints y demos MP4 permanecen fuera de Git.

## Configuracion del escritorio

Ver `docs/SETUP_DESKTOP_WINDOWS.md`.

## Comandos principales

Activar entorno:

```powershell
.\.venv\Scripts\Activate.ps1
```

Ejecutar pruebas:

```bash
env MPLCONFIGDIR=/tmp/matplotlib .venv/bin/python -m unittest discover -s tests -q
```

Validar gates:

```bash
.venv/bin/python scripts/check_level2_readiness.py
.venv/bin/python scripts/check_level2_closure.py
.venv/bin/python scripts/check_level3_readiness.py
```

Inspeccionar un video local:

```powershell
python scripts\inspect_video.py --video data\sample\clip_01.mp4
```

Generar artefactos sinteticos de escritorio:

```powershell
python scripts\create_synthetic_level1_artifacts.py
```

Ejecutar tracking desde detecciones normalizadas:

```powershell
python scripts\run_tracking.py --detections experiments\test_003_tracking\detections.json --output outputs\tracking\tracks.csv
```

Detectar eventos desde tracks:

```powershell
python scripts\run_events.py --tracks experiments\test_003_tracking\tracks.csv --output outputs\events\events.json
```

Generar heatmap:

```powershell
python scripts\run_visualizations.py --tracks experiments\test_003_tracking\tracks.csv --heatmap outputs\visualizations\heatmap.png
```

## Estado de experimentos

- `test_000_environment_check`: entorno base documentado.
- `test_001_video_ingestion`: clips reales inspeccionados.
- `test_002_sam3_segmentation`: SAM 3 real ejecutado en laptop MSI.
- `test_003_tracking`: tracking real comparado, ByteTrack recomendado.
- `test_004_events`: eventos Nivel 1 recalculados con tracks reales.
- `test_012` a `test_016`: metricas, eventos, visualizaciones, multi-clip y demo Nivel 2.
- `test_017_level2_closure`: cierre tecnico Nivel 2 y gate hacia Nivel 3.
- `test_018_level3_readiness`: decision formal, seleccion de clips y readiness Nivel 3.

## Regla principal

No subir a GitHub videos completos, checkpoints, modelos, frames masivos, mascaras masivas, datasets completos ni outputs pesados.
