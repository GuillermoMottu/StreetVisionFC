# video_595_short_window

## Configuracion

- Video: `/home/guillermo/Vídeos/CopaFutMX/17 Abril/video-595_singular_display.mov`
- Resolucion: `1344x1792`.
- FPS: `59.71505265331406`.
- Duracion: `8.071666666666667` segundos (`482` frames).
- Frames evaluados: `60`, `90`, `120`, `150`, `180`.
- Prompts: `ball`, `small robot`, `green soccer field`.
- ROI: `x=0..1344`, `y=620..1792`.

## Resultados

- Detecciones filtradas totales: `17`.
- Balon: `6` detecciones en `5/5` frames; frames sin balon: `none`.
- Robots: `6` detecciones en `5/5` frames.
- Cancha: `5` detecciones en `5/5` frames.
- Removidas por ROI: `0`.
- Nota: All target classes detected in every sampled frame; one frame has duplicate ball/robot candidates.

## Resumen por frame

- Frame `60`: ball `1`, small_robot `1`, green_soccer_field `1`.
- Frame `90`: ball `1`, small_robot `1`, green_soccer_field `1`.
- Frame `120`: ball `1`, small_robot `1`, green_soccer_field `1`.
- Frame `150`: ball `1`, small_robot `1`, green_soccer_field `1`.
- Frame `180`: ball `2`, small_robot `2`, green_soccer_field `1`.

## Artefactos

- `detections.json`
- `detections_filtered_roi.json`
- `tracks_filtered_roi.csv`
- `heatmap_filtered_roi.png`
- `overlay_frame_120_filtered_roi.png`
