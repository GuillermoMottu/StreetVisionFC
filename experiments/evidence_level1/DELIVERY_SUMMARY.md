# Resumen de entrega Nivel 1

## Estado

Nivel 1 queda respaldado con artefactos ligeros versionables: detecciones SAM 3, tracking, eventos, comparacion de prompts, pruebas en mas clips y benchmark MSI.

## Hallazgos principales

- SAM 3 funciona sobre video real CopaFutMX con checkpoint local `checkpoints/sam3/sam3.pt`.
- ROI rectangular inicial `x=0..1360`, `y=620..1808` reduce falsos positivos fuera de cancha sin perder el balon en la ventana base.
- Prompts base seleccionados: `green soccer field`, `small robot`, `ball`.
- En `video_836` frames `120-180`, SAM 3 detecta balon en `59/61` frames y robots en `61/61`.
- ByteTrack mejora continuidad frente al tracker simple: balon en `1` track y robots en `3` tracks sin inicios tardios en la ventana validada.
- Eventos Nivel 1 recalculados: `2` posesiones provisionales confiables, `1` colision provisional, `1` zona de actividad confiable.
- `shot` queda descartado en esa ventana: con umbral `350px/s` no genera candidatos y evita falsos positivos por jitter.
- En clips adicionales, `video_595` y `video_667` detectan balon/robots/cancha en `5/5` frames de muestra.
- `video_480` detecta robots/cancha en `5/5`, pero no balon en la muestra; requiere diagnostico antes de usarlo para eventos.
- Benchmark MSI: carga SAM 3 `15.5693s`; multi-frame `1.2031s/frame`; pico CUDA reserved aproximado `4236 MB`.

## Evidencia canonica

La lista canonica esta en `artifact_manifest.csv`. No se duplican videos ni checkpoints en esta carpeta; se referencian artefactos ya generados en `experiments/test_*`.

## Recomendacion siguiente

Para trabajo posterior, usar `video_595` y `video_667` como siguientes candidatos para tracking/eventos reales, y abrir una prueba especifica de recuperacion de balon en `video_480`.
