# PHASE_STATUS — FutBotMX / StreetVisionFC
> Archivo de estado vivo. Actualizar al cerrar cada fase.
> Última actualización: 2026-06-13

## Fase actual

**OWLv2 + Grounded-SAM integrado** (completado, pendiente aprobación para continuar a Fase 6)

## Estado por fase

| Fase | Nombre | Estado | Aprobación del usuario |
|---|---|---|---|
| 0 | Rama, baseline y respaldo | Completada — aprobada | "Aprobado, continúa con la Fase 1." (2026-06-11) |
| 1 | Reproducibilidad rápida | Completada — aprobada | "Aprobado, continúa con la Fase 2." (2026-06-11) |
| 2 | Segmentación SAM 3: masks y portería | Completada — aprobada | "Apruebo la fase 2 y continua con la fase 3" (2026-06-13) |
| 3 | Overlays, visualización y video demo | Completada — aprobada | "Aprobamos la Fase 3 y continuamos con la Fase 4" (2026-06-13) |
| 4 | Team assignment y análisis semántico | Completada — aprobada | "Es correcta la asignación de equipos, continua con el desarrollo" (2026-06-13) |
| 5 | Métricas, benchmark y dependencias | Completada (R1-H pendiente de anotación humana) | — |
| 5b | OWLv2 + Grounded-SAM (mejora solicitada) | **Completada** (commit b4a8a82) | Pendiente aprobación |
| 6 | Documentación para evaluación | **Completada** (commit pendiente) | Pendiente aprobación |
| 7 | Limpieza de arquitectura y CI | **Completada** (commit pendiente) | Pendiente aprobación |

## Fases aprobadas por el usuario

| Fase | Frase de aprobación | Fecha |
|---|---|---|
| 0 | "Aprobado, continúa con la Fase 1." | 2026-06-11 |
| 1 | "Aprobado, continúa con la Fase 2." | 2026-06-11 |
| 2 | "Apruebo la fase 2 y continua con la fase 3" | 2026-06-13 |
| 3 | "Aprobamos la Fase 3 y continuamos con la Fase 4" | 2026-06-13 |
| 4 | "Es correcta la asignación de equipos, continua con el desarrollo" | 2026-06-13 |

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
