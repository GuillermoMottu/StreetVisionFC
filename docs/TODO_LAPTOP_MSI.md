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

- [ ] Procesar ventana consecutiva mas larga del clip 836.
- [ ] Probar intervalos `frame_stride=1`, `frame_stride=3` y `frame_stride=5`.
- [ ] Medir cuantas veces se detecta el balon por ventana.
- [ ] Medir cuantas veces se detectan robots por ventana.
- [ ] Identificar frames donde SAM 3 pierde el balon.
- [ ] Guardar resumen por frame en `summary.md`.
- [ ] Generar overlays representativos de inicio, mitad y fin.

## Prioridad 3 - Prompts SAM 3

- [ ] Comparar prompts de balon: `ball`, `orange ball`, `small orange ball`, `soccer ball`.
- [ ] Comparar prompts de robots: `robot`, `soccer robot`, `wheeled robot`, `small robot`.
- [ ] Comparar prompts de campo: `field`, `playing field`, `green soccer field`.
- [ ] Registrar precision visual por prompt.
- [ ] Seleccionar prompts base para CopaFutMX.
- [ ] Actualizar `configs/default.yaml` si se define un set mejor.

## Prioridad 4 - Tracking Real

- [ ] Evaluar el tracker simple con frames consecutivos filtrados por ROI.
- [ ] Probar ByteTrack mediante `supervision` si el tracker simple no mantiene IDs.
- [ ] Comparar estabilidad de IDs entre tracker simple y ByteTrack.
- [ ] Documentar cambios de ID incorrectos.
- [ ] Definir parametros recomendados para videos verticales de CopaFutMX.

## Prioridad 5 - Eventos Nivel 1

- [ ] Recalcular posesion con tracks filtrados.
- [ ] Revisar si eventos `shot` son reales o falsos positivos por tracking.
- [ ] Ajustar umbrales de velocidad del balon.
- [ ] Ajustar distancia de posesion en pixeles para resolucion `1360x1808`.
- [ ] Validar eventos visualmente con overlays.
- [ ] Marcar eventos como provisionales o confiables en `summary.md`.

## Prioridad 6 - Mas Videos CopaFutMX

- [ ] Elegir 3 clips adicionales por tamano/duracion.
- [ ] Inspeccionar metadatos con `scripts/inspect_video.py`.
- [ ] Ejecutar SAM 3 en una ventana corta por clip.
- [ ] Comparar rendimiento entre clips.
- [ ] Detectar problemas por iluminacion, camara vertical o oclusiones.
- [ ] Registrar resultados en `FutBotMX_documentacion_markdown/TESTING_LOG.md`.

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
