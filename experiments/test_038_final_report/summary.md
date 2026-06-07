# Actividad 20 - Exportacion A Reporte PDF/HTML

## Resultado

- Estado: `generado`.
- Regla: `activity20_final_report_v0.1`.
- HTML imprimible: `final_report.html`.
- Links verificados: `19`.
- Links faltantes: `0`.
- Archivos pesados duplicados en el paquete: `0`.
- PDF local esperado: `local_outputs/activity20/futbotmx_final_report.pdf`.
- PDF no generado ni versionado por defecto.

## Metricas

- Checks cierre Nivel 3 pass: `11`.
- Checks cierre Nivel 3 fail: `0`.
- Clips Nivel 3 generados: `2` de `2`.
- Highlights comparados: `142`.
- Clips validados actividad 18: `4`.
- Segmentos overlay actividad 19: `3`.

## Artefactos

- `config.yaml`
- `final_report.html`
- `summary.md`
- `link_validation.csv`
- `final_report_manifest.csv`
- `pdf_export_plan.md`
- `render_final_report_pdf.sh`

## Politica PDF

- El PDF se genera solo localmente bajo `local_outputs/`.
- `local_outputs/` esta fuera de Git.
- El reporte HTML enlaza evidencias existentes y no copia videos, checkpoints, frames masivos ni mascaras.
