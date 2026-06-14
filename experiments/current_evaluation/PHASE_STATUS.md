# PHASE_STATUS — FutBotMX / StreetVisionFC
> Archivo de estado vivo. Actualizar al cerrar cada fase.
> Última actualización: 2026-06-13

## Fase actual

**Fase 2 — Segmentación SAM 3: masks y portería** (completada con box-prompt portería — pendiente aprobación)

## Estado por fase

| Fase | Nombre | Estado | Aprobación del usuario |
|---|---|---|---|
| 0 | Rama, baseline y respaldo | Completada — aprobada | "Aprobado, continúa con la Fase 1." (2026-06-11) |
| 1 | Reproducibilidad rápida | Completada — aprobada | "Aprobado, continúa con la Fase 2." (2026-06-11) |
| 2 | Segmentación SAM 3: masks y portería | Completada | "Apruebo la fase 2 y continua con la fase 3" (2026-06-13) |
| 3 | Overlays, visualización y video demo | Completada — pendiente revisión D4 (usuario) | — |
| 4 | Team assignment y análisis semántico | No iniciada | — |
| 5 | Métricas, benchmark y dependencias | No iniciada | — |
| 6 | Documentación para evaluación | No iniciada | — |
| 7 | Limpieza de arquitectura y CI | No iniciada | — |

## Fases aprobadas por el usuario

| Fase | Frase de aprobación | Fecha |
|---|---|---|
| 0 | "Aprobado, continúa con la Fase 1." | 2026-06-11 |
| 1 | "Aprobado, continúa con la Fase 2." | 2026-06-11 |
| 2 | "Apruebo la fase 2 y continua con la fase 3" | 2026-06-13 |

## Tareas incompletas

Ninguna para Fase 0.

## Bloqueos conocidos

Ninguno activo.

| Bloqueo | Fase afectada | Estado |
|---|---|---|
| `ffmpeg` no encontrado en PATH de Claude Code | Fase 3 | **Resuelto** — ffmpeg 8.0.1 instalado en /usr/bin/ (confirmado 2026-06-11) |

## Rama de trabajo

```
fix/master-audit-corrections
```
Creada desde: `main` @ commit `6761ff7`

## Cierres de fase disponibles

- `closures/FASE_0_cierre.md` — pendiente de escritura al final de esta fase
