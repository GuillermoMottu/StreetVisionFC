# Cierre de Fase 6 — Documentación para evaluación

## 1. Resumen

| Tarea | ID | Estado | Archivo |
|---|---|---|---|
| Guía del evaluador | G1 | Completa | `docs/EVALUATOR_GUIDE.md` |
| README reescrito | G2 | Completo | `README.md` |
| Arquitectura técnica | G3 | Completa | `docs/TECHNICAL_ARCHITECTURE.md` |
| Pipeline SAM3 | G4 | Completa | `docs/SAM3_PIPELINE.md` |
| Guía de reproducibilidad | G5 | Completa | `docs/REPRODUCIBILITY.md` |
| Resumen de resultados | G6 | Completo | `docs/RESULTS_SUMMARY.md` |
| Índice de artefactos | G7 | Existía | `ARTIFACTS_INDEX.md` (raíz) |
| `.env.example` actualizado | — | Completo | OWLv2 y CUDA alloc conf añadidos |

## 2. Documentos creados

### `docs/EVALUATOR_GUIDE.md`
- Demo video, métricas clave, tabla de evidencias, comandos de validación
- Acceso a todo en ≤5 minutos
- Pendiente declarado: supervisado IoU/F1 (anotación humana)

### `docs/TECHNICAL_ARCHITECTURE.md`
- Diagrama ASCII del pipeline completo (frame → OWLv2 → SAM3 → ByteTrack → Team → Demo)
- Tabla de clases detectadas con método y tipo de máscara
- Mapa de módulos Python y formatos de datos

### `docs/SAM3_PIPELINE.md`
- Dos modos de prompt SAM3: texto vs geométrico (box)
- Diagrama del pipeline Grounded-SAM
- Gestión de VRAM (offload OWLv2)
- Tabla de cobertura de portería por clip
- `_CLIP_GOALS` fallback completo con cadena de decisión
- Limitaciones documentadas

### `docs/REPRODUCIBILITY.md`
- Instalación paso a paso desde cero
- PyTorch CUDA 13.0, SAM3 desde fuente, OWLv2 via HuggingFace
- Variables de entorno
- Comandos de validación y ejecución
- Tabla de constraints conocidos

### `docs/RESULTS_SUMMARY.md`
- R1: Benchmark SAM3 (2.237s/frame, 0.447 FPS, 3878 MB VRAM)
- R2: Tracking (61 frames, 3 robots, ByteTrack, equipos validados)
- R3: Cobertura de segmentación frame 143 (9/11 máscaras)
- R4: Goalpost multi-clip (836 ✓, 667 ✓, 595 fallback)
- R5: Métricas supervisadas — **PENDING_ANNOTATION** declarado explícitamente
- R6: 425 tests pass
- Limitaciones honestas

### `README.md` (reescrito)
- Sin narrativa dual de hardware (antes: Windows/MSI)
- Sin terminología de "Nivel 1/2/3"
- Arquitectura → Instalación → Variables → Comandos → Resultados
- Links a todos los docs nuevos

## 3. Validación

| Check | Estado |
|---|---|
| G1–G7 presentes | OK |
| README sin narrative legacy (grep) | 0 coincidencias |
| Tests: 425 pass, 0 fail | OK |
| `.env.example` con OWLv2 y CUDA alloc | OK |

## 4. Pendiente para Fase 7

- Archivar docs legacy de `docs/` (`TODO_*.md`, `LIVE_PLAYBACK_*.md`, etc.)
- CI básico sin GPU (GitHub Actions)
- Limpiar scripts legacy `run_level*`
