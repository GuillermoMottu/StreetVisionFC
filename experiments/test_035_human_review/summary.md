# Revision Humana De Highlights

## Resultado

- Estado: `generado`.
- Regla: `highlight_human_review_v0.1`.
- Reviewer inicial: `codex_activity_15`.
- Fecha revision inicial: `2026-06-07`.
- Highlights revisados: `6`.
- Estados: `{'confiable': 2, 'provisional': 4}`.
- Validaciones fallidas: `0`.

## Operacion

- `human_review_panel.html` muestra overlay, mini-mapa y datos de cada highlight top.
- El panel permite cambiar `confiable`, `provisional` o `descartado`, editar notas y exportar un CSV.
- `human_review.csv` es editable manualmente y se valida con `human_review_validation.csv`.
- Dashboard y reel pueden consumir este CSV con `--human-review` sin borrar `level3_highlights.csv` original.

## Artefactos

- `config.yaml`
- `human_review_panel.html`
- `human_review.csv`
- `human_review_validation.csv`
- `human_review_manifest.csv`
- `summary.md`
