# Interfaz Local De Ejecucion

## Resultado

- Estado: `pass`.
- Regla: `local_app_v0.1`.
- Arquitectura: `HTML + backend local con libreria estandar`.
- Clip seleccionado: `video_595`.
- Frames: `120-180`.
- Stride: `1`.
- ROI: `0,615,1344,1792`.

## Comandos

- `server_smoke`: `pass` en `0.000s`; index rendered without starting long-lived server

## Artefactos

- `experiments/test_028_local_app/summary.md`: `presente`, rol `local_app`.
- `experiments/test_028_local_app/local_app_manifest.csv`: `presente`, rol `local_app`.
- `experiments/test_028_local_app/config.yaml`: `presente`, rol `local_app`.
- `experiments/test_028_local_app/dashboard/dashboard.html`: `pendiente`, rol `dashboard`.
- `experiments/test_028_local_app/reel/reel_demo.html`: `pendiente`, rol `reel`.
- `experiments/test_028_local_app/reel/reel_manifest.csv`: `pendiente`, rol `reel`.
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
