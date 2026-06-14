# Uso Del Reproductor Vivo — FutBotMX

Guia de uso de la extension Post-Nivel 3 para reproduccion con overlays sincronizados.

---

## Requisitos Previos

- Python >= 3.10 con el paquete `futbotmx` instalado en modo editable.
- Artefactos precomputados del clip deseado (`level3_tracks.csv`, `level3_events.json`, etc.).
- Video local en un path accesible para el servidor (permanece fuera de Git).

Instalar en modo editable:

```bash
pip install -e .
```

---

## Comandos Para Arrancar La App

### Modo rapido — smoke test (sin video, verifica artefactos)

```bash
python scripts/run_live_playback_app.py \
    --experiment experiments/test_039_live_playback \
    --clip-id video_595 \
    --smoke-test
```

Genera evidencia ligera en el directorio del experimento y sale sin levantar servidor.

### Modo normal — playback precomputado

```bash
python scripts/run_live_playback_app.py \
    --experiment experiments/test_039_live_playback \
    --clip-id video_595 \
    --video /ruta/local/video_595.mp4 \
    --inference-mode precomputed \
    --host 127.0.0.1 \
    --port 8766
```

Luego abrir en navegador: `http://127.0.0.1:8766/`

### Opciones completas

| Argumento | Descripcion | Valor por defecto |
|-----------|-------------|-------------------|
| `--experiment` | Directorio del experimento con artefactos | `experiments/test_039_live_playback` |
| `--clip-id` | Identificador del clip | `video_595` |
| `--config` | Archivo de configuracion YAML | `configs/default.yaml` |
| `--video` | Ruta local del video (override) | `None` |
| `--inference-mode` | `precomputed`, `sam3_sampling`, `lightweight_detector` | `precomputed` |
| `--sam3-stride` | Stride de frames para modo `sam3_sampling` | `None` |
| `--lightweight-stride` | Stride de frames para modo `lightweight_detector` | `None` |
| `--allow-gpu` | Habilitar modos GPU experimentales | `false` |
| `--gpu-profile` | Perfil de hardware GPU, ej. `msi_gpu` | `None` |
| `--host` | Host del servidor local | `127.0.0.1` |
| `--port` | Puerto del servidor local | `8766` |
| `--smoke-test` | Generar evidencia y salir | `false` |

---

## Estructura De Artefactos Esperada

```
experiments/test_039_live_playback/
  config.yaml                    # configuracion del clip y modos
  live_tracks.csv                # tracks normalizados por frame
  live_tracks.jsonl              # tracks en formato JSONL para SSE
  live_events.json               # eventos normalizados
  live_highlights.csv            # highlights derivados de level3
  minimap_frame_sample.json      # muestra de payload mini-mapa
  video_metadata.json            # fps, duracion, resolucion del video
  stream_messages.jsonl          # mensajes SSE emitidos
  stream_events.jsonl            # eventos de streaming
  stream_latency_metrics.csv     # latencia por frame de streaming
  stream_summary.json            # resumen del canal SSE
  frame_loop_summary.json        # resumen del loop online
  frame_loop_metrics.csv         # metricas por frame del loop
  inference_modes.json           # modos de inferencia disponibles
  debug_panel_summary.json       # estado del panel de depuracion
  endpoint_manifest.json         # todos los endpoints del backend
  live_playback_manifest.csv     # manifiesto de artefactos
  playback.html                  # UI del reproductor (generada)
  summary.md                     # resumen ejecutivo del smoke test

experiments/test_040_live_playback_validation/
  config.yaml                    # configuraciones por clip para validacion
  runtime_metrics.csv            # fps, latencia, frames saltados por clip
  event_comparison.csv           # comparacion eventos streaming vs batch
  summary.md                     # resumen de validacion tecnica
  live_validation_manifest.csv   # manifiesto de artefactos de validacion
```

Los videos completos, checkpoints, frames masivos y renders pesados permanecen **fuera de Git**.

---

## Endpoints Del Backend

Una vez levantado el servidor, los siguientes endpoints estan disponibles:

| Endpoint | Tipo | Descripcion |
|----------|------|-------------|
| `/` | HTML | Reproductor con canvas y controles |
| `/stream` | SSE | Canal continuo de overlays por frame |
| `/stream-summary.json` | JSON | Resumen del canal SSE |
| `/stream-messages.jsonl` | JSONL | Todos los mensajes SSE emitidos |
| `/live_tracks.jsonl` | JSONL | Tracks en formato streaming |
| `/stream_events.jsonl` | JSONL | Eventos de streaming |
| `/stream-latency.csv` | CSV | Latencia por frame |
| `/frame-loop-summary.json` | JSON | Resumen del loop online |
| `/frame-loop-metrics.csv` | CSV | Metricas del loop por frame |
| `/inference-modes.json` | JSON | Modos de inferencia disponibles |
| `/debug-panel.json` | JSON | Estado del panel de depuracion |
| `/tracks.csv` | CSV | Tracks normalizados |
| `/events.json` | JSON | Eventos normalizados |
| `/highlights.csv` | CSV | Highlights normalizados |
| `/minimap.json?frame=N` | JSON | Payload del mini-mapa para el frame N |
| `/calibration.json` | JSON | Estado de calibracion espacial |
| `/video-metadata.json` | JSON | Metadatos del video |
| `/video?clip_id=X` | Video | Servicio del archivo de video local |
| `/manifest.json` | JSON | Manifiesto de artefactos del experimento |

---

## Ejemplos Con Datos Precomputados

### Generar evidencia de smoke test con video_595

```bash
python scripts/run_live_playback_app.py \
    --experiment experiments/test_039_live_playback \
    --clip-id video_595 \
    --smoke-test
```

### Ejecutar validacion tecnica de un clip

```python
from futbotmx.live_validation import RuntimeMetricsRecorder, compare_tracks

rec = RuntimeMetricsRecorder(session_id="run1", clip_id="video_595")
rec.record_video_frame(120, timestamp_ms=0.0)
rec.record_analysis_frame(120, latency_ms=18.5, timestamp_ms=0.5)
rec.record_skip(121)
metrics = rec.compute()
print(metrics.as_dict())
```

### Comparar tracks streaming contra batch

```python
from futbotmx.live_validation import compare_tracks
import csv

with open("outputs/tracking/video_595/level3_tracks.csv") as f:
    batch_rows = list(csv.DictReader(f))

with open("experiments/test_039_live_playback/live_tracks.csv") as f:
    streaming_rows = list(csv.DictReader(f))

result = compare_tracks(streaming_rows, batch_rows, clip_id="video_595")
print(result.classification, result.match_rate)
```

---

## Hardware Y Rendimiento

### Modo precomputado (escritorio o laptop sin GPU)

- FPS de video: nativo del archivo (30-60 fps).
- FPS de overlay: 24-60 redraws/s en navegador.
- Latencia de lookup y dibujo: < 5 ms en local.
- No requiere GPU ni SAM 3.
- Compatible con escritorio Ubuntu o laptop sin RTX.

### Modo online parcial (laptop con GPU)

- FPS de analisis incremental: 5-15 frames/s estimado.
- Latencia overlay util: < 500 ms con backpressure activo.
- Hardware recomendado: laptop MSI con RTX 4050.
- El modo `precomputed` sirve de fallback si el analisis se atrasa.

### Modo SAM 3 sampling (solo laptop MSI)

- Requiere `--allow-gpu --gpu-profile msi_gpu`.
- Stride recomendado: cada 10-30 frames segun carga.
- No garantiza overlay por cada frame del video.
- Resultado esperado: benchmark con latencia documentada, no demo de produccion.

### Limites conocidos

| Condicion | Impacto | Fallback |
|-----------|---------|---------|
| Video no disponible en equipo actual | El reproductor carga datos pero no reproduce video | Mostrar aviso local, overlays disponibles |
| FPS nominal != FPS real del archivo | Desfase acumulativo en timestamp→frame | Usar metadatos inspeccionados con `inspect_video()` |
| Tracks con stride (no cada frame) | Frame sin datos en overlay | Usar frame anterior mas cercano |
| SAM 3 mas lento que FPS del video | Backpressure, frames saltados | Modo `delayed` o `replaying_cache`, ultimo overlay valido |
| Seek hacia atras | Trails y estado incremental obsoletos | `seek()` limpia trails y reinicia contadores |
