# test_003_tracking_real_video_836

## Configuracion

- Detecciones: `experiments/test_002_sam3_segmentation/video_836_temporal_stability_120_180/stride_1/detections_filtered_roi.json`
- Tracker simple: centroides con `max-distance-px` configurable.
- ByteTrack: `supervision.ByteTrack` por clase, si esta disponible.

## Resultados

### bytetrack
- `ball`: tracks `1`, inicios tardios `0`, longitud media `59.00`, longitud max `59`, salto max `5.1px`.
- `robot`: tracks `3`, inicios tardios `0`, longitud media `48.67`, longitud max `61`, salto max `33.7px`.

### simple
- `ball`: tracks `1`, inicios tardios `0`, longitud media `59.00`, longitud max `59`, salto max `5.1px`.
- `robot`: tracks `4`, inicios tardios `1`, longitud media `37.25`, longitud max `61`, salto max `95.7px`.

## Comparacion

- ByteTrack disponible: `True`.
- Tracker recomendado para la siguiente etapa: `bytetrack`.
- Cambios de ID incorrectos: no se observan cambios obvios en overlays representativos; sin ground truth, se reporta como validacion visual provisional.
- Overlays representativos: `120, 150, 180`.

## Artefactos

- `tracks_simple.csv`
- `tracks_bytetrack.csv` si ByteTrack esta disponible
- `metrics.csv`
- `heatmap_simple.png`
- `heatmap_bytetrack.png` si ByteTrack esta disponible
- Overlays representativos por tracker
