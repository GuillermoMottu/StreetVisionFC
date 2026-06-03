# test_014_level2_visualizations_video_836

## Configuracion

- Tracks: `experiments/test_003_tracking/video_836_real_tracking_120_180/tracks_bytetrack.csv`.
- Eventos Nivel 2: `experiments/test_013_level2_events/video_836_real_events_120_180/level2_events.json`.
- Metricas Nivel 2: `experiments/test_012_level2_metrics/video_836_real_metrics_120_180/level2_metrics.json`.

## Visualizaciones

- Imagenes ligeras generadas: `8`.
- Timeline de eventos: `event_timeline.png`.
- Timeline de posesion: `possession_timeline.png`.
- Mapas de calor separados por clase y por track.

## Resumen Del Clip

- Frames observados: `61`.
- Tracks analizados: `4`.
- Intervalos de posesion: `4`.

## Eventos Por Tipo

- `ball_recovery`: `4`.
- `highlight_play`: `1`.
- `interception`: `1`.

## Confiabilidad

- `confiable`: `1`.
- `descartado`: `2`.
- `provisional`: `3`.

## Artefactos

- `event_timeline.png`
- `possession_timeline.png`
- `heatmap_*.png`
- `visualization_manifest.csv`
- `visual_summary.md`
- `config.yaml`

## Politica De Archivos

- No se genero ni versiono video completo.
- Solo se versionan PNG/CSV/Markdown ligeros.
