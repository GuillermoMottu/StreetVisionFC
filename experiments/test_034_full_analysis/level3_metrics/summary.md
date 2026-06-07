# Metricas Tacticas Avanzadas Nivel 3

## Resultado

- Estado: `calculado`.
- Regla: `level3_tactical_metrics_v0.1`.
- Fuente: `experiments/test_034_full_analysis/team_assignment/level3_tracks_with_teams.csv`.
- Clips analizados: `video_595`.
- Frames con control espacial: `61`.
- Metricas exportadas: `10`.
- Muestras de interaccion: `57`.
- Aristas de grafo: `1`.
- Equipos con control agregado: `1`.

## Control Espacial

- Grilla: `24x16` (`384` celdas).
- Modo `team`: `61` filas de control.

## Control Por Equipo

- `video_595` `team_right`: control medio `100.0`%, zona dominante `middle_third`, contributors `small_robot_bt_01`.

## Voronoi Aproximado

- Voronoi se aproxima asignando cada celda normalizada al robot mas cercano.
- Las regiones quedan recortadas automaticamente al rectangulo `[0,1] x [0,1]` de la cancha visible.
- Frames representativos guardados: `3` en `voronoi_frames.csv`.

## Interacciones

- `possession_candidate`: `57`.

## Top Aristas

- `video_595` `small_robot_bt_01` -> `ball_bt_01` (`possession_candidate`): frames `57`, peso `33.005998`.

## Comparabilidad

- `video_595` y `video_667` usan el mismo contrato `level3_tracks.csv`, la misma grilla y los mismos umbrales normalizados.
- Si `team_assignment.csv` ya fue aplicado, se exportan metricas por equipo ademas del fallback por robot.
- Cada fila de `level3_metrics.csv`, `interaction_metrics.csv` e `interaction_edges.csv` incluye confianza o confiabilidad provisional.

## Limitaciones

- Control, Voronoi y presion son aproximaciones tacticas sobre homografia Nivel 3, no mediciones oficiales.
- La posesion se conserva como candidato por proximidad; contacto fisico y reglas oficiales quedan fuera del alcance.
- El grafo pondera duracion, distancia y confianza para comparacion interna de la demo.

## Artefactos

- `config.yaml`
- `level3_metrics.csv`
- `level3_metrics.json`
- `spatial_control.csv`
- `voronoi_frames.csv`
- `interaction_metrics.csv`
- `interaction_edges.csv`
- `interaction_graph.json`
- `summary.md`

## Comando

```bash
.venv/bin/python scripts/run_level3_tactical_metrics.py
```

## Grafo

- Nodos: `3`.
- Aristas: `1`.
