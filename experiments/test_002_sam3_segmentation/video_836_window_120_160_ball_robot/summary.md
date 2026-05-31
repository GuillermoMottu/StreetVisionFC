# test_002_sam3_segmentation

## Estado

SAM 3 ejecutado en laptop MSI.

## Configuracion

- Video: `/home/guillermo/Vídeos/CopaFutMX/17 Abril/video-836_singular_display.mov`
- Frames: `120, 125, 130, 135, 140, 145, 150, 155, 160`
- Prompts: `ball, robot`
- Detecciones: `39`

## Artefactos

- `config.yaml`
- `detections.json`
- `tracks.csv`
- `events.json`
- `detections_filtered_roi.json`
- `tracks_filtered_roi.csv`
- `events_filtered_roi.json`
- `heatmap.png`
- `heatmap_filtered_roi.png`
- `overlay_frame_120.png`
- `overlay_frame_140.png`
- `overlay_frame_160.png`
- `overlay_frame_120_filtered_roi.png`
- `overlay_frame_140_filtered_roi.png`
- `overlay_frame_160_filtered_roi.png`

## Resultado por frame

- Frame 120: 1 balon, 3 robots.
- Frame 125: 1 balon, 4 robots.
- Frame 130: 1 balon, 4 robots.
- Frame 135: 0 balon, 4 robots.
- Frame 140: 1 balon, 4 robots.
- Frame 145: 1 balon, 3 robots.
- Frame 150: 1 balon, 3 robots.
- Frame 155: 1 balon, 3 robots.
- Frame 160: 1 balon, 3 robots.

## Observaciones

SAM 3 detecto el balon en 8 de 9 frames y robots en todos los frames. La ventana consecutiva permite tracking mucho mas coherente que la muestra espaciada.

El prompt `robot` tambien detecta un robot elevado/fuera de cancha en el fondo. Antes de calcular eventos finales conviene agregar filtrado por zona de cancha o una ROI de campo.

`events.json` contiene eventos provisionales (`shot`, `activity_zone`) generados desde detecciones reales; deben validarse despues de filtrar objetos fuera de cancha.

## Filtrado ROI de cancha

ROI inicial para `video-836_singular_display.mov`: rectangulo `x=0..1360`, `y=620..1808`, aplicado sobre el centroide de cada deteccion. La ROI se eligio visualmente para cubrir la cancha visible y excluir objetos detectados sobre la barda/fondo.

Resultado del filtro:

- Detecciones totales: 39 -> 31.
- Balon: 8 -> 8.
- Robots: 31 -> 23.
- Falsos positivos removidos: 8 detecciones de robot fuera de cancha, principalmente el robot elevado/fondo sobre la barda.

Resultado por frame despues del filtro:

- Frame 120: 1 balon, 3 robots.
- Frame 125: 1 balon, 3 robots.
- Frame 130: 1 balon, 3 robots.
- Frame 135: 0 balon, 3 robots.
- Frame 140: 1 balon, 3 robots.
- Frame 145: 1 balon, 2 robots.
- Frame 150: 1 balon, 2 robots.
- Frame 155: 1 balon, 2 robots.
- Frame 160: 1 balon, 2 robots.

`events_filtered_roi.json` conserva 2 eventos provisionales (`shot`, `activity_zone`). El `shot` sigue marcado como provisional porque la ventana es corta y el umbral de velocidad aun requiere calibracion visual.
