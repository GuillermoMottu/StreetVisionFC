# Cierre de Fase 5 — Rigor profesional: métricas y benchmark

## 1. Resumen

| Tarea | Estado | Evidencia |
|---|---|---|
| R1: Infraestructura ground truth | Completa | 8 frames exportados + plantilla COCO |
| R1-H: Anotación humana | **Pendiente** | Requiere anotación manual de `annotation_template.json` |
| R2: Métricas supervisadas | Infraestructura lista, pendiente de anotación | `supervised_metrics.json` → `pending_annotation` |
| R3: Benchmark SAM 3 | Completo | `benchmark_summary.json` — datos reales de GPU |
| R4: Pinning de dependencias | Completo | `requirements-gpu.txt` con 17 deps pinadas |
| R5: Validación pipeline | Completo | Todos los checks pasan |

## 2. R3 — Benchmark SAM 3 (RTX 4050 Laptop, CUDA 13.0)

| Métrica | Single frame | Multi-frame (5) |
|---|---|---|
| Tiempo / frame | **2.237 s** | **1.203 s** |
| FPS efectivo | **0.447** | **0.831** |
| VRAM pico (allocated) | 3878 MB | 3878 MB |
| VRAM pico (nvidia-smi) | 4372 MB | 4372 MB |
| Carga del modelo | 15.57 s (una sola vez) | — |

- GPU: NVIDIA GeForce RTX 4050 Laptop (5772 MB total, 3626 MB usados tras carga)
- Prompts: 3 texto (`small robot`, `ball`, `green soccer field`) + 1 box-prompt (portería)
- Fuente: `experiments/test_007_msi_benchmarks/video_836_sam3/benchmark.json`

## 3. R4 — Dependencies pinadas

`requirements-gpu.txt` actualizado con versiones exactas verificadas:
- torch==2.12.0, torchvision==0.27.0
- numpy==1.26.4, opencv-python==4.13.0.92, pillow==12.2.0
- supervision==0.28.0, timm==1.0.27, einops==0.8.2
- huggingface-hub==1.17.0, pandas==2.3.0, scipy==1.15.3
- pycocotools==2.0.11, psutil==7.2.2, python-dotenv==1.1.0

## 4. R1 — Infraestructura ground truth

- Frames exportados: 8 (120, 130, 140, 143, 150, 160, 170, 180) en `data/annotations/frames/`
- Plantilla COCO: `data/annotations/annotation_template.json`
- Clases: small_robot (1), ball (2), green_soccer_field (3), goalpost (4)
- Estado: `pending_annotation` — el usuario debe anotar bboxes/masks manualmente

**Cómo anotar:**  
Abrir los PNGs en `data/annotations/frames/`, dibujar bboxes por clase, y llenar el
array `"annotations"` de `annotation_template.json` en formato COCO. Luego re-ejecutar:
```bash
python scripts/run_phase5_metrics.py
```

## 5. R5 — Validación del pipeline

| Check | Estado |
|---|---|
| `load_config('configs/default.yaml')` | OK |
| Imports: SAM3Segmenter, detect_goalposts_with_mask | OK |
| Round-trip detecciones: 8/8 con mask_path | OK |
| Team assignment: 146 filas con equipo no-neutral | OK |
| `python -m unittest discover -s tests` | OK (425 tests) |

## 6. Pendiente (R1-H)

La infraestructura está lista. Las métricas supervisadas (IoU/Dice/F1) **no pueden
calcularse sin anotaciones humanas**. Según el plan: se entrega con estado
`pending_annotation` documentado en `supervised_metrics.json`. No se fabrican
anotaciones artificiales.
