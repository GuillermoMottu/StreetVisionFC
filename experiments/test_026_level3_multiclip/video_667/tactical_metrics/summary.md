# Metricas Tacticas Avanzadas Nivel 3

## Resultado

- Estado: `calculado`.
- Regla: `level3_tactical_metrics_v0.1`.
- Fuente: `experiments/test_026_level3_multiclip/video_667/spatial_model/level3_tracks.csv`.
- Clips analizados: `video_667`.
- Frames con control espacial: `61`.
- Metricas exportadas: `17`.
- Muestras de interaccion: `428`.
- Aristas de grafo: `8`.

## Control Espacial

- Grilla: `24x16` (`384` celdas).
- Modo `track_fallback`: `184` filas de control.

## Voronoi Aproximado

- Voronoi se aproxima asignando cada celda normalizada al robot mas cercano.
- Las regiones quedan recortadas automaticamente al rectangulo `[0,1] x [0,1]` de la cancha visible.
- Frames representativos guardados: `4` en `voronoi_frames.csv`.

## Interacciones

- `dispute_cluster`: `61`.
- `possession_candidate`: `88`.
- `pressure_candidate`: `122`.
- `robot_ball_distance`: `96`.
- `robot_proximity`: `61`.

## Top Aristas

- `video_667` `small_robot_bt_01` -> `small_robot_bt_02` (`robot_proximity`): frames `61`, peso `34.362905`.
- `video_667` `small_robot_bt_01` -> `small_robot_bt_02` (`pressure_candidate`): frames `61`, peso `33.756465`.
- `video_667` `small_robot_bt_02` -> `ball_bt_01` (`dispute_cluster`): frames `61`, peso `33.247968`.
- `video_667` `small_robot_bt_02` -> `ball_bt_01` (`possession_candidate`): frames `61`, peso `32.658906`.
- `video_667` `small_robot_bt_02` -> `small_robot_bt_03` (`pressure_candidate`): frames `61`, peso `31.766337`.

## Comparabilidad

- `video_595` y `video_667` usan el mismo contrato `level3_tracks.csv`, la misma grilla y los mismos umbrales normalizados.
- Como los equipos siguen `neutral`, el control por equipo queda en fallback por robot individual.
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

- Nodos: `5`.
- Aristas: `8`.
