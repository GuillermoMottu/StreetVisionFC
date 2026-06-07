# Actividad 18 - Validacion Con Mas Clips

## Resultado

- Regla: `activity18_clip_validation_v0.1`.
- Clips seleccionados: `4`.
- Clasificacion: `{"degradacion": 2, "exito": 1, "fallo_conocido": 1}`.
- No se generaron ni versionaron videos, frames masivos ni renders pesados.

## Comparacion

| clip | estado | alcance | homografia | balon | highlights | riesgo falso highlight |
| --- | --- | --- | --- | --- | --- | --- |
| `video_595` | `exito` | `level3_reused` | `usable (0.824417)` | `exito` | `degradacion` | `medio` |
| `video_667` | `degradacion` | `level3_reused` | `usable (0.738172)` | `exito` | `degradacion` | `medio` |
| `video_836` | `degradacion` | `level2_baseline` | `not_evaluated (0.0)` | `degradacion` | `not_evaluated` | `not_evaluated` |
| `video_480` | `fallo_conocido` | `diagnostic_only` | `not_evaluated (0.0)` | `fallo` | `not_evaluated` | `not_evaluated` |

## Fallos Buscados

- Mala homografia: registrada cuando no hay Level 3 espacial o la confianza queda baja/provisional.
- Perdida de balon: registrada cuando la seleccion o el diagnostico reportan balon parcial o ausente.
- Falsos highlights: registrada como riesgo cuando la revision visual sigue provisional o los equipos son neutrales.

## Artefactos

- `clip_selection.csv`
- `clip_validation_comparison.csv`
- `failure_modes.csv`
- `activity18_manifest.csv`
- `<clip_id>/summary.md`
- `<clip_id>/clip_validation.csv`
- `<clip_id>/failure_modes.csv`

## Fallos Detectados

- `video_595` `falsos_highlights` `media`: Mantener highlights como candidatos y revisar visualmente los top antes de narrarlos.
- `video_667` `mala_homografia` `media`: Usar calibracion manual o descartar metricas espaciales finas para este clip.
- `video_667` `falsos_highlights` `media`: Mantener highlights como candidatos y revisar visualmente los top antes de narrarlos.
- `video_836` `mala_homografia` `media`: Usar calibracion manual o descartar metricas espaciales finas para este clip.
- `video_836` `perdida_de_balon` `media`: Reprocesar SAM 3 con prompts de balon y revisar overlays ligeros antes de usar eventos de posesion.
- `video_480` `mala_homografia` `alta`: Usar calibracion manual o descartar metricas espaciales finas para este clip.
- `video_480` `perdida_de_balon` `alta`: Reprocesar SAM 3 con prompts de balon y revisar overlays ligeros antes de usar eventos de posesion.
