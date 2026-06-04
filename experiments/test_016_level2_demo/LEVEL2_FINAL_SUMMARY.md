# Resumen Final Nivel 2

## Alcance Completado

- Metricas deportivas intermedias: posesion temporal, distancia y velocidad por track.
- Eventos intermedios: recuperacion, intercepcion aproximada y jugada destacada con confiabilidad.
- Visualizaciones: timelines, posesion y heatmaps separados.
- Multi-clip real: `video_595`, `video_667`, baseline `video_836` y diagnostico `video_480`.
- Demo ligera: `demo_board.png` y resumen local sin videos versionados.

## Baseline video_836

- Frames observados: `61`.
- Tracks: `4`.
- Posesion asignada: `0.904406s`.
- Robot principal: `robot_bt_01` (`88.52459%`).

## Eventos

- `ball_recovery`: `4`.
- `highlight_play`: `1`.
- `interception`: `1`.

## Confiabilidad

- `confiable`: `1`.
- `descartado`: `2`.
- `provisional`: `3`.

## Multi-Clip

- `video_595`: frames `5`, tracks `3`, posesion `0.502386s`, eventos `1/1/1`.
- `video_667`: frames `5`, tracks `4`, posesion `0.0s`, eventos `0/1/1`.
- `video_480`: diagnostico de balon con `0` detecciones de balon y `5` detecciones de robot.

## Limitaciones

- Las metricas estan en pixeles por perspectiva no rectificada.
- `video_595` y `video_667` usan muestras sparse cada 30 frames, no tracking denso equivalente a `video_836`.
- La intercepcion aproximada requiere validacion visual humana cuando exista cambio real de poseedor.

## Entrega Ligera

- `demo_board.png`
- `demo_local.md`
- `LEVEL2_FINAL_SUMMARY.md`
- `demo_manifest.csv`
- Capturas copiadas desde `test_014`.
