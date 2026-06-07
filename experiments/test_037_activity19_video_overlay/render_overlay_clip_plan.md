# Plan De Render Local - Overlay Corto

El MP4 se renderiza localmente y queda fuera de Git. La evidencia versionada son thumbnails, contact sheet, CSV y manifest.

## Dependencias

- `ffmpeg` disponible en `PATH`.
- Overlays PNG ya versionados en la etapa de eventos Nivel 3.

## Comando

```bash
cd experiments/test_037_activity19_video_overlay
bash render_overlay_clip.sh
```

Salida local esperada: `local_outputs/activity19/video_595_overlay_clip.mp4`.

## Segmentos

- `overlay_segment_01` rank `1` frames `122-123` thumbnail `overlay_thumb_rank_01_video_595_frame_122.png`.
- `overlay_segment_02` rank `2` frames `128-129` thumbnail `overlay_thumb_rank_02_video_595_frame_128.png`.
- `overlay_segment_03` rank `3` frames `133-135` thumbnail `overlay_thumb_rank_03_video_595_frame_133.png`.

## Politica

- `*.mp4` esta ignorado por `.gitignore`.
- No se copian videos fuente ni frames masivos al repositorio.
- El overlay muestra IDs, trazas cortas y etiqueta de evento cuando existen en la evidencia Nivel 3.
