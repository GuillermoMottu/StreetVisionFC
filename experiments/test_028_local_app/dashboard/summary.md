# Dashboard Ligero Nivel 3

## Resultado

- Estado: `generado`.
- Regla: `level3_dashboard_v0.1`.
- Formato: `HTML estatico local`.
- Arquitectura: sin backend, sin login, sin dependencias nuevas.
- Clips integrados: `video_595, video_667`.
- Highlights enlazados: `142`.
- Metricas CSV: `25`.
- Eventos avanzados: `144`.
- Muestras de interaccion: `485`.
- Aristas de grafo: `9`.
- Cadenas de pase conservadoras: `2`.

## Secciones

- Resumen con score de highlight, conteos de metricas, interacciones, aristas y cadenas.
- Metricas por clip y control medio por robot.
- Visualizaciones: storyboard, grafo, Voronoi en mini-mapa y Voronoi proyectado.
- Highlights y aristas principales.
- Evidencia con links relativos a CSV, JSON, Markdown y manifest.

## Assets Integrados

- `storyboard`: `highlight_storyboard.png`.
- `interaction_graph`: `interaction_graph.png`.
- `primary_voronoi`: `voronoi_frame_video_595_120.png`.
- `primary_voronoi_original`: `voronoi_original_frame_video_595_120.png`.

## Manifest

- Filas en `dashboard_manifest.csv`: `15`.
- El dashboard referencia assets ligeros existentes; no duplica PNGs ni versiona video.

## Limitaciones

- El dashboard presenta analisis aproximado Nivel 3, no arbitraje oficial ni reproduccion de video completo.
- Los links dependen de la estructura relativa de `experiments/` versionada en el repositorio.
- Las visualizaciones se muestran como capturas estaticas para mantener el paquete liviano.

## Artefactos

- `dashboard.html`
- `dashboard_manifest.csv`
- `config.yaml`
- `summary.md`

## Comando

```bash
.venv/bin/python scripts/run_level3_dashboard.py
```
