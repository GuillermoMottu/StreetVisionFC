# test_006_more_copafutmx_videos

## Objetivo

Validar SAM 3 en tres clips adicionales de CopaFutMX y comparar estabilidad basica de prompts fuera del clip `836`.

## Seleccion de clips

Se eligieron tres `singular_display` pequenos por tamano/duracion para una primera expansion controlada: `video_480`, `video_595` y `video_667`. Todos tienen duracion cercana a 8 segundos y resolucion vertical similar a `video_836`.

## Configuracion

- Fecha de ejecucion: `2026-05-31`.
- Equipo: Laptop MSI Thin GF63 12VE con RTX 4050.
- Checkpoint: `checkpoints/sam3/sam3.pt`.
- Frames por clip: `60`, `90`, `120`, `150`, `180`.
- Prompts base: `ball`, `small robot`, `green soccer field`.
- ROI: ancho completo del video, `y=620..height`.
- Tracking ligero: tracker simple con `max-distance-px=180` sobre detecciones filtradas.

## Resultados

| Clip | Duracion | Balon | Robots | Cancha | Detecciones | Nota |
|---|---:|---:|---:|---:|---:|---|
| `video_480` | `7.655s` | `0/5` | `5/5` | `5/5` | `10` | Ball not detected in the sampled window; robot and field are stable. |
| `video_595` | `8.072s` | `5/5` | `5/5` | `5/5` | `17` | All target classes detected in every sampled frame; one frame has duplicate ball/robot candidates. |
| `video_667` | `8.19s` | `5/5` | `5/5` | `5/5` | `28` | All target classes detected in every sampled frame; robot prompt returns multiple robot candidates per frame. |

## Problemas detectados

- `video_480`: no hay deteccion de balon con el prompt base en ningun frame de la muestra, aunque robot y cancha son estables. Requiere revisar si el balon esta ausente/ocluido o si hace falta prompt alternativo antes de usarlo para eventos.
- `video_595`: buen candidato para siguiente tracking/eventos; se observan duplicados puntuales de balon/robot que conviene filtrar por NMS o seleccion de confianza.
- `video_667`: buen candidato con robots muy visibles; el prompt `small robot` devuelve multiples robots por frame, por lo que conviene usar ByteTrack y deduplicacion al pasar a eventos.

## Artefactos

- `metrics.csv`
- `video_*/summary.md`
- `video_*/detections_filtered_roi.json`
- `video_*/tracks_filtered_roi.csv`
- `video_*/heatmap_filtered_roi.png`
- `video_*/overlay_frame_120_filtered_roi.png`

## Conclusion

La expansion a clips adicionales confirma que los prompts base generalizan bien para robots y cancha en `595` y `667`, mientras que `480` queda sin evidencia util de balon en la ventana muestreada. Para la siguiente etapa, `595` y `667` son mejores candidatos para tracking/eventos reales; `480` debe reservarse para diagnostico de balon.
