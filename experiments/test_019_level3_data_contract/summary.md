# Contrato De Datos Nivel 3

## Resultado

- Estado: `definido`.
- Clips auditados: `2`.
- Tracks unicos heredados: `10`.
- Eventos Nivel 2 heredados: `4`.
- Esquemas Nivel 3 definidos: `7`.

## Auditoria Nivel 2

### video_595

- Frames observados: `61`.
- Tracks unicos: `4`.
- Eventos heredados: `2`.
- Clases: `ball|green_soccer_field|small_robot`.
- Equipos exportados: `neutral`.
- Faltantes para Nivel 3: `tracks:clip_id|tracks:time_sec|tracks:source_track_id|tracks:x_norm|tracks:y_norm|tracks:zone|tracks:calibration_id|tracks:calibration_status|metrics:confidence|metrics:source|events:event_subtype|events:secondary_object_ids|events:highlight_score|events:source_event_ids|events:interaction_edges|events:spatial_context|events:narrative|tracks:non_neutral_team_assignment`.

### video_667

- Frames observados: `61`.
- Tracks unicos: `6`.
- Eventos heredados: `2`.
- Clases: `ball|green_soccer_field|small_robot`.
- Equipos exportados: `neutral`.
- Faltantes para Nivel 3: `tracks:clip_id|tracks:time_sec|tracks:source_track_id|tracks:x_norm|tracks:y_norm|tracks:zone|tracks:calibration_id|tracks:calibration_status|metrics:confidence|metrics:source|events:event_subtype|events:secondary_object_ids|events:highlight_score|events:source_event_ids|events:interaction_edges|events:spatial_context|events:narrative|tracks:non_neutral_team_assignment`.

## Esquemas Definidos

- `level3_tracks.csv`: conserva coordenadas originales y agrega coordenadas rectificadas/fallback.
- `level3_metrics.csv`: metricas tacticas atomicas con confianza y fuente.
- `level3_metrics.json`: resumen legible para dashboard y README.
- `level3_events.json`: eventos avanzados con contexto espacial, narrativa y fuentes.
- `level3_highlights.csv`: ranking de jugadas con score y razon.
- `level3_narrative.md`: narrativa deportiva generada por reglas.
- `level3_visualization_manifest.csv`: indice de assets visuales ligeros o locales.

## Campos Faltantes A Resolver En Actividades Siguientes

- `events:event_subtype`
- `events:highlight_score`
- `events:interaction_edges`
- `events:narrative`
- `events:secondary_object_ids`
- `events:source_event_ids`
- `events:spatial_context`
- `metrics:confidence`
- `metrics:source`
- `tracks:calibration_id`
- `tracks:calibration_status`
- `tracks:clip_id`
- `tracks:non_neutral_team_assignment`
- `tracks:source_track_id`
- `tracks:time_sec`
- `tracks:x_norm`
- `tracks:y_norm`
- `tracks:zone`

## Limitaciones

- Nivel 2 usa coordenadas en pixeles; Nivel 3 requiere homografia o fallback documentado.
- Las etiquetas de equipo siguen siendo neutrales/unknown en los clips auditados.
- El contrato define campos de interaccion, narrativa y highlight avanzado, pero su calculo empieza en Actividades 3 y 4.
- Actividad 1 no ejecuta inferencia SAM 3 nueva ni genera archivos pesados.

## Artefactos

- `config.yaml`
- `level2_audit.csv`
- `level3_schema_manifest.csv`
- `level3_schema.json`
- `summary.md`
