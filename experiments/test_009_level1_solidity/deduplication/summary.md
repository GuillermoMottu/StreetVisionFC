# test_009_level1_deduplication

## Objetivo

Validar una limpieza ligera de detecciones antes de escalar eventos a clips adicionales.

## Configuracion

- Script: `scripts/clean_detections.py`.
- Entrada `video_595`: `experiments/test_006_more_copafutmx_videos/video_595_short_window/detections_filtered_roi.json`.
- Entrada `video_667`: `experiments/test_006_more_copafutmx_videos/video_667_short_window/detections_filtered_roi.json`.
- NMS por clase: `iou_threshold=0.6`.
- Top-k `video_595`: `ball=1`.
- Top-k `video_667`: `ball=1`, `small_robot=3`.

## Resultados

- `video_595`: remueve `1` deteccion duplicada de balon (`6 -> 5`).
- `video_667`: remueve `3` detecciones extra de robot (`18 -> 15`).
- Cancha se conserva completa en ambos clips (`5 -> 5`).

## Artefactos

- `video_595_detections_cleaned.json`
- `video_595_cleaning_metrics.csv`
- `video_667_detections_cleaned.json`
- `video_667_cleaning_metrics.csv`

## Conclusion

La limpieza NMS/top-k resuelve los duplicados observados en clips adicionales sin requerir rerun de SAM 3. Debe aplicarse antes de tracking/eventos multi-clip.
