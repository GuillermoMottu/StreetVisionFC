# video_667_short_window

## Configuracion

- Video: `/home/guillermo/Vídeos/CopaFutMX/17 Abril/video-667_singular_display.mov`
- Resolucion: `1360x1808`.
- FPS: `59.70695970695971`.
- Duracion: `8.19` segundos (`489` frames).
- Frames evaluados: `60`, `90`, `120`, `150`, `180`.
- Prompts: `ball`, `small robot`, `green soccer field`.
- ROI: `x=0..1360`, `y=620..1808`.

## Resultados

- Detecciones filtradas totales: `28`.
- Balon: `5` detecciones en `5/5` frames; frames sin balon: `none`.
- Robots: `18` detecciones en `5/5` frames.
- Cancha: `5` detecciones en `5/5` frames.
- Removidas por ROI: `0`.
- Nota: All target classes detected in every sampled frame; robot prompt returns multiple robot candidates per frame.

## Resumen por frame

- Frame `60`: ball `1`, small_robot `3`, green_soccer_field `1`.
- Frame `90`: ball `1`, small_robot `4`, green_soccer_field `1`.
- Frame `120`: ball `1`, small_robot `3`, green_soccer_field `1`.
- Frame `150`: ball `1`, small_robot `4`, green_soccer_field `1`.
- Frame `180`: ball `1`, small_robot `4`, green_soccer_field `1`.

## Artefactos

- `detections.json`
- `detections_filtered_roi.json`
- `tracks_filtered_roi.csv`
- `heatmap_filtered_roi.png`
- `overlay_frame_120_filtered_roi.png`
