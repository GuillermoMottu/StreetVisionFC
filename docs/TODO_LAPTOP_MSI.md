# TODO Laptop MSI

Este checklist concentra el trabajo que debe continuar en la Laptop MSI con Ubuntu, RTX 4050, SAM 3 y los videos reales de CopaFutMX.

## Estado actual

- [x] Driver NVIDIA validado con `nvidia-smi`.
- [x] PyTorch CUDA validado en RTX 4050.
- [x] SAM 3 oficial instalado desde `facebookresearch/sam3`.
- [x] Checkpoint `facebook/sam3` descargado en `checkpoints/sam3/sam3.pt`.
- [x] `SAM3Segmenter` conectado a inferencia real.
- [x] Primer video real validado: `/home/guillermo/Vídeos/CopaFutMX/17 Abril/video-836_singular_display.mov`.
- [x] Ventana real `120-160` procesada con SAM 3.
- [x] Detecciones, tracking, eventos y overlays generados desde datos reales.

## Prioridad 1 - Filtrado De Cancha

- [x] Definir ROI inicial de cancha para `video-836_singular_display.mov`.
- [x] Implementar filtro por ROI para descartar detecciones fuera del campo.
- [x] Aplicar filtro a detecciones SAM 3 antes de tracking.
- [x] Recalcular `tracks.csv` de la ventana `120-160`.
- [x] Recalcular `events.json` con detecciones filtradas.
- [x] Generar overlays comparativos antes/despues del filtro.
- [x] Documentar falsos positivos removidos, especialmente robots fuera de cancha.

Resultado: ROI inicial rectangular `x=0..1360`, `y=620..1808` aplicada sobre centroides. En la ventana `120-160` conserva 8/8 detecciones de balon y reduce robots de 31 a 23, removiendo 8 detecciones de fondo por encima de la cancha.

## Prioridad 2 - Estabilidad Temporal

- [x] Procesar ventana consecutiva mas larga del clip 836.
- [x] Probar intervalos `frame_stride=1`, `frame_stride=3` y `frame_stride=5`.
- [x] Medir cuantas veces se detecta el balon por ventana.
- [x] Medir cuantas veces se detectan robots por ventana.
- [x] Identificar frames donde SAM 3 pierde el balon.
- [x] Guardar resumen por frame en `summary.md`.
- [x] Generar overlays representativos de inicio, mitad y fin.

Resultado: ventana `120-180` procesada en `experiments/test_002_sam3_segmentation/video_836_temporal_stability_120_180/` con ROI `x=0..1360`, `y=620..1808`. En `frame_stride=1`, SAM 3 detecta balon en 59/61 frames y robots en 61/61; pierde el balon en frames 135 y 147. En `frame_stride=3`, detecta balon en 19/21 y robots en 21/21; pierde balon en 135 y 147. En `frame_stride=5`, detecta balon en 12/13 y robots en 13/13; pierde balon en 135. Overlays representativos generados para frames 120, 150 y 180.

## Prioridad 3 - Prompts SAM 3

- [x] Comparar prompts de balon: `ball`, `orange ball`, `small orange ball`, `soccer ball`.
- [x] Comparar prompts de robots: `robot`, `soccer robot`, `wheeled robot`, `small robot`.
- [x] Comparar prompts de campo: `field`, `playing field`, `green soccer field`.
- [x] Registrar precision visual por prompt.
- [x] Seleccionar prompts base para CopaFutMX.
- [x] Actualizar `configs/default.yaml` si se define un set mejor.

Resultado: comparacion en `experiments/test_002_sam3_segmentation/video_836_prompt_comparison_120_180/` sobre frames `120`, `135`, `143`, `147`, `150` y `180`. Seleccion base: `green soccer field`, `small robot`, `ball`. `ball` supera a `orange ball` por confianza media ligeramente mayor con el mismo recall; `small robot` mejora recall/confianza frente a `robot`; `green soccer field` es el unico prompt de cancha con deteccion consistente.

## Prioridad 4 - Tracking Real

- [x] Evaluar el tracker simple con frames consecutivos filtrados por ROI.
- [x] Probar ByteTrack mediante `supervision` si el tracker simple no mantiene IDs.
- [x] Comparar estabilidad de IDs entre tracker simple y ByteTrack.
- [x] Documentar cambios de ID incorrectos.
- [x] Definir parametros recomendados para videos verticales de CopaFutMX.

Resultado: comparacion en `experiments/test_003_tracking/video_836_real_tracking_120_180/` usando detecciones filtradas por ROI de la ventana consecutiva `120-180`. El tracker simple mantiene el balon en 1 track y robots en 4 tracks con 1 inicio tardio; ByteTrack mantiene el balon en 1 track y robots en 3 tracks sin inicios tardios. Recomendacion para la siguiente etapa: ByteTrack mediante `supervision` con `track_activation_threshold=0.25`, `lost_track_buffer=30`, `minimum_matching_threshold=0.8`, `frame_rate` del video y ROI previo.

## Prioridad 5 - Eventos Nivel 1

- [x] Recalcular posesion con tracks filtrados.
- [x] Revisar si eventos `shot` son reales o falsos positivos por tracking.
- [x] Ajustar umbrales de velocidad del balon.
- [x] Ajustar distancia de posesion en pixeles para resolucion `1360x1808`.
- [x] Validar eventos visualmente con overlays.
- [x] Marcar eventos como provisionales o confiables en `summary.md`.

Resultado: validacion en `experiments/test_004_events/video_836_real_events_120_180/` usando `tracks_bytetrack.csv`. Se ajusto posesion a `190px` para la resolucion `1360x1808` y tiro a `350px/s` para evitar falsos positivos por jitter. Eventos generados: 2 posesiones provisionales confiables, 1 colision provisional y 1 zona de actividad confiable. `shot` queda descartado en esta ventana: el umbral previo `180px/s` daba 11 candidatos, pero la revision indica movimiento pequeno/jitter cerca del gol.

## Prioridad 6 - Mas Videos CopaFutMX

- [x] Elegir 3 clips adicionales por tamano/duracion.
- [x] Inspeccionar metadatos con `scripts/inspect_video.py`.
- [x] Ejecutar SAM 3 en una ventana corta por clip.
- [x] Comparar rendimiento entre clips.
- [x] Detectar problemas por iluminacion, camara vertical o oclusiones.
- [x] Registrar resultados en `FutBotMX_documentacion_markdown/TESTING_LOG.md`.

Resultado: expansion en `experiments/test_006_more_copafutmx_videos/` con clips `video_480`, `video_595` y `video_667`, todos `singular_display` de ~8 segundos. En frames `60`, `90`, `120`, `150` y `180`, `video_595` y `video_667` detectan balon, robots y cancha en `5/5` frames; `video_480` detecta robots/cancha en `5/5`, pero no detecta balon en la muestra. Se generaron metadatos, detecciones filtradas por ROI, tracks ligeros, heatmaps, overlays centrales y `metrics.csv`. Siguiente recomendacion: usar `595`/`667` para tracking-eventos y reservar `480` para diagnostico de balon ausente/ocluido o recall bajo del prompt.

## Prioridad 7 - Benchmarks MSI

- [ ] Medir tiempo de carga de SAM 3.
- [ ] Medir tiempo por frame.
- [ ] Medir uso aproximado de VRAM durante inferencia.
- [ ] Medir diferencia entre una corrida de 1 frame y ventanas multi-frame.
- [ ] Documentar configuracion de hardware/software exacta.

## Prioridad 8 - Evidencia Ligera

- [ ] Mantener fuera de Git videos completos, checkpoints y outputs pesados.
- [ ] Subir solo JSON, CSV, summaries, heatmaps y capturas ligeras.
- [ ] Revisar tamano de overlays antes de versionarlos.
- [ ] Crear una carpeta final de evidencia Nivel 1.
- [ ] Preparar resumen de hallazgos para entrega.

## Comandos Base

Activar entorno:

```bash
source .venv/bin/activate
```

Inspeccionar video:

```bash
python scripts/inspect_video.py --video "/home/guillermo/Vídeos/CopaFutMX/17 Abril/video-836_singular_display.mov"
```

Ejecutar SAM 3 en ventana corta:

```bash
python scripts/run_sam3_test.py \
  --video "/home/guillermo/Vídeos/CopaFutMX/17 Abril/video-836_singular_display.mov" \
  --experiment experiments/test_002_sam3_segmentation/video_836_window_120_160_ball_robot \
  --checkpoint checkpoints/sam3/sam3.pt \
  --frame 120 --frame 125 --frame 130 --frame 135 --frame 140 --frame 145 --frame 150 --frame 155 --frame 160 \
  --prompt ball --prompt robot
```

Generar tracking:

```bash
python scripts/run_tracking.py \
  --detections experiments/test_002_sam3_segmentation/video_836_window_120_160_ball_robot/detections.json \
  --output experiments/test_002_sam3_segmentation/video_836_window_120_160_ball_robot/tracks.csv \
  --max-distance-px 120
```

Filtrar detecciones por ROI:

```bash
python scripts/filter_detections_roi.py \
  --detections experiments/test_002_sam3_segmentation/video_836_window_120_160_ball_robot/detections.json \
  --output experiments/test_002_sam3_segmentation/video_836_window_120_160_ball_robot/detections_filtered_roi.json \
  --roi 0 620 1360 1808
```

Generar eventos:

```bash
python scripts/run_events.py \
  --tracks experiments/test_002_sam3_segmentation/video_836_window_120_160_ball_robot/tracks.csv \
  --output experiments/test_002_sam3_segmentation/video_836_window_120_160_ball_robot/events.json \
  --fps 59.707724425887264 \
  --field-width 1360 \
  --field-height 1808
```

Comparar estabilidad temporal:

```bash
python scripts/run_temporal_stability.py \
  --video "/home/guillermo/Vídeos/CopaFutMX/17 Abril/video-836_singular_display.mov" \
  --checkpoint checkpoints/sam3/sam3.pt \
  --experiment experiments/test_002_sam3_segmentation/video_836_temporal_stability_120_180 \
  --start-frame 120 --end-frame 180 \
  --stride 1 --stride 3 --stride 5 \
  --prompt ball --prompt robot \
  --roi 0 620 1360 1808 \
  --max-distance-px 120
```

Comparar prompts SAM 3:

```bash
python scripts/run_prompt_comparison.py \
  --video "/home/guillermo/Vídeos/CopaFutMX/17 Abril/video-836_singular_display.mov" \
  --checkpoint checkpoints/sam3/sam3.pt \
  --experiment experiments/test_002_sam3_segmentation/video_836_prompt_comparison_120_180 \
  --frame 120 --frame 135 --frame 143 --frame 147 --frame 150 --frame 180 \
  --group all \
  --roi 0 620 1360 1808
```

Comparar tracking real:

```bash
python scripts/run_tracking_comparison.py \
  --detections experiments/test_002_sam3_segmentation/video_836_temporal_stability_120_180/stride_1/detections_filtered_roi.json \
  --experiment experiments/test_003_tracking/video_836_real_tracking_120_180 \
  --video "/home/guillermo/Vídeos/CopaFutMX/17 Abril/video-836_singular_display.mov" \
  --max-distance-px 120 \
  --max-lost-frames 15
```

Validar eventos reales:

```bash
python scripts/run_event_validation.py \
  --tracks experiments/test_003_tracking/video_836_real_tracking_120_180/tracks_bytetrack.csv \
  --experiment experiments/test_004_events/video_836_real_events_120_180 \
  --video "/home/guillermo/Vídeos/CopaFutMX/17 Abril/video-836_singular_display.mov" \
  --fps 59.707724425887264 \
  --field-width 1360 \
  --field-height 1808 \
  --possession-distance-px 190 \
  --shot-min-speed-px-per-sec 350
```
