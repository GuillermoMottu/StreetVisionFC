# Cierre Experimental — Playback Vivo Y Analisis Online

Extension Post-Nivel 3 de FutBotMX. Actividades 21 a 35.

---

## Resumen Ejecutivo

Esta extension agrega reproduccion de video local con overlays sincronizados, canal SSE backend/frontend, tracker incremental, detector de eventos por ventana movil, mini-mapa vivo, control de backpressure y validacion tecnica. Todo el codigo nuevo es ligero, reproducible en escritorio sin GPU y compatible con artefactos del pipeline batch existente.

El modo principal es `playback_precomputado`. Los modos online estan implementados pero requieren hardware GPU para producir resultados utiles.

---

## Modulos Implementados

| Modulo | Actividad | Descripcion | Tests |
|--------|-----------|-------------|-------|
| `live_playback_contract.py` | 22 | Normalizacion de tracks, eventos y highlights; validadores de contrato de datos | 9 |
| `live_playback.py` | 23-28 | Servidor HTTP local, SSE, loop de frames, modos de inferencia, UI HTML | 18 |
| `tracking/incremental_tracker.py` | 29 | Tracker frame-a-frame con matching por centroide, ventana de perdida, seek | 46 |
| `events/stream_detector.py` | 30 | Detector de eventos por ventana movil: posesion, pase, colision, disparo, highlight | 52 |
| `live_playback_minimap.py` | 31 | Mini-mapa vivo con homografia/fallback, trails por track, metricas de zona y velocidad | 62 |
| `live_playback_backpressure.py` | 32 | Cola acotada, monitor de relojes video/analisis, politica de fallback y degradacion | 82 |
| `live_validation.py` | 33 | Grabador de metricas runtime, comparacion streaming vs batch, clasificacion de calidad | 72 |

**Total: 341 tests de la extension** sobre una suite total de **425 tests** (incluyendo tests de Nivel 1, 2 y 3 preexistentes).

---

## Experimentos Y Artefactos Ligeros

| Directorio | Actividad | Contenido |
|------------|-----------|-----------|
| `experiments/test_039_live_playback/` | 23-28 | Evidencia de smoke test: tracks, eventos, highlights, SSE, loop, mini-mapa, debug, manifest |
| `experiments/test_040_live_playback_validation/` | 33 | Config por clip, CSVs de metricas y comparacion, summary, manifest |

---

## Documentos De La Extension

| Documento | Actividad | Descripcion |
|-----------|-----------|-------------|
| `docs/LIVE_PLAYBACK_SCOPE.md` | 21 | Alcance, modos, limites tecnicos y presupuesto de rendimiento |
| `docs/LIVE_PLAYBACK_DATA_CONTRACT.md` | 22 | Contrato de datos: columnas, formatos y fixtures de prueba |
| `docs/LIVE_PLAYBACK_USAGE.md` | 35 | Comandos, estructura de artefactos, ejemplos y notas de hardware |
| `docs/LIVE_PLAYBACK_DECISIONS.md` | 35 | Registro de decisiones tecnicas: precomputed, SSE, modos, SAM 3 |
| `docs/LIVE_PLAYBACK_CLOSURE.md` | 35 | Este documento |
| `docs/TODO_LIVE_PLAYBACK.md` | 21-35 | Lista de actividades con estado de avance |

---

## Pruebas Ejecutadas

```
Ran 425 tests in ~2.4s — OK (0 failures, 0 errors)
```

| Suite | Tests | Cubre |
|-------|-------|-------|
| `test_live_playback_contract` | 9 | Normalizacion de filas, validadores de tracks y eventos |
| `test_live_playback` | 18 | Servidor HTTP, endpoints, SSE, loop, modos de inferencia |
| `test_incremental_tracker` | 46 | Matching, ventana de perdida, seek, snapshot, CSV |
| `test_stream_event_detector` | 52 | Buffer movil, posesion, pase, colision, disparo, ciclo de vida |
| `test_live_playback_minimap` | 62 | Calibracion, homografia, trails, metricas, frames de salida |
| `test_live_playback_backpressure` | 82 | Cola acotada, monitor de relojes, politica de fallback |
| `test_live_validation` | 72 | Grabador de metricas, comparacion de tracks y eventos, CSV/MD |
| Suites Nivel 1-3 | 84 | Contratos preexistentes sin regresiones |

---

## Estado Por Actividad

| Actividad | Titulo | Estado |
|-----------|--------|--------|
| 21 | Definir Alcance Del Modo Playback Vivo | Completa |
| 22 | Contrato De Datos Temporal | Completa |
| 23 | Reproductor Con Overlays Precomputados | Completa |
| 24 | Sincronizador Frame/Timestamp | Completa |
| 25 | Backend Local De Playback | Completa |
| 26 | Canal Backend/Frontend | Completa |
| 27 | Loop De Frames Vivo | Completa |
| 28 | Modos De Inferencia | Completa |
| 29 | Tracker Incremental | Completa |
| 30 | Detector De Eventos En Streaming | Completa |
| 31 | Mini-Mapa Y Metricas Vivas | Completa |
| 32 | Backpressure Y Degradacion | Completa |
| 33 | Validacion Tecnica | Completa |
| 34 | Panel De Depuracion | Parcial (indicadores basicos en UI; descarga de logs pendiente) |
| 35 | Documentacion Y Cierre Experimental | Completa |

---

## Riesgos Pendientes

| Riesgo | Probabilidad | Impacto | Mitigacion |
|--------|--------------|---------|-----------|
| FPS nominal != FPS real del video | Media | Alto (desfase timestamp→frame) | Usar `inspect_video()` para metadatos reales; documentar en config |
| SAM 3 demasiado lento para online | Alta | Medio (backpressure acumulado) | Usar modo precomputado o stride >= 30; medir en laptop MSI antes de demo |
| Tracks con stride en artefactos batch | Media | Bajo (frames sin overlay) | Usar frame anterior mas cercano; marcador visual de frame sin datos |
| Cambio de ID despues de seek | Baja | Medio (trails confusos) | `seek()` limpia estado; documentar como comportamiento esperado |
| Video no disponible en otro equipo | Alta | Bajo (overlay sigue visible) | Aviso en UI; datos y overlays si estan versionados |
| Eventos streaming distintos a batch | Media | Bajo (candidatos, no definitivos) | Usar lenguaje conservador: candidato/provisional; validar con `compare_events()` |
| Panel de depuracion incompleto | Media | Bajo (depuracion manual) | Actividad 34 pendiente; `/debug-panel.json` disponible como endpoint intermedio |

---

## Criterio De Exito Alcanzado

El primer criterio de exito declarado en la actividad 21 se cumplio:

> Un video local reproduce fluido y muestra tracks, balon, IDs, eventos, posesion candidata, highlights y mini-mapa sincronizados usando artefactos existentes.

Evidencia en `experiments/test_039_live_playback/summary.md`:

- Latencia promedio del loop hasta overlay: **1.23 ms** en modo precomputado.
- Frames con datos disponibles: **61 de 61** en el rango de prueba.
- Frames saltados por backpressure: **0**.
- Errores de validacion: **0**.

---

## Proximos Pasos Opcionales

1. Completar Actividad 34 (descargar logs, `live_tracks.jsonl`, `stream_events.jsonl` desde UI).
2. Ejecutar `RuntimeMetricsRecorder` durante reproduccion real con `video_595`, `video_667` y `video_480` y poblar `experiments/test_040_live_playback_validation/runtime_metrics.csv`.
3. Benchmark de modo `sam3_sampling` en laptop MSI con stride configurable.
4. Evaluar modo `lightweight_detector` con detector YOLO ligero como alternativa a SAM 3.
