# ARTIFACTS_INDEX - FutBotMX / StreetVisionFC

> Índice de artefactos clave del pipeline. Los videos fuente, checkpoints, caches y renders pesados no se versionan en Git. El demo público ligero requerido por la convocatoria sí se versiona.

## Video Demo

| Artefacto | Ruta local | Duración | Contenido |
|---|---|---|---|
| `futbotmx_demo_h264.mp4` | `outputs/videos/futbotmx_demo_h264.mp4` | 46.6 s | Título + SAM 3 masks + ByteTrack + Eventos + Heatmap |

Estado Git: versionado como entregable público ligero.

## Publicacion Externa

| Artefacto | URL | Estado |
|---|---|---|
| Instagram Reel | https://www.instagram.com/reel/DZynpB2pH_L_Mxq8V9Iq3bN5WHSFDGvsy_17iw0/?igsh=dnZ6MnlyYm13ZWV2 | Publicado |

### Regenerar

```bash
python scripts/create_phase3_demo.py \
  --video "$FUTBOTMX_VIDEO_836" \
  --output outputs/videos/futbotmx_demo.mp4

ffmpeg -i outputs/videos/futbotmx_demo.mp4 \
  -vcodec libx264 -crf 22 -preset fast -pix_fmt yuv420p \
  outputs/videos/futbotmx_demo_h264.mp4 -y
```

### Contenido del demo (secciones)

| Sección | Duración | Descripción |
|---|---|---|
| Título | ~4 s | Card negra con nombre del proyecto y tecnologías |
| Segmentación SAM 3 | ~13 s | Frame 143 con 8 masks pixel-level (robots, cancha, pelota, portería) |
| Tracking ByteTrack | ~12 s | Frames 120-180 con bboxes y track_id |
| Eventos | ~8 s | Eventos nivel 2 (ball_recovery, possession, highlight) |
| Heatmap + Métricas | ~10 s | Mapa de actividad + panel de métricas |

---

## SAM 3 Masks (frame 143)

| Archivo | Clase | Confianza | Método |
|---|---|---|---|
| `frame_000143_small_robot_000.png` | small_robot | 0.72 | SAM 3 texto |
| `frame_000143_small_robot_001.png` | small_robot | 0.61 | SAM 3 texto |
| `frame_000143_small_robot_002.png` | small_robot | 0.58 | SAM 3 texto |
| `frame_000143_small_robot_003.png` | small_robot | 0.85 | SAM 3 texto |
| `frame_000143_small_robot_004.png` | small_robot | 0.58 | SAM 3 texto |
| `frame_000143_ball_005.png` | ball | 0.72 | SAM 3 texto |
| `frame_000143_green_soccer_field_006.png` | green_soccer_field | 0.53 | SAM 3 texto |
| `frame_000143_goalpost_007.png` | goalpost | 0.96 | SAM 3 box-prompt (HSV bbox) |

Directorio: `experiments/current_evaluation/masks/`

### Regenerar masks

```bash
python scripts/run_goalpost_mask_test.py \
  --video "$FUTBOTMX_VIDEO_836" \
  --frame 143
```

---

## Tracks ByteTrack

| Clip | Frames | Archivo |
|---|---|---|
| video_836 | 120-180 | `experiments/test_003_tracking/video_836_real_tracking_120_180/tracks_bytetrack.csv` |

---

## Métricas y Eventos

| Tipo | Archivo |
|---|---|
| Level 2 metrics | `experiments/test_012_level2_metrics/video_836_real_metrics_120_180/level2_metrics.json` |
| Level 2 events | `experiments/test_013_level2_events/video_836_real_events_120_180/level2_events.json` |
| Heatmap | `experiments/test_003_tracking/video_836_real_tracking_120_180/heatmap_bytetrack.png` |

---

## Checkpoint SAM 3

| Artefacto | Ruta | Tamaño |
|---|---|---|
| `sam3.pt` | `checkpoints/sam3/sam3.pt` | 3.3 GB |

No versionado en Git. Variable de entorno: `SAM3_CHECKPOINT_PATH`.
