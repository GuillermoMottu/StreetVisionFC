# Live Playback Validation — Actividad 33

Experimento: test_040_live_playback_validation
Creado: 2026-06-07

## Objetivo

Medir si la experiencia funciona realmente durante reproduccion con datos precomputados.

## Clips de prueba

| Clip | Rol | Modo |
|------|-----|------|
| video_595 | clip principal | precomputed |
| video_667 | clip secundario | precomputed |
| video_480 | diagnostico balon | precomputed |

## Metricas de Runtime

| Clip | FPS Video | FPS Analisis | Latencia Media ms | Latencia p95 ms | Frames Saltados | Estado |
|------|-----------|--------------|-------------------|-----------------|-----------------|--------|
| video_595 | — | — | — | — | — | pendiente |
| video_667 | — | — | — | — | — | pendiente |
| video_480 | — | — | — | — | — | pendiente |

## Tracks: Streaming vs Batch

| Clip | Streaming | Batch | Matched | Match Rate | Cobertura Batch | Estado |
|------|-----------|-------|---------|------------|-----------------|--------|
| video_595 | — | — | — | — | — | pendiente |
| video_667 | — | — | — | — | — | pendiente |
| video_480 | — | — | — | — | — | pendiente |

## Eventos: Streaming vs Batch

| Clip | Streaming | Batch | Matched | Overlap Rate | Estado |
|------|-----------|-------|---------|--------------|--------|
| video_595 | — | — | — | — | pendiente |
| video_667 | — | — | — | — | pendiente |
| video_480 | — | — | — | — | pendiente |

## Criterio de aceptacion

- Match Rate tracks >= 85% → acceptable; >= 60% → degraded; < 60% → failed.
- Overlap Rate eventos >= 70% → acceptable; >= 40% → degraded; < 40% → failed.
- Latencia media <= 33.3 ms → acceptable; <= 100 ms → degraded; > 100 ms → failed.

## Notas

- Ejecutar en modo precomputed antes de intentar inferencia online.
- Las metricas se generan usando RuntimeMetricsRecorder durante reproduccion real.
- Poblar runtime_metrics.csv y event_comparison.csv tras la primera ejecucion.
