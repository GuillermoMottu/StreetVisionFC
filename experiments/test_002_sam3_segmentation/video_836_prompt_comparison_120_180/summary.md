# test_002_sam3_prompt_comparison

## Configuracion

- Video: `/home/guillermo/Vídeos/CopaFutMX/17 Abril/video-836_singular_display.mov`
- Frames evaluados: `120, 135, 143, 147, 150, 180`.
- Prompts comparados por grupo: `ball`, `robot`, `field`.

## Resultados metricos

### ball
- `ball`: filtrado `4/6`, total `4`, confianza `0.6865`, sin deteccion `135, 147`.
- `orange ball`: filtrado `4/6`, total `4`, confianza `0.6758`, sin deteccion `135, 147`.
- `small orange ball`: filtrado `3/6`, total `3`, confianza `0.6940`, sin deteccion `135, 147, 180`.
- `soccer ball`: filtrado `0/6`, total `0`, confianza `0.0000`, sin deteccion `120, 135, 143, 147, 150, 180`.
- Seleccion metrica preliminar: `ball`.

### robot
- `robot`: filtrado `6/6`, total `14`, confianza `0.7564`, sin deteccion `ninguno`.
- `soccer robot`: filtrado `6/6`, total `14`, confianza `0.7188`, sin deteccion `ninguno`.
- `wheeled robot`: filtrado `3/6`, total `6`, confianza `0.6576`, sin deteccion `120, 143, 180`.
- `small robot`: filtrado `6/6`, total `17`, confianza `0.8024`, sin deteccion `ninguno`.
- Seleccion metrica preliminar: `small robot`.

### field
- `field`: filtrado `0/6`, total `0`, confianza `0.0000`, sin deteccion `120, 135, 143, 147, 150, 180`.
- `playing field`: filtrado `1/6`, total `1`, confianza `0.5703`, sin deteccion `135, 143, 147, 150, 180`.
- `green soccer field`: filtrado `5/6`, total `5`, confianza `0.6195`, sin deteccion `147`.
- Seleccion metrica preliminar: `green soccer field`.

## Decision

- Prompts base recomendados por metrica automatica: `ball=ball, robot=small robot, field=green soccer field`.
- Revision visual ligera registrada en `visual_review.md`.
- Prompts base seleccionados para CopaFutMX: `green soccer field`, `small robot`, `ball`.
- `configs/default.yaml` actualizado con estos prompts base.

## Artefactos

- `comparison.csv`
- `visual_review.md`
- Subcarpetas por grupo y prompt con `detections.json`, `detections_filtered_roi.json`, `metrics.csv` y `summary.md`.
- Overlays representativos conservados solo para prompts seleccionados.
