# Actividad 18 - video_480

## Resultado

- Estado: `fallo_conocido`.
- Alcance pipeline: `diagnostic_only`.
- Homografia: `not_evaluated` confianza `0.0`.
- Balon: `fallo`.
- Robots: `exito`.
- Campo: `degradacion`.
- Highlights: `not_evaluated` riesgo falso positivo `not_evaluated`.
- Limitaciones: `no_level3_outputs`.

## Evidencia

- `experiments/test_015_level2_multiclip/video_480/summary.md`.
- `experiments/test_017_level2_closure/video_480/diagnostic_summary.md`.

## Fallos Documentados

- `mala_homografia` `not_evaluated`: Sin salida Level 3 espacial versionada para este clip.
- `perdida_de_balon` `fallo_conocido`: experiments/test_017_level2_closure/video_480/diagnostic_summary.md

## Nota

Fallo conocido por perdida/no deteccion de balon; se conserva como caso diagnostico.
