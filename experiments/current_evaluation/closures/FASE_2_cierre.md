# Cierre de Fase 2 — Segmentación SAM 3: masks y portería

## 1. Resumen de cambios

- **Inspección real de la API de SAM 3** con modelo cargado (3.3 GB checkpoint, RTX 4050): documentada en `sam3_output_inspection.md`
- **Extracción de masks implementada** en `sam3_segmenter.py`:
  - Nuevo parámetro `mask_output_dir` en `SAM3Segmenter.__init__`
  - `_detections_from_output` ahora extrae `output["masks"]` (tensor `(N, 1, H, W)` bool)
  - Nueva función `_save_mask`: guarda cada máscara como PNG grayscale (uint8 0/255) en `{mask_output_dir}/frame_{idx:06d}_{class}_{det:03d}.png`
  - `Detection.mask_path` se rellena con la ruta absoluta al PNG
- **Round-trip validado**: `save_detections → load_detections` preserva `mask_path` en 7/7 detecciones
- **Comparación de prompts para portería** ejecutada (5 prompts × 6 frames, threshold=0.3 y confirmado a 0.1): 0 detecciones en todos los prompts
- **Fallback geométrico inicial** implementado en `goalpost_fallback.py` con coordenadas por clip derivadas de detección HSV de color amarillo
- **Pipeline box-prompt → SAM3 para portería** — adición de 2026-06-13:
  - Nuevo método `SAM3Segmenter.segment_with_box_prompt(image, class_name, bbox_pixel)`:  
    convierte bbox (x0,y0,x1,y1) pixel → cxcywh normalizado → `processor.add_geometric_prompt` → mask pixel-level real
  - Nueva función `detect_goalposts_with_mask(image, frame_index, clip_id, segmenter)`:  
    combina coordenadas HSV confirmadas + SAM3 box-prompt → portería con `mask_path` poblado
  - **Resultado validado**: `goalpost conf=0.96 [mask]` en frame 143 — todos los 8 elementos tienen mask pixel-level
- **Portería añadida a `configs/default.yaml`** con `detection_method: geometric_fallback` y documentación de los 5 prompts fallidos
- `src/futbotmx/segmentation/__init__.py` actualizado para exponer el fallback y `detect_goalposts_with_mask`

## 2. Archivos modificados/creados

| Archivo | Cambio | Motivo |
|---|---|---|
| `src/futbotmx/segmentation/sam3_segmenter.py` | Añadida extracción de masks y `mask_output_dir` | Brecha C1 — masks pixel-level |
| `src/futbotmx/segmentation/goalpost_fallback.py` | Fallback geométrico + `detect_goalposts_with_mask` | Portería no detectable por texto; box-prompt da mask real |
| `src/futbotmx/segmentation/__init__.py` | Exponer `detect_goalposts`, `detect_goalposts_with_mask` | Acceso público al fallback y al pipeline box-prompt |
| `configs/default.yaml` | Añadido bloque `goalpost` con método y prompts fallidos | Documentar decisión |
| `experiments/current_evaluation/sam3_output_inspection.md` | Creado — inspección real de la API | Requisito obligatorio de Fase 2 |
| `experiments/current_evaluation/masks/` | 8 PNGs generados (frame 143, incl. portería) | Evidencia de masks pixel-level |
| `experiments/current_evaluation/detections_frame143.json` | Creado — 7 detecciones con mask_path | Evidencia de round-trip (paso inicial) |
| `experiments/current_evaluation/detections_frame143_with_goalpost_mask.json` | Creado — 8 detecciones incluyendo portería con mask | Evidencia final: todos con mask |
| `experiments/current_evaluation/goalpost_prompt_comparison/` | comparison.csv + 10 JSON | Evidencia de prompt comparison |
| `experiments/current_evaluation/masks/visualization_frame143_v2.png` | Visualización final — 8 elementos con mask pixel-level | Verificación visual completa |
| `scripts/run_goalpost_mask_test.py` | Nuevo — test del pipeline box-prompt | Reproducibilidad |
| `scripts/visualize_detections.py` | Nuevo — generador de visualizaciones | Reproducibilidad |

## 3. Pruebas ejecutadas

| Comando / Acción | Resultado | Evidencia |
|---|---|---|
| Inspección real SAM 3 (checkpoint cargado) | Estructura de salida documentada | `sam3_output_inspection.md` |
| `segment_video(video_836, [143], [...])` con `mask_output_dir` | 7 detecciones, 7 masks exportadas | `experiments/current_evaluation/masks/` |
| Round-trip `save_detections → load_detections` | 7/7 mask_path conservados | Terminal |
| Mask PNG abierta con PIL | (1360, 1808), modo L, válida | Terminal |
| Goalpost comparison: 5 prompts × 6 frames @ threshold=0.3 | 0/30 frames con detección | `goalpost_prompt_comparison/comparison.csv` |
| Goalpost comparison: 3 prompts @ threshold=0.1 | 0 detecciones | Terminal |
| `detect_goalposts_with_mask(frame=143, clip_id='video_836', segmenter=...)` | goalpost conf=0.96, mask=YES | Terminal — 2026-06-13 |
| `python -m unittest discover -s tests` | 425 tests, 0 fallos | 2026-06-13 (todos pasan) |

## 4. Validación QA

| Criterio | Estado | Observaciones |
|---|---|---|
| API SAM 3 inspeccionada con modelo real antes de implementar | Cumplido | `sam3_output_inspection.md` |
| Al menos una mask PNG exportada y verificable | Cumplido | 8 PNGs en `experiments/current_evaluation/masks/` |
| `mask_path` no nulo en JSON de detecciones — TODOS los elementos | Cumplido | 8/8 (robots + campo + pelota + portería) — 2026-06-13 |
| Round-trip mask_path conservado tras reload | Cumplido | 7/7 (paso original), 8/8 en dataset final |
| Evidencia de prompt comparison para portería | Cumplido | `comparison.csv` con 5 prompts, todos 0 detecciones |
| Portería con mask pixel-level real (no solo bbox) | Cumplido | `detect_goalposts_with_mask` → `goalpost conf=0.96 [mask]` |
| Visualización con mask de portería verificable visualmente | Cumplido | `visualization_frame143_v2.png` — overlay amarillo en portería |
| Tests ejecutados sin regresiones | Cumplido | 425 tests, 0 fallos — 2026-06-13 |

## 5. Riesgos o pendientes

### Portería — SAM 3 no detecta por texto; sí por box-prompt
SAM 3 no puede detectar la portería del juego de robots con ningún prompt textual (incluso a threshold=0.1). Sin embargo, al proporcionar las coordenadas confirmadas por HSV como geometric prompt, SAM 3 genera una mask pixel-level real con `conf=0.96`. Las coordenadas de portería para video_595 y video_667 son estimaciones — requieren verificación HSV cuando los videos estén disponibles.

### Masks — solo frame 143 en evidencia
Las 7 masks exportadas son del frame 143 con 3 prompts (small_robot, ball, green_soccer_field). En el pipeline de producción, `mask_output_dir` debe pasarse al segmentador para cada run. El script `run_sam3_test.py` puede recibir actualización para pasar este parámetro (Fase 3).

### BLOQUEO Fase 3
~~`ffmpeg` no instalado~~ — **Resuelto**: ffmpeg 8.0.1 disponible en `/usr/bin/ffmpeg` (confirmado 2026-06-11).

## 6. Tareas pendientes del usuario (humano en el loop)

Ninguna para esta fase.

## 7. Recomendación

**La fase está lista para aprobación.** La API real de SAM 3 fue inspeccionada antes de implementar, las masks son pixel-level verificables (1360×1808 PNG), el round-trip funciona, la comparación de prompts para portería está documentada con evidencia real, y el fallback geométrico es explícitamente diferenciado de segmentación real.

## 8. Espera de aprobación

No continuaré con la Fase 3 hasta aprobación explícita del usuario.
