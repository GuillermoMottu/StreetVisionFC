# Interfaz Local De Ejecucion

## Resultado

- Estado: `pass`.
- Regla: `local_app_v0.1`.
- Arquitectura: `HTML + backend local con libreria estandar`.
- Clip seleccionado: `video_667`.
- Frames: `120-180`.
- Stride: `1`.
- ROI: `0,620,1360,1808`.

## Comandos

- `dashboard`: `pass` en `0.490s`; Wrote Level 3 dashboard to experiments/test_034_full_analysis/dashboard (15 manifest rows, 6 highlights shown)
- `reel`: `pass` en `1.672s`; Wrote Level 3 reel package to experiments/test_034_full_analysis/reel (4 segments, 21 manifest rows)

## Artefactos

- `experiments/test_034_full_analysis/summary.md`: `presente`, rol `local_app`.
- `experiments/test_034_full_analysis/local_app_manifest.csv`: `presente`, rol `local_app`.
- `experiments/test_034_full_analysis/config.yaml`: `presente`, rol `local_app`.
- `experiments/test_034_full_analysis/dashboard/dashboard.html`: `presente`, rol `dashboard`.
- `experiments/test_034_full_analysis/reel/reel_demo.html`: `presente`, rol `reel`.
- `experiments/test_034_full_analysis/reel/reel_manifest.csv`: `presente`, rol `reel`.
- `experiments/test_024_level3_dashboard/dashboard.html`: `presente`, rol `evidence`.
- `experiments/test_025_level3_reel/reel_demo.html`: `presente`, rol `evidence`.
- `experiments/test_027_level3_closure/closure_checks.csv`: `presente`, rol `checks`.

## Checks

- Checks Nivel 3 leidos: `11`.
- Pass: `11`.
- No pass: `0`.

## Comando

```bash
.venv/bin/python scripts/run_local_app.py
```
