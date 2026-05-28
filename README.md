# FutBotMX

Pipeline de vision por computadora para analizar videos de futbol robotico usando SAM 3, tracking, deteccion de eventos y visualizaciones ligeras.

Este repositorio esta configurado para trabajo en dos equipos:

- Escritorio Windows: desarrollo, documentacion, eventos, revision de CSV/JSON y entregables.
- Laptop MSI Ubuntu con RTX 4050: inferencia SAM 3, segmentacion, tracking pesado, overlays y benchmarks.

La documentacion base esta en `FutBotMX_documentacion_markdown/`.

## Estado actual

- Nivel 1 en preparacion con pipeline base de escritorio implementado.
- Estructura base del repositorio creada.
- Dependencias de escritorio definidas en `requirements-dev.txt`.
- Dependencias GPU definidas en `requirements-gpu.txt`.
- Configuracion inicial en `configs/default.yaml`.
- Python 3.12.10 instalado para este escritorio.
- Entorno virtual `.venv` creado con dependencias de desarrollo.
- Ingesta de video, tracking simple, eventos Nivel 1 y heatmap basico implementados.
- SAM 3 real pendiente de validacion en laptop MSI.

## Configuracion del escritorio

Ver `docs/SETUP_DESKTOP_WINDOWS.md`.

## Comandos principales

Activar entorno:

```powershell
.\.venv\Scripts\Activate.ps1
```

Ejecutar pruebas:

```powershell
python -m unittest discover -s tests
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

- `test_000_environment_check`: completado parcialmente en escritorio; GPU pendiente en laptop.
- `test_001_video_ingestion`: validado con prueba unitaria sintetica; clip real pendiente.
- `test_002_sam3_segmentation`: bloqueado hasta laptop MSI.
- `test_003_tracking`: validado con detecciones sinteticas.
- `test_004_events`: validado con tracks sinteticos.
- `test_005_visualizations`: heatmap sintetico generado.

## Regla principal

No subir a GitHub videos completos, checkpoints, modelos, frames masivos, mascaras masivas, datasets completos ni outputs pesados.
