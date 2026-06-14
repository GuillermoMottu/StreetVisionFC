# Cierre de Fase 7 — Limpieza de arquitectura y CI

## 1. Resumen

| Tarea | ID | Riesgo | Estado | Resultado |
|---|---|---|---|---|
| Archivar documentación obsoleta | L5 | Bajo | Completa | 14 docs movidos a `docs/archived/` |
| CI básico GitHub Actions | L6 | Bajo | Completo | `.github/workflows/ci.yml` |
| Índice de experimentos legacy | L4 | Bajo | Completo | `experiments/archived/INDEX.md` |
| Script de validación unificado | L3 | Bajo | Completo | `scripts/validate_pipeline.py` |
| Migrar módulos level2/level3 | L1 | Alto | **Omitido** | Riesgo > beneficio sin margen de tiempo |
| Renombrar scripts run_level* | L2 | Medio | **Omitido** | Scripts referenciados en experimentos históricos |
| Clip de muestra público | L7 | Bajo | N/A | Demo ya en `outputs/videos/futbotmx_demo_h264.mp4` |

## 2. Tareas completadas

### L5 — `docs/archived/`
14 documentos legacy movidos (sin eliminar):
- TODO_*.md (3), LIVE_PLAYBACK_*.md (5), SETUP_DESKTOP_WINDOWS.md,
  TASK_LIST_DETAILED.md, ACTIVITY_17_CACHE.md, BACKLOG_POST_LEVEL3.md,
  LEVEL1_SOLIDITY_RECOMMENDATIONS.md
- Índice: `docs/archived/INDEX.md`

### L6 — `.github/workflows/ci.yml`
- Trigger: push a `fix/master-audit-corrections` y `main`; PR a `main`
- Runner: ubuntu-latest, Python 3.12
- CPU-only torch (sin GPU en CI)
- Jobs: imports, test suite (425 tests), goalpost fallback

### L4 — `experiments/archived/INDEX.md`
- 40 directorios test_000 a test_040 catalogados con descripción
- Ningún archivo eliminado ni movido

### L3 — `scripts/validate_pipeline.py`
- 7 secciones: config, imports, checkpoints, artefactos, goalpost fallback, team assignment, tests
- Todo en verde: `[PASS] All checks passed.`
- Sin GPU requerida

## 3. Tareas omitidas y justificación

**L1 (rename level2/level3 modules)**: Los módulos `level2`/`level3` están referenciados en 40+ experimentos y en las pruebas existentes. Renombrarlos requeriría aliases temporales en todas las rutas de importación. Con 425 tests pasando y sin margen de tiempo seguro, el riesgo supera el beneficio cosmético.

**L2 (rename run_level* scripts)**: Los scripts legacy son referenciados por los experimentos históricos en `experiments/`. Renombrarlos sin wrappers rompería la reproducibilidad del historial. Se dejan como están con el índice en `experiments/archived/INDEX.md` como referencia.

## 4. Validación final

```
.venv/bin/python scripts/validate_pipeline.py
→ [PASS] All checks passed.

.venv/bin/python -m unittest discover -s tests -q
→ 425 tests: OK
```

## 5. Estado del proyecto al cierre de Fase 7

- Rama: `fix/master-audit-corrections`
- Todas las fases 0-7 completadas
- Gates A y B: documentación lista, pipeline validado, benchmark real, pendientes declarados
- Pendiente único de usuario: anotar `data/annotations/annotation_template.json` para IoU/F1
