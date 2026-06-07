# Actividad 17 - Optimizacion y cache

## Objetivo

Reducir recomputacion al repetir el pipeline completo sobre el mismo clip, rango de frames y entradas ligeras ya procesadas.

## Alcance implementado

- Cache local por etapa en `.cache/futbotmx/full_analysis/<stage_id>/<cache_key>/`.
- Llave SHA-256 por etapa con `RULE_VERSION`, `CACHE_RULE_VERSION`, `clip_id`, rango de frames, fingerprint del video, hash de configuracion y hash de entradas ligeras.
- Cache de detecciones SAM 3 cuando se entrega un JSON precomputado con `--detections`.
- Cache de tracks cuando se entregan con `--tracks`, se generan desde detecciones o se reutilizan desde cierre Nivel 2.
- Cache de artefactos Nivel 3: espacial, asignacion de equipos, metricas, eventos avanzados, visualizaciones, dashboard y reel local.
- Cache de etapas ligeras auxiliares: ingesta, eventos Nivel 1 y eventos Nivel 2.
- `--force` para omitir cache hits, recomputar etapas y refrescar la entrada local correspondiente.

## Uso

```bash
.venv/bin/python scripts/run_full_analysis.py \
  --video "/ruta/local/video.mov" \
  --clip-id video_595 \
  --start-frame 120 \
  --end-frame 180
```

Para forzar recomputacion controlada:

```bash
.venv/bin/python scripts/run_full_analysis.py \
  --video "/ruta/local/video.mov" \
  --clip-id video_595 \
  --start-frame 120 \
  --end-frame 180 \
  --force
```

El directorio se puede cambiar con `--cache-dir`, pero debe seguir fuera de Git.

## Artefactos de observabilidad

Cada corrida de `run_full_analysis.py` exporta:

- `stage_plan.csv`: estado, politica de ejecucion, duracion y datos de cache por etapa.
- `runtime_metrics.csv`: `duration_sec`, `cache_status` y `cache_key` por etapa.
- `cache_manifest.csv`: resumen de cache local por etapa.
- `summary.md`: seccion `Cache Local` con hits, entradas guardadas/refrescadas y recordatorio de `--force`.

`cache_status` puede ser:

- `hit`: la etapa fue restaurada desde cache.
- `stored`: la etapa se ejecuto y se guardo por primera vez.
- `refreshed`: la etapa se ejecuto y reemplazo una entrada existente, normalmente con `--force`.
- `not_stored`: la etapa fallo o no produjo artefactos cacheables.
- `not_applicable`: etapa sin cache, por ejemplo setup o una etapa GPU documentada sin detecciones precomputadas.

## Cuellos de botella

No se agrego un benchmark nuevo en esta actividad. Los cuellos deben leerse desde `runtime_metrics.csv` de cada corrida real:

- SAM 3 sigue siendo el costo pesado y debe ejecutarse en la laptop MSI; el pipeline local solo cachea/reusa el JSON de detecciones ya generado.
- Tracking desde detecciones y las etapas Nivel 3 con PNG/HTML pueden acumular tiempo si se regeneran en cada experimento.
- En repeticiones, las etapas con `cache_status=hit` deberian reducir su `duration_sec` a copia local de artefactos.

## Reglas de versionado

Los caches son salida local operativa y no deben subirse a Git. El repositorio versiona solo codigo, tests, documentacion y evidencia ligera.
