# Temporal stability stride 3

## Configuracion

- Frames: `120` a `180` con stride `3` (`21` frames).
- Prompts: `ball, robot`.
- ROI: `(0.0, 620.0, 1360.0, 1808.0)`.

## Resultados

- Balon detectado: `19/21` frames filtrados.
- Robots detectados: `21/21` frames filtrados.
- Detecciones removidas por ROI: `19`.
- Frames sin balon: `135, 147`.
- Frames sin robots: `ninguno`.
- Overlays representativos: `120, 150, 180`.

## Resumen por frame

- Frame `120`: ball `1`, robot `3`, total `4`
- Frame `123`: ball `1`, robot `3`, total `4`
- Frame `126`: ball `1`, robot `3`, total `4`
- Frame `129`: ball `1`, robot `3`, total `4`
- Frame `132`: ball `1`, robot `3`, total `4`
- Frame `135`: ball `0`, robot `3`, total `3`
- Frame `138`: ball `1`, robot `3`, total `4`
- Frame `141`: ball `1`, robot `3`, total `4`
- Frame `144`: ball `1`, robot `3`, total `4`
- Frame `147`: ball `0`, robot `2`, total `2`
- Frame `150`: ball `1`, robot `2`, total `3`
- Frame `153`: ball `1`, robot `2`, total `3`
- Frame `156`: ball `1`, robot `2`, total `3`
- Frame `159`: ball `1`, robot `2`, total `3`
- Frame `162`: ball `1`, robot `2`, total `3`
- Frame `165`: ball `1`, robot `2`, total `3`
- Frame `168`: ball `1`, robot `2`, total `3`
- Frame `171`: ball `1`, robot `2`, total `3`
- Frame `174`: ball `1`, robot `2`, total `3`
- Frame `177`: ball `1`, robot `3`, total `4`
- Frame `180`: ball `1`, robot `2`, total `3`

## Artefactos

- `detections.json`
- `detections_filtered_roi.json`
- `tracks_filtered_roi.csv`
- `metrics.csv`
- `heatmap_filtered_roi.png`
