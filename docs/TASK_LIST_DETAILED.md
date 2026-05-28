# FutBotMX Task List Detallado

## Estado de Fase 0

- [x] Estructura base del repositorio creada.
- [x] `.gitignore` configurado para excluir datos y outputs pesados.
- [x] `requirements-dev.txt` y `requirements-gpu.txt` creados.
- [x] `configs/default.yaml` creado.
- [x] Python 3.12.10 instalado en escritorio.
- [x] `.venv` creado en escritorio con dependencias de desarrollo.
- [x] Commit inicial realizado: `aca0ac1`.
- [x] Push a GitHub realizado.
- [ ] Configuracion de laptop MSI pendiente.
- [ ] Validacion CUDA/PyTorch/SAM 3 pendiente.

## Nivel 1 MVP

### Fase 1 - Ingesta de video

- [x] Modulo de lectura de video con OpenCV.
- [x] Extraccion de FPS, resolucion, frames y duracion.
- [x] Script CLI `scripts/inspect_video.py`.
- [x] Prueba unitaria con video sintetico.
- [ ] Prueba con clip real local.
- [ ] Evidencia con clip real en `experiments/test_001_video_ingestion/`.

### Fase 2 - Segmentacion con SAM 3

- [x] Wrapper de interfaz `SAM3Segmenter`.
- [x] Contrato de detecciones normalizadas.
- [x] Script CLI `scripts/run_sam3_test.py`.
- [ ] Instalacion oficial SAM 3 en laptop MSI.
- [ ] Prueba real de segmentacion de balon.
- [ ] Prueba real de segmentacion de robots.
- [ ] Prueba real de segmentacion de campo.
- [ ] Evidencia visual ligera en `experiments/test_002_sam3_segmentation/`.

### Fase 3 - Tracking

- [x] Formato de detecciones normalizadas.
- [x] Tracker simple por centroides para desarrollo inicial.
- [x] Exportacion `tracks.csv`.
- [x] Script CLI `scripts/run_tracking.py`.
- [x] Prueba unitaria con detecciones sinteticas.
- [x] Artefacto sintetico en `experiments/test_003_tracking/`.
- [ ] Prueba con detecciones reales de SAM 3.

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
- [ ] Validacion visual con datos reales.

### Fase 5 - Visualizaciones Nivel 1

- [x] Heatmap basico desde `tracks.csv`.
- [x] Overlay de frame con bbox, centroide e ID.
- [x] Script CLI `scripts/run_visualizations.py`.
- [x] Prueba unitaria de heatmap.
- [x] Artefacto sintetico en `experiments/test_005_visualizations/`.
- [ ] Overlay con video real generado en laptop.

### Fase 6 - Exportacion y reproducibilidad

- [x] Outputs minimos definidos: `tracks.csv`, `events.json`, `metrics.csv`, `summary.md`, `config.yaml`.
- [x] Config snapshots por experimento sintetico.
- [x] Tests de escritorio reproducibles.
- [x] Commit hash real agregado despues de commit inicial.
- [ ] Resultados reales de laptop documentados.

### Fase 7 - Documentacion y demo

- [x] README actualizado con pipeline, comandos y estado.
- [x] Task list versionado.
- [ ] Capturas reales de overlay.
- [ ] Fragmento real de `events.json` desde SAM 3/tracking.
- [ ] Demo local o video anotado generado en laptop.

## Backlog bloqueado

Nivel 2 y Nivel 3 permanecen bloqueados hasta validar Nivel 1 con evidencia real de SAM 3 en la laptop MSI.
