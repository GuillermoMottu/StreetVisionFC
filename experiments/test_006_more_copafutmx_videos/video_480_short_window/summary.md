# video_480_short_window

## Configuracion

- Video: `/home/guillermo/Vídeos/CopaFutMX/17 Abril/video-480_singular_display.mov`
- Resolucion: `1360x1808`.
- FPS: `59.6995427824951`.
- Duracion: `7.655` segundos (`457` frames).
- Frames evaluados: `60`, `90`, `120`, `150`, `180`.
- Prompts: `ball`, `small robot`, `green soccer field`.
- ROI: `x=0..1360`, `y=620..1808`.

## Resultados

- Detecciones filtradas totales: `10`.
- Balon: `0` detecciones en `0/5` frames; frames sin balon: `60, 90, 120, 150, 180`.
- Robots: `5` detecciones en `5/5` frames.
- Cancha: `5` detecciones en `5/5` frames.
- Removidas por ROI: `0`.
- Nota: Ball not detected in the sampled window; robot and field are stable. Review absence, occlusion, or prompt recall before using this clip for events.

## Resumen por frame

- Frame `60`: ball `0`, small_robot `1`, green_soccer_field `1`.
- Frame `90`: ball `0`, small_robot `1`, green_soccer_field `1`.
- Frame `120`: ball `0`, small_robot `1`, green_soccer_field `1`.
- Frame `150`: ball `0`, small_robot `1`, green_soccer_field `1`.
- Frame `180`: ball `0`, small_robot `1`, green_soccer_field `1`.

## Artefactos

- `detections.json`
- `detections_filtered_roi.json`
- `tracks_filtered_roi.csv`
- `heatmap_filtered_roi.png`
- `overlay_frame_120_filtered_roi.png`
