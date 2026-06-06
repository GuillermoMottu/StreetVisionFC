# Validacion Multi-Clip Nivel 3 - video_667

## Resultado

- Estado: `generado`.
- Rol: `secondary`.
- Regla: `level3_multiclip_v0.1`.
- Homografia: `usable` con confianza `0.738172`.
- Filas rectificadas: `306` de `306`.
- Highlights: `60`; score top `74.044923`.
- Interacciones: `428.0` muestras y `8.0` aristas.
- Revision visual ligera: `provisional`.
- Limitaciones: `homografia_provisional|revision_visual_provisional|equipos_neutrales`.

## Evidencia Ligera

- `spatial_model/level3_tracks.csv` y `spatial_validation.csv`.
- `tactical_metrics/level3_metrics.csv`, `interaction_metrics.csv` e `interaction_edges.csv`.
- `advanced_events/level3_highlights.csv`, `level3_events.json` y overlays top.
- `visualizations/visualization_manifest.csv` con PNGs versionables.
- `dashboard/dashboard.html` como demo estatica del clip.
- `human_review.csv` con clasificacion `confiable`, `provisional` o `descartado`.

## Lectura Operativa

- El clip se proceso con las mismas reglas Nivel 3 que los demas clips; no hay ajustes especificos por clip.
- La revision conserva lenguaje de candidatos tacticos y evita afirmar goles, faltas o pases oficiales.
- Los artefactos pesados siguen fuera de Git; solo se versionan CSV, JSON, Markdown, HTML y PNGs ligeros.
