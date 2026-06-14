# SAM 3 Output Inspection — FutBotMX Fase 2
> Generado: 2026-06-11 — inspeccionado con modelo real sobre frame 143 de video-836

## Método de inspección

1. Carga del modelo real: `checkpoints/sam3/sam3.pt` (3.3 GB) en CUDA (RTX 4050).
2. Extracción del frame 143 de `video-836_singular_display.mov` (1808×1360 px).
3. Llamada a `processor.set_image(img)` → `state`.
4. Llamada a `processor.set_text_prompt(state=state, prompt="small robot")` → `state`.
5. Inspección del `state` retornado.

## Estructura real de la salida

`set_text_prompt()` retorna el mismo `state` dict, con las siguientes claves relevantes:

| Clave | Tipo | Shape (ejemplo con 5 detecciones) | Descripción |
|---|---|---|---|
| `state["boxes"]` | `torch.Tensor` float32 | `(N, 4)` | Bounding boxes en píxeles `[x0, y0, x1, y1]` |
| `state["scores"]` | `torch.Tensor` bfloat16 | `(N,)` | Confidence scores (escalares) |
| `state["masks"]` | `torch.Tensor` bool | `(N, 1, H, W)` | Masks binarias a resolución original |
| `state["masks_logits"]` | `torch.Tensor` float32 | `(N, 1, H, W)` | Logits pre-threshold (sigmoid) |
| `state["backbone_out"]` | dict | — | Features internas del backbone |
| `state["geometric_prompt"]` | `Prompt` | — | Estado de prompts geométricos |
| `state["original_height"]` | int | — | Alto original de la imagen en px |
| `state["original_width"]` | int | — | Ancho original de la imagen en px |

## Resultado con frame 143, prompt "small robot"

```
Frame shape: (1808, 1360, 3)   ← (H, W, C)
Detecciones: 5 robots (confidence threshold 0.3)
Scores: [0.719, 0.609, 0.578, 0.852, 0.578]
Masks shape: (5, 1, 1808, 1360), dtype=torch.bool
Mask[0] true pixels: 26,006  ← máscara pixel-level real, no estimación
```

## Bug identificado en código anterior

`_detections_from_output` solo leía `output.get("boxes")` y `output.get("scores")`:
```python
# ANTES (incompleto):
boxes = output.get("boxes")
scores = output.get("scores")
# masks → NUNCA extraídas → mask_path siempre None
```

## Corrección implementada

`_detections_from_output` ahora también lee `output.get("masks")` y, cuando se pasa
un `mask_output_dir`, guarda cada máscara como PNG `(H, W)` uint8 (0/255) y rellena
`Detection.mask_path` con la ruta absoluta.

Nombre de archivo de mask:
```
{mask_output_dir}/frame_{frame_index:06d}_{class_name}_{det_idx:03d}.png
```

## Comportamiento cuando no hay detecciones

Si ninguna detección supera el `confidence_threshold`, el estado retorna tensores vacíos:
```
masks: shape=(0, 1, H, W)
boxes: shape=(0, 4)
scores: shape=(0,)
```
`_detections_from_output` retorna `[]` (sin cambios en comportamiento anterior).

## Portería — resultado de comparación de prompts

Ver `goalpost_prompt_comparison/comparison.csv` para los 5 prompts evaluados.

Prompts evaluados: `goal`, `soccer goal`, `goalpost`, `small soccer goal`, `robot soccer goal`

El mejor prompt para portería quedó documentado en la comparación. Si ninguno fue
estable, se implementó fallback geométrico (ver sección de fallback en FASE_2_cierre.md).
