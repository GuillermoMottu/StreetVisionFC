# test_003_tracking_real_video_836

## Configuracion

- Detecciones: `experiments/test_017_level2_closure/video_595_sam3_window_120_180/stride_1/detections_filtered_roi.json`
- Tracker simple: centroides con `max-distance-px` configurable.
- ByteTrack: `supervision.ByteTrack` por clase, si esta disponible.

## Resultados

### bytetrack
- `ball`: tracks `2`, inicios tardios `1`, longitud media `42.00`, longitud max `57`, salto max `13.9px`.
- `green_soccer_field`: tracks `1`, inicios tardios `0`, longitud media `61.00`, longitud max `61`, salto max `2.1px`.
- `small_robot`: tracks `1`, inicios tardios `0`, longitud media `61.00`, longitud max `61`, salto max `18.1px`.

### simple
- `ball`: tracks `2`, inicios tardios `1`, longitud media `42.50`, longitud max `57`, salto max `13.9px`.
- `green_soccer_field`: tracks `1`, inicios tardios `0`, longitud media `61.00`, longitud max `61`, salto max `2.1px`.
- `small_robot`: tracks `2`, inicios tardios `1`, longitud media `31.00`, longitud max `61`, salto max `18.1px`.

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
