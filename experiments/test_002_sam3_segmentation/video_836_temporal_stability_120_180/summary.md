# test_002_sam3_temporal_stability

## Configuracion

- Video: `/home/guillermo/Vídeos/CopaFutMX/17 Abril/video-836_singular_display.mov`
- Ventana: `120` a `180`.
- Strides comparados: `1, 3, 5`.

## Resultados

- Stride `1`: balon `59/61`, robots `61/61`, removidas por ROI `56`, sin balon `135, 147`.
- Stride `3`: balon `19/21`, robots `21/21`, removidas por ROI `19`, sin balon `135, 147`.
- Stride `5`: balon `12/13`, robots `13/13`, removidas por ROI `12`, sin balon `135`.

## Artefactos

- Subcarpetas `stride_1`, `stride_3` y `stride_5` con detecciones, tracking, metricas y overlays.
- Cada `summary.md` incluye resumen por frame.
