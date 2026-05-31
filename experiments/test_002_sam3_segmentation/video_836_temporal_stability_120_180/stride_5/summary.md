# Temporal stability stride 5

## Configuracion

- Frames: `120` a `180` con stride `5` (`13` frames).
- Prompts: `ball, robot`.
- ROI: `(0.0, 620.0, 1360.0, 1808.0)`.

## Resultados

- Balon detectado: `12/13` frames filtrados.
- Robots detectados: `13/13` frames filtrados.
- Detecciones removidas por ROI: `12`.
- Frames sin balon: `135`.
- Frames sin robots: `ninguno`.
- Overlays representativos: `120, 150, 180`.

## Resumen por frame

- Frame `120`: ball `1`, robot `3`, total `4`
- Frame `125`: ball `1`, robot `3`, total `4`
- Frame `130`: ball `1`, robot `3`, total `4`
- Frame `135`: ball `0`, robot `3`, total `3`
- Frame `140`: ball `1`, robot `3`, total `4`
- Frame `145`: ball `1`, robot `2`, total `3`
- Frame `150`: ball `1`, robot `2`, total `3`
- Frame `155`: ball `1`, robot `2`, total `3`
- Frame `160`: ball `1`, robot `2`, total `3`
- Frame `165`: ball `1`, robot `2`, total `3`
- Frame `170`: ball `1`, robot `2`, total `3`
- Frame `175`: ball `1`, robot `2`, total `3`
- Frame `180`: ball `1`, robot `2`, total `3`

## Artefactos

- `detections.json`
- `detections_filtered_roi.json`
- `tracks_filtered_roi.csv`
- `metrics.csv`
- `heatmap_filtered_roi.png`
