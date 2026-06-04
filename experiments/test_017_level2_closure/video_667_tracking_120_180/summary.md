# test_003_tracking_real_video_836

## Configuracion

- Detecciones: `experiments/test_017_level2_closure/video_667_sam3_window_120_180/stride_1/detections_filtered_roi.json`
- Tracker simple: centroides con `max-distance-px` configurable.
- ByteTrack: `supervision.ByteTrack` por clase, si esta disponible.

## Resultados

### bytetrack
- `ball`: tracks `1`, inicios tardios `0`, longitud media `61.00`, longitud max `61`, salto max `1.3px`.
- `green_soccer_field`: tracks `1`, inicios tardios `0`, longitud media `61.00`, longitud max `61`, salto max `2.6px`.
- `small_robot`: tracks `4`, inicios tardios `0`, longitud media `46.00`, longitud max `61`, salto max `3.6px`.

### simple
- `ball`: tracks `1`, inicios tardios `0`, longitud media `61.00`, longitud max `61`, salto max `1.3px`.
- `green_soccer_field`: tracks `1`, inicios tardios `0`, longitud media `61.00`, longitud max `61`, salto max `2.6px`.
- `small_robot`: tracks `4`, inicios tardios `0`, longitud media `46.00`, longitud max `61`, salto max `3.6px`.

## Comparacion

- ByteTrack disponible: `True`.
- Tracker recomendado para la siguiente etapa: `simple`.
- Cambios de ID incorrectos: no se observan cambios obvios en overlays representativos; sin ground truth, se reporta como validacion visual provisional.
- Overlays representativos: `120, 150, 180`.

## Artefactos

- `tracks_simple.csv`
- `tracks_bytetrack.csv` si ByteTrack esta disponible
- `metrics.csv`
- `heatmap_simple.png`
- `heatmap_bytetrack.png` si ByteTrack esta disponible
- Overlays representativos por tracker
