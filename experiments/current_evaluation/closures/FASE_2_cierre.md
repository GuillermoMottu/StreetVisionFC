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
- **Fallback geométrico implementado** en `src/futbotmx/segmentation/goalpost_fallback.py`:
  - Basado en `field_calibration.json` (spatial model existente)
  - Retorna 2 detecciones por frame (top_goal, bottom_goal) con `confidence=0.0` y `mask_path=None`
  - `confidence=0.0` señaliza explícitamente "no es inferencia de modelo"
- **Portería añadida a `configs/default.yaml`** con `detection_method: geometric_fallback` y documentación de los 5 prompts fallidos
- `src/futbotmx/segmentation/__init__.py` actualizado para exponer el fallback

## 2. Archivos modificados/creados

| Archivo | Cambio | Motivo |
|---|---|---|
| `src/futbotmx/segmentation/sam3_segmenter.py` | Añadida extracción de masks y `mask_output_dir` | Brecha C1 — masks pixel-level |
| `src/futbotmx/segmentation/goalpost_fallback.py` | Creado — fallback geométrico | Portería no detectable por SAM 3 |
| `src/futbotmx/segmentation/__init__.py` | Exponer `detect_goalposts` | Acceso público al fallback |
| `configs/default.yaml` | Añadido bloque `goalpost` con método y prompts fallidos | Documentar decisión |
| `experiments/current_evaluation/sam3_output_inspection.md` | Creado — inspección real de la API | Requisito obligatorio de Fase 2 |
| `experiments/current_evaluation/masks/` | 7 PNGs generados (frame 143) | Evidencia de masks pixel-level |
| `experiments/current_evaluation/detections_frame143.json` | Creado — detecciones con mask_path | Evidencia de round-trip |
| `experiments/current_evaluation/goalpost_prompt_comparison/` | comparison.csv + 10 JSON | Evidencia de prompt comparison |

## 3. Pruebas ejecutadas

| Comando / Acción | Resultado | Evidencia |
|---|---|---|
| Inspección real SAM 3 (checkpoint cargado) | Estructura de salida documentada | `sam3_output_inspection.md` |
| `segment_video(video_836, [143], [...])` con `mask_output_dir` | 7 detecciones, 7 masks exportadas | `experiments/current_evaluation/masks/` |
| Round-trip `save_detections → load_detections` | 7/7 mask_path conservados | Terminal |
| Mask PNG abierta con PIL | (1360, 1808), modo L, válida | Terminal |
| Goalpost comparison: 5 prompts × 6 frames @ threshold=0.3 | 0/30 frames con detección | `goalpost_prompt_comparison/comparison.csv` |
| Goalpost comparison: 3 prompts @ threshold=0.1 | 0 detecciones | Terminal |
| Fallback geométrico `detect_goalposts(143, 'video_836')` | 2 detecciones top/bottom, conf=0.0 | Terminal |
| `python3 -m unittest discover -s tests` | 268 tests, 247 pass, 21 errores | Idéntico al baseline |

## 4. Validación QA

| Criterio | Estado | Observaciones |
|---|---|---|
| API SAM 3 inspeccionada con modelo real antes de implementar | Cumplido | `sam3_output_inspection.md` |
| Al menos una mask PNG exportada y verificable | Cumplido | 7 PNGs en `experiments/current_evaluation/masks/` |
| `mask_path` no nulo en JSON de detecciones | Cumplido | 7/7 detecciones frame 143 |
| Round-trip mask_path conservado tras reload | Cumplido | 7/7 |
| Evidencia de prompt comparison para portería | Cumplido | `comparison.csv` con 5 prompts, todos 0 detecciones |
| Fallback geométrico documentado como fallback (no SAM 3) | Cumplido | `confidence=0.0`, `mask_path=None`, comentario en código |
| Tests ejecutados sin regresiones | Cumplido | 21 errores — idénticos al baseline |

## 5. Riesgos o pendientes

### Portería — imposibilidad de SAM 3
SAM 3 no puede detectar la portería del juego de robots con ningún prompt textual, incluso a threshold=0.1. El fallback geométrico proporciona posición aproximada basada en calibración del campo. **No equivale a segmentación pixel-level** — es una estimación de bbox. Documentado explícitamente en:
- `src/futbotmx/segmentation/goalpost_fallback.py` (docstring)
- `configs/default.yaml` (campo `goalpost.reason` con fecha y prompts fallidos)

### Masks — solo frame 143 en evidencia
Las 7 masks exportadas son del frame 143 con 3 prompts (small_robot, ball, green_soccer_field). En el pipeline de producción, `mask_output_dir` debe pasarse al segmentador para cada run. El script `run_sam3_test.py` puede recibir actualización para pasar este parámetro (Fase 3).

### BLOQUEO Fase 3 persiste
`ffmpeg`/`ffprobe` no instalados → `sudo apt-get install ffmpeg` antes de la Fase 3.

## 6. Tareas pendientes del usuario (humano en el loop)

Ninguna para esta fase.

## 7. Recomendación

**La fase está lista para aprobación.** La API real de SAM 3 fue inspeccionada antes de implementar, las masks son pixel-level verificables (1360×1808 PNG), el round-trip funciona, la comparación de prompts para portería está documentada con evidencia real, y el fallback geométrico es explícitamente diferenciado de segmentación real.

## 8. Espera de aprobación

No continuaré con la Fase 3 hasta aprobación explícita del usuario.
