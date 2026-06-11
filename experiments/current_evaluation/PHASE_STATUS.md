# PHASE_STATUS — FutBotMX / StreetVisionFC
> Archivo de estado vivo. Actualizar al cerrar cada fase.
> Última actualización: 2026-06-10

## Fase actual

**Fase 0 — Rama, baseline y respaldo** (pendiente de aprobación del usuario)

## Estado por fase

| Fase | Nombre | Estado | Aprobación del usuario |
|---|---|---|---|
| 0 | Rama, baseline y respaldo | Completada — pendiente aprobación | — |
| 1 | Reproducibilidad rápida | No iniciada | — |
| 2 | Segmentación SAM 3: masks y portería | No iniciada | — |
| 3 | Overlays, visualización y video demo | No iniciada | — |
| 4 | Team assignment y análisis semántico | No iniciada | — |
| 5 | Métricas, benchmark y dependencias | No iniciada | — |
| 6 | Documentación para evaluación | No iniciada | — |
| 7 | Limpieza de arquitectura y CI | No iniciada | — |

## Fases aprobadas por el usuario

Ninguna todavía.

## Tareas incompletas

Ninguna para Fase 0.

## Bloqueos conocidos

| Bloqueo | Fase afectada | Acción requerida |
|---|---|---|
| `ffmpeg` no instalado | Fase 3 | `sudo apt-get install ffmpeg` antes de iniciar Fase 3 |
| `ffprobe` no instalado | Fase 3 | Incluido en el paquete `ffmpeg` |

## Rama de trabajo

```
fix/master-audit-corrections
```
Creada desde: `main` @ commit `6761ff7`

## Cierres de fase disponibles

- `closures/FASE_0_cierre.md` — pendiente de escritura al final de esta fase
