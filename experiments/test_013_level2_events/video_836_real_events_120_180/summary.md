# test_013_level2_events_video_836

## Configuracion

- Tracks: `experiments/test_003_tracking/video_836_real_tracking_120_180/tracks_bytetrack.csv`.
- Regla: `level2_events_v0.1`.
- Umbral de posesion: `190px`.
- Min frames recuperacion: `5`.
- Gap max intercepcion: `12` frames.
- Velocidad min highlight: `250px/s`.

## Eventos

- `ball_recovery` / `confiable`: `1`.
- `ball_recovery` / `descartado`: `1`.
- `ball_recovery` / `provisional`: `2`.
- `highlight_play` / `provisional`: `1`.
- `interception` / `descartado`: `1`.

## Detalle

- `lvl2_evt_000001` `ball_recovery` `provisional`: frames `120-133`, confianza `0.58`, senales `{'frames': 14, 'min_frames': 5, 'mean_distance_px': 171.046}`.
- `lvl2_evt_000002` `ball_recovery` `provisional`: frames `137-142`, confianza `0.58`, senales `{'frames': 6, 'min_frames': 5, 'mean_distance_px': 184.603}`.
- `lvl2_evt_000003` `ball_recovery` `descartado`: frames `144-144`, confianza `0.15`, senales `{'frames': 1, 'min_frames': 5, 'mean_distance_px': 177.083}`.
- `lvl2_evt_000004` `ball_recovery` `confiable`: frames `148-180`, confianza `0.78`, senales `{'frames': 33, 'min_frames': 5, 'mean_distance_px': 138.851}`.
- `lvl2_evt_000005` `interception` `descartado`: frames `120-180`, confianza `0.05`, senales `{'possession_runs': 4, 'max_gap_frames': 12, 'min_speed_px_per_sec': 120.0}`.
- `lvl2_evt_000006` `highlight_play` `provisional`: frames `127-128`, confianza `0.671`, senales `{'speed_px_per_sec': 307.306, 'min_speed_px_per_sec': 250.0}`.

## Validacion Visual

- Overlays representativos encontrados/generados: `15`.
- Overlays pendientes: `0`.
- Si no se provee `--video`, el script enlaza overlays existentes cercanos por frame.

## Limitaciones

- Recuperacion e intercepcion son heuristicas de proximidad, no contacto fisico confirmado.
- En tracks con equipo `neutral`, la intercepcion se conserva como candidato descartado cuando no hay cambio de robot.
- La jugada destacada usa velocidad/zona en pixeles y requiere revision visual final.

## Artefactos

- `level2_events.json`
- `level2_event_metrics.csv`
- `overlay_validation.csv`
- `config.yaml`
