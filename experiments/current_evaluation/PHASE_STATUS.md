# PHASE_STATUS — FutBotMX / StreetVisionFC
> Archivo de estado vivo. Actualizar al cerrar cada fase.
> Última actualización: 2026-06-14

## Fase actual

**PROYECTO COMPLETO** — pipeline unificado implementado y listo para evaluación por jueces.

## Estado por fase

| Fase | Nombre | Estado | Aprobación del usuario |
|---|---|---|---|
| 0 | Rama, baseline y respaldo | Completada — aprobada | "Aprobado, continúa con la Fase 1." (2026-06-11) |
| 1 | Reproducibilidad rápida | Completada — aprobada | "Aprobado, continúa con la Fase 2." (2026-06-11) |
| 2 | Segmentación SAM 3: masks y portería | Completada — aprobada | "Apruebo la fase 2 y continua con la fase 3" (2026-06-13) |
| 3 | Overlays, visualización y video demo | Completada — aprobada | "Aprobamos la Fase 3 y continuamos con la Fase 4" (2026-06-13) |
| 4 | Team assignment y análisis semántico | Completada — aprobada | "Es correcta la asignación de equipos, continua con el desarrollo" (2026-06-13) |
| 5 | Métricas, benchmark y dependencias | Completada — aprobada | "Continua con la fase 6" (2026-06-13) |
| 5b | OWLv2 + Grounded-SAM (mejora solicitada) | Completada — aprobada | "Sigue la recomendación" (2026-06-13) |
| 6 | Documentación para evaluación | Completada — aprobada | "Continua" (2026-06-13) |
| 7 | Limpieza de arquitectura y CI | Completada — aprobada | "Continua" (2026-06-13) |
| **R1-H** | **Métricas supervisadas (anotaciones humanas)** | **Completada** | Roboflow GT proporcionado por usuario (2026-06-14) |
| **U1** | **Pipeline unificado (Grounded-SAM → full_analysis → live_playback)** | **Completada** | 2026-06-14 |

## Fases aprobadas por el usuario

| Fase | Frase de aprobación | Fecha |
|---|---|---|
| 0 | "Aprobado, continúa con la Fase 1." | 2026-06-11 |
| 1 | "Aprobado, continúa con la Fase 2." | 2026-06-11 |
| 2 | "Apruebo la fase 2 y continua con la fase 3" | 2026-06-13 |
| 3 | "Aprobamos la Fase 3 y continuamos con la Fase 4" | 2026-06-13 |
| 4 | "Es correcta la asignación de equipos, continua con el desarrollo" | 2026-06-13 |
| 5 | "Continua con la fase 6" | 2026-06-13 |
| 5b | "Sigue la recomendación" | 2026-06-13 |
| 6 | "Continua" | 2026-06-13 |
| 7 | "Actualizalo" → proyecto completado | 2026-06-14 |

## Resultados finales

| Métrica | Valor |
|---|---|
| Benchmark (single frame) | 2.237 s/frame — 0.447 FPS — 3878 MB VRAM |
| Supervised F1 micro avg (frame 143, IoU@0.5) | **0.857** |
| Recall total | **1.00** (todos los objetos anotados detectados) |
| Precision total | 0.75 |
| Tests unitarios | 425 — PASS |
| Anotaciones GT | 49 anotaciones humanas, 8 frames, Roboflow |

## Tareas incompletas

Ninguna.

## Bloqueos conocidos

Ninguno activo.

## Rama de trabajo

```
fix/master-audit-corrections
```
Creada desde: `main` @ commit `6761ff7`

## Commits de cierre

| Commit | Descripción |
|---|---|
| `8daa311` | feat(metrics): supervised metrics con anotaciones Roboflow reales |
| `7c17648` | chore(fase7): cleanup, CI y archivado |
| `72675a7` | docs(fase6): paquete de documentación para evaluación |
| `7711915` | feat: goalpost fallback + OWLv2 reload fix |
| `b4a8a82` | feat: pipeline Grounded-SAM (OWLv2 + SAM3) |

## Cierres de fase disponibles

- `closures/FASE_6_cierre.md`
- `closures/FASE_7_cierre.md`
