# test_002_sam3_segmentation

## Estado

SAM 3 ejecutado en laptop MSI.

## Configuracion

- Video: `/home/guillermo/Vídeos/CopaFutMX/17 Abril/video-836_singular_display.mov`
- Frames: `30, 90, 143, 200, 260`
- Prompts: `ball, robot`
- Detecciones: `18`

## Artefactos

- `config.yaml`
- `detections.json`
- `tracks.csv`
- `events.json`
- `heatmap.png`
- `overlay_frame_30.png`
- `overlay_frame_90.png`
- `overlay_frame_143.png`
- `overlay_frame_200.png`
- `overlay_frame_260.png`

## Resultado por frame

- Frame 30: 1 balon, 3 robots.
- Frame 90: 0 balon, 4 robots.
- Frame 143: 1 balon, 2 robots.
- Frame 200: 1 balon, 3 robots.
- Frame 260: 0 balon, 3 robots.

## Observaciones

Los robots se detectan de forma consistente en los cinco frames. El balon aparece en 3 de 5 frames con el prompt `ball`.

El tracking y `events.json` validan el contrato del pipeline con detecciones reales de SAM 3. Como los frames estan espaciados, los IDs de tracking no deben interpretarse todavia como continuidad tactica confiable.
