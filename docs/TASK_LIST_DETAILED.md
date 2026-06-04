# FutBotMX Task List Detallado

## Estado de Fase 0

Checklist operativo de la laptop: `docs/TODO_LAPTOP_MSI.md`.

- [x] Estructura base del repositorio creada.
- [x] `.gitignore` configurado para excluir datos y outputs pesados.
- [x] `requirements-dev.txt` y `requirements-gpu.txt` creados.
- [x] `configs/default.yaml` creado.
- [x] Python 3.12.10 instalado en escritorio.
- [x] `.venv` creado en escritorio con dependencias de desarrollo.
- [x] Commit inicial realizado: `aca0ac1`.
- [x] Push a GitHub realizado.
- [x] Configuracion de laptop MSI completada.
- [x] Validacion integral inicial con SAM 3 y clip real completada.
- [x] Validacion CUDA/PyTorch base completada en laptop MSI.
- [x] Instalacion de codigo oficial SAM 3 completada en laptop MSI.
- [x] Checkpoint oficial SAM 3 descargado y carga validada en GPU.
- [x] Validacion SAM 3 con clip real completada.

## Nivel 1 MVP

### Fase 1 - Ingesta de video

- [x] Modulo de lectura de video con OpenCV.
- [x] Extraccion de FPS, resolucion, frames y duracion.
- [x] Script CLI `scripts/inspect_video.py`.
- [x] Prueba unitaria con video sintetico.
- [x] Prueba con clip real local.
- [x] Evidencia con clip real en `experiments/test_001_video_ingestion/`.

### Fase 2 - Segmentacion con SAM 3

- [x] Wrapper de interfaz `SAM3Segmenter`.
- [x] Contrato de detecciones normalizadas.
- [x] Script CLI `scripts/run_sam3_test.py`.
- [x] Instalacion oficial SAM 3 en laptop MSI.
- [x] Acceso/autenticacion Hugging Face para checkpoints SAM 3.
- [x] Wrapper `SAM3Segmenter` conectado a inferencia SAM 3 real.
- [x] Prueba real de segmentacion de balon.
- [x] Prueba real de segmentacion de robots.
- [x] Prueba real de segmentacion de campo.
- [x] Evidencia visual ligera en `experiments/test_002_sam3_segmentation/`.

### Fase 3 - Tracking

- [x] Formato de detecciones normalizadas.
- [x] Tracker simple por centroides para desarrollo inicial.
- [x] Exportacion `tracks.csv`.
- [x] Script CLI `scripts/run_tracking.py`.
- [x] Prueba unitaria con detecciones sinteticas.
- [x] Artefacto sintetico en `experiments/test_003_tracking/`.
- [x] Prueba con detecciones reales de SAM 3.
- [x] Filtrado ROI inicial aplicado antes de tracking real.

### Fase 4 - Eventos Nivel 1

- [x] Posesion por proximidad.
- [x] Pase simple por cambio de posesion entre mismo equipo.
- [x] Tiro aproximado por velocidad y direccion.
- [x] Colision basica por distancia o bbox.
- [x] Zona de actividad basica.
- [x] Exportacion `events.json`.
- [x] Script CLI `scripts/run_events.py`.
- [x] Prueba unitaria con tracks sinteticos.
- [x] Artefacto sintetico en `experiments/test_004_events/`.
- [x] Validacion visual con datos reales.
- [x] Eventos recalculados con tracks reales filtrados por ROI.

### Fase 5 - Visualizaciones Nivel 1

- [x] Heatmap basico desde `tracks.csv`.
- [x] Overlay de frame con bbox, centroide e ID.
- [x] Script CLI `scripts/run_visualizations.py`.
- [x] Prueba unitaria de heatmap.
- [x] Artefacto sintetico en `experiments/test_005_visualizations/`.
- [x] Overlay con video real generado en laptop.
- [x] Overlays comparativos antes/despues de ROI generados en laptop.

### Fase 6 - Exportacion y reproducibilidad

- [x] Outputs minimos definidos: `tracks.csv`, `events.json`, `metrics.csv`, `summary.md`, `config.yaml`.
- [x] Config snapshots por experimento sintetico.
- [x] Tests de escritorio reproducibles.
- [x] Commit hash real agregado despues de commit inicial.
- [x] Resultados reales de laptop documentados.
- [x] Experimento de estabilidad temporal con `frame_stride=1/3/5` documentado.
- [x] Prompts base de SAM 3 seleccionados con evidencia real.
- [x] Tracking real comparado entre tracker simple y ByteTrack.
- [x] Eventos Nivel 1 recalculados y calibrados con tracks reales ByteTrack.
- [x] Paquete de evidencia ligera Nivel 1 creado en `experiments/evidence_level1/`.
- [x] Script reproducible para reconstruir evidencia ligera: `scripts/build_level1_evidence_package.py`.
- [x] Reporte automatico de validacion Nivel 1: `scripts/run_level1_validation_report.py`.
- [x] Limpieza de detecciones por NMS/top-k implementada antes de eventos multi-clip.

### Fase 7 - Documentacion y demo

- [x] README actualizado con pipeline, comandos y estado.
- [x] Task list versionado.
- [x] Capturas reales de overlay.
- [x] Fragmento real de `events.json` desde SAM 3/tracking.
- [x] Cinco recomendaciones de solidez Nivel 1 documentadas en `docs/LEVEL1_SOLIDITY_RECOMMENDATIONS.md`.
- [x] Demo local o video anotado generado en laptop.

## Nivel 2 - Extension Intermedia

Estado operativo: implementado; cierre tecnico en `experiments/test_017_level2_closure/`.

Checklist operativo: `docs/TODO_LEVEL2.md`.

- [x] Gate de desbloqueo Nivel 2 ejecutado.
- [x] Nivel 1 validado con `10 pass`, `0 warn`, `0 fail`.
- [x] Demo local Nivel 1 documentada.
- [x] Archivos pesados fuera de Git.
- [x] Prioridad 1 - Metricas deportivas intermedias.
- [x] Prioridad 2 - Eventos intermedios.
- [x] Prioridad 3 - Visualizaciones Nivel 2.
- [x] Prioridad 4 - Multi-clip real.
- [x] Prioridad 5 - Demo Nivel 2.
- [x] Gate de cierre tecnico Nivel 2 agregado: `scripts/check_level2_closure.py`.

## Backlog Nivel 3

Nivel 3 no esta iniciado. Queda listo para gate/decision cuando el cierre Nivel 2 pase sin checks fallidos.
