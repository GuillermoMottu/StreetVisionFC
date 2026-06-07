# Actividad 18 - video_667

## Resultado

- Estado: `degradacion`.
- Alcance pipeline: `level3_reused`.
- Homografia: `usable` confianza `0.738172`.
- Balon: `exito`.
- Robots: `exito`.
- Campo: `degradacion`.
- Highlights: `degradacion` riesgo falso positivo `medio`.
- Limitaciones: `homografia_provisional|revision_visual_provisional|equipos_neutrales`.

## Evidencia

- `experiments/test_026_level3_multiclip/level3_multiclip_comparison.csv`.
- `experiments/test_017_level2_closure/video_667/summary.md`.

## Fallos Documentados

- `mala_homografia` `degradacion`: Homografia usable pero confianza conservadora: 0.738172.
- `falsos_highlights` `riesgo`: homografia_provisional|revision_visual_provisional|equipos_neutrales

## Nota

Clip util para robustez, con degradaciones controladas: homografia_provisional|revision_visual_provisional|equipos_neutrales.
