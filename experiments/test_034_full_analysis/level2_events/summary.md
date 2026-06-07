# test_013_level2_events_video_836

## Configuracion

- Tracks: `experiments/test_034_full_analysis/tracking/tracks.csv`.
- Regla: `level2_events_v0.1`.
- Umbral de posesion: `190px`.
- Min frames recuperacion: `5`.
- Gap max intercepcion: `12` frames.
- Velocidad min highlight: `250px/s`.
- Eje de zonas: `y`.

## Eventos

- `highlight_play` / `provisional`: `1`.
- `interception` / `descartado`: `1`.

## Detalle

- `lvl2_evt_000001` `interception` `descartado`: frames `120-180`, confianza `0.05`, senales `{'possession_runs': 0, 'max_gap_frames': 12, 'min_speed_px_per_sec': 120.0}`.
- `lvl2_evt_000002` `highlight_play` `provisional`: frames `122-123`, confianza `0.717`, senales `{'speed_px_per_sec': 370.406, 'min_speed_px_per_sec': 250.0, 'ball_track_continuity': 'same_track', 'zone_axis': 'y'}`.

## Validacion Visual

- Overlays representativos encontrados/generados: `5`.
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
