# test_004_events_real_video_836

## Configuracion

- Tracks: `experiments/test_003_tracking/video_836_real_tracking_120_180/tracks_bytetrack.csv`
- Distancia de posesion: `190.0px`.
- Min frames posesion: `8`.
- Umbral de tiro: `350.0px/s`.
- Distancia colision: `35px`.

## Diagnostico

- Distancia balon-robot mas cercana: min `113.4px`, p50 `158.3px`, p90 `187.5px`, max `210.0px`.
- Velocidad balon: max `307.3px/s`.
- Candidatos de tiro con umbral previo `180px/s`: `11`.
- Candidatos de tiro con umbral ajustado `350px/s`: `0`.

## Eventos

- `activity_zone`: `1`
- `collision`: `1`
- `possession`: `2`

## Confiabilidad

- possession: provisional_confiable - distancia ajustada a resolucion 1360x1808 y validada contra robot cercano.
- collision: provisional - depende de solape/distancia de bbox; revisar visualmente en frames indicados.
- activity_zone: confiable - calculado desde posiciones del balon en la ventana.
- shot: descartado - umbral ajustado evita falsos positivos por jitter (11 candidatos con umbral previo, 0 con umbral ajustado).

## Validacion visual

- Overlays generados para frames: `120, 126, 133, 148, 164, 180, 128, 135, 142, 150`.
- Los eventos de `shot` quedan desactivados para esta ventana porque el umbral previo respondia a jitter/movimiento pequeno del balon cerca del gol.

## Artefactos

- `events.json`
- `event_metrics.csv`
- `nearest_robot_distance.csv`
- `ball_speed.csv`
- Overlays de eventos.
