# Asignacion De Equipos Nivel 3

## Resultado

- Estado: `generado`.
- Regla: `team_assignment_v0.1`.
- Tracks fuente: `experiments/current_evaluation/phase4_team_assignment/level3_tracks_video836.csv`.
- Robots asignados: `3`.
- Archivo editable: `team_assignment.csv`.
- Tracks enriquecidos: `level3_tracks_with_teams.csv`.

## Estrategias

- `manual_by_id`: `editable_template`, confianza `0.0`. 0 valid manual rows; CSV can be edited by humans.
- `dominant_color`: `not_available`, confianza `0.0`. Level 3 tracks do not include robot crops or color histograms; color strategy is documented for future video/crop integration.
- `initial_side_fallback`: `available`, confianza `0.64`. Split robots by initial x_norm; mean clip spread=0.517.

## Equipos

- `team_left`: `2` tracks.
- `team_right`: `1` tracks.

## Fuentes

- `initial_side_fallback`: `3` tracks.

## Validacion

- `pass`: `3` filas.

## Uso En Nivel 3

```bash
.venv/bin/python scripts/run_level3_tactical_metrics.py --tracks experiments/test_031_team_assignment/level3_tracks_with_teams.csv --experiment experiments/test_032_level3_team_metrics
.venv/bin/python scripts/run_level3_advanced_events.py --tracks experiments/test_031_team_assignment/level3_tracks_with_teams.csv --interaction-metrics experiments/test_032_level3_team_metrics/interaction_metrics.csv --interaction-edges experiments/test_032_level3_team_metrics/interaction_edges.csv --experiment experiments/test_033_level3_team_events
```

## Limitaciones

- La asignacion por lado inicial es aproximada y editable; no sustituye revision humana ni deteccion visual de uniformes.
- La estrategia de color queda documentada como no disponible porque los artefactos actuales no incluyen crops/histogramas por robot.
- Si un clip tiene pocos robots o poco spread lateral, la confianza se mantiene conservadora.

## Manifest

- Filas en `team_assignment_manifest.csv`: `7`.
