# LEVEL3_CLOSURE_SUMMARY

Nivel 3 queda completado tecnicamente como demo avanzada reproducible de FutBotMX.

## Resultado

- Estado: `completado`.
- Gate tecnico: `scripts/check_level3_closure.py`.
- Checks pass: `11`.
- Checks fail: `0`.
- Tests: `54` pruebas con `unittest`.
- Clips principales: `video_595` y `video_667`.
- Alcance: analisis tactico aproximado, no arbitraje oficial ni sistema en tiempo real.

## Checks De Cierre

| Check | Estado | Evidencia |
|---|---|---|
| Tests unitarios | pass | `env MPLCONFIGDIR=/tmp/matplotlib .venv/bin/python -m unittest discover -s tests -q` |
| Readiness Nivel 3 | pass | `experiments/test_018_level3_readiness/readiness_checks.csv` |
| Contrato de datos | pass | `experiments/test_019_level3_data_contract/` |
| Rectificacion espacial | pass | `experiments/test_020_level3_spatial_model/` |
| Metricas tacticas | pass | `experiments/test_021_level3_tactical_metrics/` |
| Eventos avanzados | pass | `experiments/test_022_level3_advanced_events/` |
| Visualizaciones | pass | `experiments/test_023_level3_visualizations/` |
| Dashboard | pass | `experiments/test_024_level3_dashboard/` |
| Reel/demo | pass | `experiments/test_025_level3_reel/` |
| Multi-clip | pass | `experiments/test_026_level3_multiclip/` |
| Archivos pesados en Git | pass | `git ls-files` sin videos/modelos pesados |

## Artefactos Principales

- Readiness: `experiments/test_018_level3_readiness/summary.md`.
- Contrato: `experiments/test_019_level3_data_contract/level3_schema_manifest.csv`.
- Tracks Nivel 3: `experiments/test_020_level3_spatial_model/level3_tracks.csv`.
- Metricas tacticas: `experiments/test_021_level3_tactical_metrics/level3_metrics.csv`.
- Eventos avanzados: `experiments/test_022_level3_advanced_events/level3_events.json`.
- Highlights: `experiments/test_022_level3_advanced_events/level3_highlights.csv`.
- Narrativa: `experiments/test_022_level3_advanced_events/level3_narrative.md`.
- Visualizaciones: `experiments/test_023_level3_visualizations/visualization_manifest.csv`.
- Dashboard: `experiments/test_024_level3_dashboard/dashboard.html`.
- Reel local: `experiments/test_025_level3_reel/reel_demo.html`.
- Multi-clip: `experiments/test_026_level3_multiclip/level3_multiclip_comparison.csv`.
- Gate de cierre: `experiments/test_027_level3_closure/closure_checks.csv`.

## Tabla Multi-Clip

| Clip | Rol | Highlights | Score top | Interacciones | Aristas | Homografia | Revision |
|---|---|---:|---:|---:|---:|---:|---|
| `video_595` | principal | 82 | 82.868076 | 57 | 1 | 0.824417 | provisional |
| `video_667` | secundario | 60 | 74.044923 | 428 | 8 | 0.738172 | provisional |

Fuente: `experiments/test_026_level3_multiclip/level3_multiclip_comparison.csv`.

## Limitaciones Conocidas

- La homografia es aproximada y depende de la caja visible del campo.
- Las etiquetas de equipo siguen `neutral` o `unknown` en los clips principales.
- Las cadenas de pases se conservan como candidatas/dudosas cuando falta equipo confiable.
- Los highlights combinan velocidad normalizada, proximidad, zona y confianza; no declaran goles ni decisiones oficiales.
- El grafo de interaccion usa proximidad y duracion como senales comparativas, no contacto fisico confirmado.
- La revision visual es ligera sobre PNGs versionables; no reemplaza una auditoria humana frame a frame con video completo.

## Comandos Reproducibles

```bash
env MPLCONFIGDIR=/tmp/matplotlib .venv/bin/python -m unittest discover -s tests -q
.venv/bin/python scripts/check_level3_readiness.py
.venv/bin/python scripts/build_level3_data_contract.py
.venv/bin/python scripts/run_level3_spatial_model.py
.venv/bin/python scripts/run_level3_tactical_metrics.py
.venv/bin/python scripts/run_level3_advanced_events.py
.venv/bin/python scripts/run_level3_visualizations.py
.venv/bin/python scripts/run_level3_dashboard.py
.venv/bin/python scripts/run_level3_reel.py
.venv/bin/python scripts/run_level3_multiclip.py
.venv/bin/python scripts/check_level3_closure.py
```

## Politica De Archivos Pesados

No se versionan videos completos, checkpoints, modelos, frames masivos, mascaras masivas ni MP4 finales. El reel final se documenta como salida local mediante manifest y script de render en `experiments/test_025_level3_reel/`; cualquier MP4 generado debe permanecer fuera de Git.

## Lectura Para Evaluacion

1. Abrir `README.md`.
2. Revisar `experiments/test_024_level3_dashboard/dashboard.html`.
3. Revisar `experiments/test_025_level3_reel/reel_demo.html`.
4. Revisar `experiments/test_026_level3_multiclip/summary.md`.
5. Revisar `experiments/test_027_level3_closure/closure_checks.csv`.
