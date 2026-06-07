# Pipeline Completo Para Video Nuevo

## Resultado

- Estado: `pass`.
- Regla: `full_analysis_v0.1`.
- Clip: `video_595`.
- Video: `/home/guillermo/Vídeos/CopaFutMX/17 Abril/video-595_singular_display.mov`.
- Frames: `120-180`.
- Experimento: `experiments/test_034_full_analysis`.
- Etapas pass: `12`.
- Etapas que requieren GPU/insumo externo: `1`.
- Etapas saltadas: `0`.
- Etapas fallidas: `0`.

## Frontera Ligero / GPU

- Ligeras en escritorio: ingesta de metadatos, tracking desde detecciones existentes, eventos Nivel 1/2, rectificacion Nivel 3, asignacion de equipos, metricas, eventos avanzados, visualizaciones estaticas, dashboard y reel demo.
- Requiere laptop/GPU: SAM 3 para generar detecciones frescas desde video. En este comando se ejecuta si se entrega `--detections`; si no, queda documentado y se reutilizan tracks ligeros disponibles.
- No se versiona MP4 final, checkpoints, frames masivos ni mascaras masivas.

## Etapas

- `setup` `pass` `lightweight`: Experiment folder and request snapshot created.
- `ingestion` `pass` `lightweight`: Video metadata inspected with OpenCV.
- `sam3_detections` `requires_gpu` `requires_gpu`: SAM 3 inference is intentionally documented as a laptop/GPU stage; provide --detections to execute tracking from fresh detections.
- `tracking` `pass` `lightweight_or_reused`: No fresh detections were provided; reused lightweight Level 2 closure tracks for this clip.
- `level1_events` `pass` `lightweight`: Wrote 2 events to experiments/test_034_full_analysis/level1_events/events.json
- `level2_events` `pass` `lightweight`: Wrote Level 2 events experiment to experiments/test_034_full_analysis/level2_events
- `level3_spatial` `pass` `lightweight`: Wrote Level 3 spatial model to experiments/test_034_full_analysis/level3_spatial (1/1 clips usable)
- `team_assignment` `pass` `lightweight`: Wrote team assignment package to experiments/test_034_full_analysis/team_assignment (1 robot tracks, 1 validation rows)
- `level3_metrics` `pass` `lightweight`: Wrote Level 3 tactical metrics to experiments/test_034_full_analysis/level3_metrics (10 metrics, 1 graph edges)
- `level3_events` `pass` `lightweight`: Wrote Level 3 advanced events to experiments/test_034_full_analysis/level3_events (83 events, 82 highlights)
- `level3_visualizations` `pass` `lightweight`: Wrote Level 3 visualizations to experiments/test_034_full_analysis/level3_visualizations (13 assets)
- `dashboard` `pass` `lightweight`: Wrote Level 3 dashboard to experiments/test_034_full_analysis/dashboard (15 manifest rows, 6 highlights shown)
- `reel` `pass` `lightweight`: Wrote Level 3 reel package to experiments/test_034_full_analysis/reel (4 segments, 21 manifest rows)

## Artefactos Raiz

- `config.yaml`
- `summary.md`
- `stage_plan.csv`
- `runtime_metrics.csv`
- `full_analysis_manifest.csv`

## Comando

```bash
.venv/bin/python scripts/run_full_analysis.py --video "/home/guillermo/Vídeos/CopaFutMX/17 Abril/video-595_singular_display.mov" --clip-id video_595 --start-frame 120 --end-frame 180
```
