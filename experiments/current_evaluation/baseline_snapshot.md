# Baseline Snapshot — FutBotMX / StreetVisionFC
> Generado: 2026-06-10 (inicio de Fase 0)
> Rama: fix/master-audit-corrections (creada desde main @ 6761ff7)

## Estado del repositorio al inicio

| Campo | Valor |
|---|---|
| Rama base (origen) | main |
| Commit HEAD (main) | 6761ff7 — docs: add usage guide, decision log, and closure report for live playback (actividad 35) |
| Rama de trabajo | fix/master-audit-corrections |
| Archivos sin seguimiento | PLAN_MAESTRO_FUTBOTMX_AJUSTADO.md |
| Cambios staged | Ninguno |

## Estructura del proyecto al inicio

```
StreetVisionFC/
├── .deps/               # SAM3 y dependencias locales
├── .venv/               # Entorno virtual Python
├── configs/
│   └── default.yaml     # TIENE rutas absolutas en level2_closure (brecha C4)
├── data/
│   └── sample/          # Vacío (brecha C4)
├── docs/                # Documentación existente (incluye docs dual máquina)
├── experiments/         # Resultados históricos (43 directorios)
├── outputs/             # Outputs generados
├── scripts/             # Scripts de pipeline (~50 scripts)
├── src/futbotmx/        # Código fuente principal
│   ├── config.py
│   ├── events/
│   ├── io/
│   ├── level3/          # team_assignment, advanced_events, spatial, etc.
│   ├── metrics/
│   ├── segmentation/    # sam3_segmenter.py
│   ├── tracking/
│   ├── video_io/
│   └── visualization/
└── tests/               # 28 archivos de test
```

## Tests baseline

| Métrica | Valor |
|---|---|
| Total tests ejecutados | 268 |
| Pasados | 247 |
| Errores | 21 |
| Fallos | 0 |

**Causa de errores (todos pre-existentes):**
- `ModuleNotFoundError: No module named 'cv2'` — 2 tests
- `ModuleNotFoundError: No module named 'matplotlib'` — 17 tests
- `ModuleNotFoundError: No module named 'numpy'` — 2 tests

**Diagnóstico:** El runner `python3 -m unittest` invoca el Python del sistema (3.14.4) que no tiene los paquetes del `.venv`. Los mismos tests pasan al usarse `.venv/bin/python`. Esta es una condición pre-existente, no introducida por esta fase.

## Brechas críticas identificadas (del plan maestro)

| ID | Brecha | Observación |
|---|---|---|
| C1 | SAM 3 no exporta masks pixel-level | `mask_path` siempre null; overlay.py solo dibuja rectángulos |
| C2 | No existe video demo de ≤2 min | Sin MP4 funcional accesible |
| C3 | Equipos en `neutral` en todos los tracks | team_assignment.py existe pero no conectado al flujo |
| C4 | Pipeline no reproducible | Rutas absolutas en `default.yaml`; sin `LICENSE` |

## Herramientas externas faltantes

| Herramienta | Estado | Bloqueante para |
|---|---|---|
| ffmpeg | NO INSTALADO | Fase 3 (demo video) |
| ffprobe | NO INSTALADO | Fase 3 (validación duración) |

## Archivos de interés para fases posteriores

| Archivo | Relevancia |
|---|---|
| `configs/default.yaml` | Contiene rutas absolutas → Fase 1 |
| `src/futbotmx/segmentation/sam3_segmenter.py` | API SAM 3 → Fase 2 |
| `src/futbotmx/level3/team_assignment.py` | Team assignment → Fase 4 |
| `src/futbotmx/visualization/overlay.py` | Overlays → Fase 3 |
| `scripts/create_demo_video.py` | Demo video → Fase 3 |
| `scripts/run_sam3_benchmark.py` | Benchmark → Fase 5 |
