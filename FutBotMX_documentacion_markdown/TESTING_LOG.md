# TESTING_LOG

Este documento registra pruebas relevantes del proyecto FutBotMX.

Toda prueba pesada ejecutada en la laptop MSI debe documentarse aquí o en un archivo `summary.md` dentro de `experiments/test_xxx/`.

---

## Test ID

`test_007_msi_sam3_benchmark_video_836`

## Fecha

`2026-05-31`

## Equipo utilizado

Laptop MSI Thin GF63 12VE con RTX 4050.

## Codigo usado

Commit base: `e80a0ef`.

## Video utilizado

Ruta local:

```text
/home/guillermo/Vídeos/CopaFutMX/17 Abril/video-836_singular_display.mov
```

Nota: el archivo de video no debe subirse a GitHub.

## Configuracion

- Script: `scripts/run_sam3_benchmark.py`.
- Checkpoint: `checkpoints/sam3/sam3.pt`.
- Prompts: `ball`, `small robot`, `green soccer field`.
- Corrida single-frame: frame `120`.
- Corrida multi-frame: frames `120`, `130`, `140`, `150`, `160`.
- Resolucion: `1360x1808`.
- FPS video: `59.707724425887264`.

## Hardware/software

- SO: `Linux-7.0.0-15-generic-x86_64-with-glibc2.43`.
- Python: `3.14.4`.
- GPU: `NVIDIA GeForce RTX 4050 Laptop GPU`.
- Driver NVIDIA: `595.71.05`.
- VRAM total reportada por `nvidia-smi`: `6141 MB`.
- PyTorch: `2.12.0+cu130`.
- CUDA runtime PyTorch: `13.0`.
- `torch.cuda.is_available() == True`.
- SAM 3: `0.1.0`.

## Resultados

- Tiempo de carga SAM 3: `15.5693s`.
- VRAM `nvidia-smi` antes/despues de carga: `12 -> 3626 MB`.
- Single-frame: `2.237s`, `2.237s/frame`, `0.447 FPS`, `5` detecciones.
- Multi-frame: `6.0157s`, `1.2031s/frame`, `0.8312 FPS`, `26` detecciones.
- Pico CUDA allocated/reserved single-frame: `3877.86/4236.0 MB`.
- Pico CUDA allocated/reserved multi-frame: `3878.11/4236.0 MB`.
- Multi-frame queda en `0.54x` del tiempo por frame de single-frame.

## Archivos subidos a GitHub

```text
scripts/run_sam3_benchmark.py
experiments/test_007_msi_benchmarks/video_836_sam3/summary.md
experiments/test_007_msi_benchmarks/video_836_sam3/metrics.csv
experiments/test_007_msi_benchmarks/video_836_sam3/benchmark.json
experiments/test_007_msi_benchmarks/video_836_sam3/config.yaml
```

## Conclusion

La RTX 4050 sostiene SAM 3 con margen util de VRAM para inferencia por imagen/frame en resolucion vertical `1360x1808`, con pico reservado cercano a `4.24 GB`. Las ventanas multi-frame amortizan mejor el costo por frame que corridas aisladas.

## Siguiente accion

Mantener benchmarks como referencia base y pasar a evidencia ligera final de Nivel 1.

---

## Test ID

`test_006_more_copafutmx_videos`

## Fecha

`2026-05-31`

## Equipo utilizado

Laptop MSI Thin GF63 12VE con RTX 4050.

## Codigo usado

Commit base: `fb34501`.

## Videos utilizados

Rutas locales:

```text
/home/guillermo/Vídeos/CopaFutMX/17 Abril/video-480_singular_display.mov
/home/guillermo/Vídeos/CopaFutMX/17 Abril/video-595_singular_display.mov
/home/guillermo/Vídeos/CopaFutMX/17 Abril/video-667_singular_display.mov
```

Nota: los archivos de video no deben subirse a GitHub.

## Configuracion

- Clips elegidos por tamano/duracion: `20.12MB`, `21.46MB`, `22.10MB`; todos cercanos a 8 segundos.
- Frames evaluados por clip: `60`, `90`, `120`, `150`, `180`.
- Prompts base: `ball`, `small robot`, `green soccer field`.
- Checkpoint: `checkpoints/sam3/sam3.pt`.
- ROI: ancho completo del video, `y=620..height`.
- Tracking ligero: tracker simple con `max-distance-px=180`.

## Resultados

- `video_480`: balon `0/5`, robots `5/5`, cancha `5/5`, `10` detecciones filtradas.
- `video_595`: balon `5/5`, robots `5/5`, cancha `5/5`, `17` detecciones filtradas.
- `video_667`: balon `5/5`, robots `5/5`, cancha `5/5`, `28` detecciones filtradas.
- ROI no removio detecciones en esta muestra.
- `video_480` queda marcado para diagnostico de balon ausente/ocluido o recall bajo del prompt.
- `video_595` y `video_667` quedan como mejores candidatos para continuar con tracking/eventos reales.

## Archivos subidos a GitHub

```text
experiments/test_001_video_ingestion/video_667_metadata.json
experiments/test_006_more_copafutmx_videos/summary.md
experiments/test_006_more_copafutmx_videos/metrics.csv
experiments/test_006_more_copafutmx_videos/video_*/summary.md
experiments/test_006_more_copafutmx_videos/video_*/detections.json
experiments/test_006_more_copafutmx_videos/video_*/detections_filtered_roi.json
experiments/test_006_more_copafutmx_videos/video_*/tracks_filtered_roi.csv
experiments/test_006_more_copafutmx_videos/video_*/heatmap_filtered_roi.png
experiments/test_006_more_copafutmx_videos/video_*/overlay_frame_120_filtered_roi.png
```

## Conclusion

Los prompts base generalizan bien para robots/cancha y tambien para balon en `595` y `667`. El clip `480` no ofrece deteccion de balon en la ventana muestreada, por lo que no debe usarse para eventos sin revisar ausencia, oclusion o prompts alternativos.

## Siguiente accion

Ejecutar tracking/eventos reales en `595` y `667`, y abrir una prueba especifica de prompts/frames para recuperar el balon en `480`.

---

## Test ID

`test_001_sam3_ball_prompt`

## Fecha

`YYYY-MM-DD`

## Equipo utilizado

Laptop MSI Thin GF63 12VE

## Motivo de usar este equipo

Prueba pesada de inferencia con GPU RTX 4050.

## Código usado

Commit: `<hash>`

## Video utilizado

Ruta local:

```text
data/raw/clip_01.mp4
```

Nota: no subir video pesado a GitHub.

## Configuración

- Modelo:
- Prompt:
- Resolución:
- Duración del clip:
- FPS:
- Tracking:
- Umbrales:

## Resultados

- Detecta balón:
- Detecta robots:
- Detecta campo:
- Mantiene tracking:
- Tiempo de procesamiento:
- Uso aproximado de VRAM:

## Archivos subidos a GitHub

```text
experiments/test_001/summary.md
experiments/test_001/metrics.csv
experiments/test_001/events.json
experiments/test_001/screenshots/frame_001.png
```

## Archivos no subidos

```text
overlay completo
frames extraídos
máscaras completas
checkpoints
video completo anotado
```

## Conclusión

Resumen honesto de la prueba.

Ejemplo:

```text
La prueba queda pendiente de validación. Aún no se confirma que SAM 3 funcione correctamente en la laptop MSI.
```

## Siguiente acción

Indicar qué debe hacerse después:

- En escritorio:
  - Ajustar código.
  - Revisar JSON/CSV.
  - Modificar configuración.
  - Documentar errores.
- En laptop:
  - Repetir inferencia.
  - Probar otro prompt.
  - Generar nuevas capturas.
  - Ejecutar benchmark.

---

## Test ID

`test_000_environment_check`

## Fecha

`2026-05-28`

## Equipo utilizado

Escritorio Windows.

## Codigo usado

Commit: `aca0ac1`.

## Configuracion

- Python: 3.12.10.
- Entorno: `.venv`.
- Dependencias: `requirements-dev.txt`.

## Resultados

- Imports de escritorio validados.
- Estructura base creada.
- Pipeline sintetico de Nivel 1 generado.
- GPU, CUDA, PyTorch CUDA y SAM 3 quedan pendientes para laptop MSI.

## Archivos subidos a GitHub

```text
experiments/test_000_environment_check/summary.md
experiments/test_000_environment_check/metrics.csv
experiments/test_000_environment_check/config.yaml
```

## Conclusion

El escritorio queda listo para desarrollo ligero. No se declara validacion SAM 3.

## Siguiente accion

Ejecutar validacion GPU en laptop MSI.

---

## Test ID

`test_000_environment_check_msi`

## Fecha

`2026-05-30`

## Equipo utilizado

Laptop MSI Thin GF63 12VE con Ubuntu 26.04 LTS.

## Codigo usado

Commit: `9b9e13f`.

## Configuracion

- GPU: NVIDIA GeForce RTX 4050 Laptop GPU.
- NVIDIA Driver: 595.71.05.
- CUDA reportado por driver: 13.2.
- Python: 3.14.4.
- Entorno: `.venv`.
- Dependencias: `requirements-gpu.txt`.
- PyTorch: 2.12.0+cu130.
- CUDA runtime de PyTorch: 13.0.

## Resultados

- `nvidia-smi` valida la RTX 4050 Laptop GPU.
- Imports principales validados: OpenCV, NumPy, Pandas, YAML, Matplotlib y Supervision.
- PyTorch CUDA validado fuera del sandbox de Codex:
  - `torch.cuda.is_available() == True`.
  - `torch.cuda.device_count() == 1`.
  - Dispositivo: NVIDIA GeForce RTX 4050 Laptop GPU.
- Pruebas unitarias ejecutadas en laptop: `Ran 3 tests ... OK`.

## Limitaciones

- SAM 3 oficial aun no estaba instalado ni validado en este punto.
- Dentro del sandbox de Codex, PyTorch puede reportar `cuda available False`; la validacion GPU real se hizo fuera del sandbox.

## Conclusion

La laptop MSI queda lista como entorno base de inferencia GPU. Falta instalar SAM 3 y ejecutar la primera segmentacion real.

## Siguiente accion

Instalar SAM 3 siguiendo su documentacion oficial y ejecutar `scripts/run_sam3_test.py` con evidencia ligera.

---

## Test ID

`test_002_sam3_install_msi`

## Fecha

`2026-05-30`

## Equipo utilizado

Laptop MSI Thin GF63 12VE con Ubuntu 26.04 LTS.

## Codigo usado

Commit: `9b9e13f`.

## Recursos usados

- `facebookresearch/sam3`.
- Hugging Face `facebook/sam3` o `facebook/sam3.1` para checkpoints.
- `roboflow/supervision` ya instalado desde `requirements-gpu.txt`.

## Configuracion

- SAM 3 clonado en `.deps/sam3`.
- Instalacion editable: `pip install -e .deps/sam3`.
- Dependencias extra para imports de inferencia: `einops`, `pycocotools`, `psutil`.
- PyTorch: `2.12.0+cu130`.

## Resultados

- Imports oficiales validados:
  - `build_sam3_image_model`.
  - `build_sam3_video_predictor`.
- PyTorch CUDA validado fuera del sandbox:
  - `torch.cuda.is_available() == True`.
  - Dispositivo: NVIDIA GeForce RTX 4050 Laptop GPU.
- Pruebas unitarias del proyecto: `Ran 3 tests ... OK`.

## Limitaciones

- Aun no se ejecuto inferencia con clip real del proyecto.
- SAM 3 requiere `numpy>=1.26,<2`; en Python 3.14 quedan advertencias de dependencia con pandas/OpenCV, aunque los imports actuales funcionan.

## Conclusion

La instalacion de codigo oficial SAM 3 queda completada. El checkpoint queda descargado y la carga en GPU queda validada.

## Siguiente accion

Colocar clip real local y ejecutar una prueba minima de segmentacion.

---

## Test ID

`test_002_sam3_checkpoint_msi`

## Fecha

`2026-05-30`

## Equipo utilizado

Laptop MSI Thin GF63 12VE con Ubuntu 26.04 LTS.

## Configuracion

- Hugging Face autenticado como `RomVqz`.
- Checkpoint: `checkpoints/sam3/sam3.pt`.
- Tamano local aproximado: 3.3 GB.
- Modelo cargado: `Sam3Image`.
- Dispositivo: `cuda:0`.

## Resultados

- Checkpoint `facebook/sam3` descargado desde Hugging Face.
- Carga local validada con `build_sam3_image_model(..., load_from_HF=False)`.
- `SAM3Segmenter` conectado a inferencia real de imagen/frame usando autocast BF16.
- `scripts/run_sam3_test.py` actualizado para generar `detections.json` y `summary.md`.
- Prueba temporal end-to-end con video sintetico en `/tmp` ejecuto sin errores.

## Limitaciones

- La imagen sintetica temporal no produjo detecciones; no se toma como metrica de calidad.
- Falta ejecutar sobre clip real de futbol robotico.

## Siguiente accion

Agregar `data/sample/clip_01.mp4` localmente y ejecutar:

```bash
python scripts/run_sam3_test.py --config configs/default.yaml --checkpoint checkpoints/sam3/sam3.pt --frame 0 --prompt ball
```

---

## Test ID

`test_002_sam3_real_video_836`

## Fecha

`2026-05-30`

## Equipo utilizado

Laptop MSI Thin GF63 12VE con RTX 4050.

## Video utilizado

Ruta local:

```text
/home/guillermo/Vídeos/CopaFutMX/17 Abril/video-836_singular_display.mov
```

Nota: el archivo de video no debe subirse a GitHub.

## Configuracion

- Frame evaluado: `143`.
- Resolucion del video: `1360x1808`.
- FPS: `59.707724425887264`.
- Prompts iniciales: `ball`, `robot`, `field`.
- Prompts refinados: `soccer ball`, `small orange ball`, `robot`.
- Checkpoint: `checkpoints/sam3/sam3.pt`.

## Resultados

- SAM 3 ejecuto correctamente sobre video real.
- Detecciones iniciales: `3`.
- Detecciones refinadas: `3`.
- Robots detectados: `2`.
- Balon/objeto pequeno detectado: `1`.
- Tracking desde detecciones reales generado: `tracks.csv`.
- Overlay visual generado: `overlay_frame_143.png`.
- Heatmap ligero generado: `heatmap.png`.

## Artefactos subidos a GitHub

```text
experiments/test_001_video_ingestion/video_836_metadata.json
experiments/test_002_sam3_segmentation/video_836_frame_143/detections.json
experiments/test_002_sam3_segmentation/video_836_frame_143/tracks.csv
experiments/test_002_sam3_segmentation/video_836_frame_143/overlay_frame_143.png
experiments/test_002_sam3_segmentation/video_836_frame_143_soccer_ball/detections.json
experiments/test_002_sam3_segmentation/video_836_frame_143_soccer_ball/overlay_frame_143.png
```

## Conclusion

SAM 3 ya produce detecciones utiles sobre video real de CopaFutMX. Las cajas de robots son visualmente correctas en el frame evaluado. La deteccion del balon requiere revisar prompts y mas frames para confirmar precision.

## Siguiente accion

Ejecutar una muestra multi-frame del mismo clip y probar prompts especificos para campo/cancha.

---

## Test ID

`test_002_sam3_multiframe_video_836`

## Fecha

`2026-05-30`

## Equipo utilizado

Laptop MSI Thin GF63 12VE con RTX 4050.

## Video utilizado

Ruta local:

```text
/home/guillermo/Vídeos/CopaFutMX/17 Abril/video-836_singular_display.mov
```

## Configuracion

- Frames evaluados: `30`, `90`, `143`, `200`, `260`.
- Prompts: `ball`, `robot`.
- Checkpoint: `checkpoints/sam3/sam3.pt`.
- Tracking: tracker simple por centroides con `max-distance-px 220`.

## Resultados

- Detecciones totales: `18`.
- Frame 30: `1` balon, `3` robots.
- Frame 90: `0` balon, `4` robots.
- Frame 143: `1` balon, `2` robots.
- Frame 200: `1` balon, `3` robots.
- Frame 260: `0` balon, `3` robots.
- `tracks.csv` generado desde detecciones reales.
- `events.json` generado desde tracks reales.
- Overlays generados para los cinco frames.

## Limitaciones

- Los frames estan espaciados; los IDs de tracking no deben interpretarse como continuidad tactica confiable todavia.
- La deteccion de balon no fue completa en todos los frames.
- El evento `shot` generado es provisional porque depende de tracking disperso.

## Conclusion

SAM 3 detecta robots de forma consistente en la muestra multi-frame y detecta el balon en 3 de 5 frames. El pipeline completo ya acepta detecciones reales de SAM 3 hasta tracking, eventos y visualizaciones ligeras.

## Siguiente accion

Ejecutar una ventana de frames consecutivos o semi-consecutivos para mejorar continuidad de tracking y validar eventos con mayor confianza.

---

## Test ID

`test_002_sam3_window_120_160_video_836`

## Fecha

`2026-05-30`

## Equipo utilizado

Laptop MSI Thin GF63 12VE con RTX 4050.

## Configuracion

- Video: `/home/guillermo/Vídeos/CopaFutMX/17 Abril/video-836_singular_display.mov`.
- Frames evaluados: `120`, `125`, `130`, `135`, `140`, `145`, `150`, `155`, `160`.
- Prompts: `ball`, `robot`.
- Checkpoint: `checkpoints/sam3/sam3.pt`.
- Tracking: tracker simple por centroides con `max-distance-px 120`.

## Resultados

- Detecciones totales: `39`.
- Balon detectado en `8/9` frames.
- Robots detectados en `9/9` frames.
- `tracks.csv`, `events.json`, `heatmap.png` y overlays generados.
- Eventos provisionales: `shot`, `activity_zone`.

## Limitaciones

- El prompt `robot` tambien detecta un robot elevado/fuera de cancha en el fondo.
- Falta filtrar por ROI/campo antes de considerar eventos como definitivos.
- Frame 135 no tuvo deteccion de balon.

## Conclusion

La ventana consecutiva valida que SAM 3 puede sostener deteccion temporal util en video real. El siguiente problema ya no es instalacion, sino filtrado espacial y refinamiento de tracking.

## Siguiente accion

Agregar filtrado por zona de cancha/ROI para descartar robots fuera del campo y recalcular tracking/eventos.

---

## Test ID

`test_002_sam3_temporal_stability_120_180_video_836`

## Fecha

`2026-05-30`

## Equipo utilizado

Laptop MSI Thin GF63 12VE con RTX 4050.

## Codigo usado

Commit: `476c036`.

## Video utilizado

Ruta local:

```text
/home/guillermo/Vídeos/CopaFutMX/17 Abril/video-836_singular_display.mov
```

## Configuracion

- Ventana evaluada: frames `120-180`.
- Strides: `1`, `3`, `5`.
- Prompts: `ball`, `robot`.
- ROI: `x=0..1360`, `y=620..1808`.
- Checkpoint: `checkpoints/sam3/sam3.pt`.
- Tracking: tracker simple por centroides con `max-distance-px 120`.

## Resultados

- `frame_stride=1`: balon `59/61`, robots `61/61`, frames sin balon `135`, `147`.
- `frame_stride=3`: balon `19/21`, robots `21/21`, frames sin balon `135`, `147`.
- `frame_stride=5`: balon `12/13`, robots `13/13`, frame sin balon `135`.
- Detecciones removidas por ROI: `56` en stride 1, `19` en stride 3, `12` en stride 5.
- Overlays representativos generados para frames `120`, `150` y `180`.

## Archivos subidos a GitHub

```text
experiments/test_002_sam3_segmentation/video_836_temporal_stability_120_180/summary.md
experiments/test_002_sam3_segmentation/video_836_temporal_stability_120_180/stride_*/summary.md
experiments/test_002_sam3_segmentation/video_836_temporal_stability_120_180/stride_*/metrics.csv
experiments/test_002_sam3_segmentation/video_836_temporal_stability_120_180/stride_*/detections_filtered_roi.json
experiments/test_002_sam3_segmentation/video_836_temporal_stability_120_180/stride_*/tracks_filtered_roi.csv
experiments/test_002_sam3_segmentation/video_836_temporal_stability_120_180/stride_*/overlay_frame_*_filtered_roi.png
```

## Conclusion

SAM 3 mantiene deteccion temporal util en una ventana consecutiva mas larga. El balon es estable en la mayoria de frames, pero las perdidas repetidas en frames 135 y 147 deben revisarse visualmente y compararse contra prompts alternativos antes de cerrar prompts base.

## Siguiente accion

Comparar prompts de balon, robots y campo/cancha para definir el set base de CopaFutMX.

---

## Test ID

`test_002_sam3_prompt_comparison_120_180_video_836`

## Fecha

`2026-05-30`

## Equipo utilizado

Laptop MSI Thin GF63 12VE con RTX 4050.

## Codigo usado

Commit base: `78be8e2`.

## Video utilizado

Ruta local:

```text
/home/guillermo/Vídeos/CopaFutMX/17 Abril/video-836_singular_display.mov
```

## Configuracion

- Frames evaluados: `120`, `135`, `143`, `147`, `150`, `180`.
- Prompts de balon: `ball`, `orange ball`, `small orange ball`, `soccer ball`.
- Prompts de robots: `robot`, `soccer robot`, `wheeled robot`, `small robot`.
- Prompts de cancha: `field`, `playing field`, `green soccer field`.
- ROI: `x=0..1360`, `y=620..1808`.
- Checkpoint: `checkpoints/sam3/sam3.pt`.

## Resultados

- Balon: `ball` detecta `4/6` frames, igual que `orange ball`, con confianza media ligeramente mayor. `small orange ball` detecta `3/6`. `soccer ball` no detecta.
- Robots: `small robot` detecta `6/6` frames, `17` detecciones filtradas y mejor confianza media que `robot` y `soccer robot`.
- Cancha: `green soccer field` detecta `5/6` frames; `field` no detecta y `playing field` solo detecta `1/6`.
- Revision visual ligera: `ball`, `small robot` y `green soccer field` producen overlays coherentes en los frames revisados.
- `configs/default.yaml` actualizado con `green_soccer_field`, `small_robot`, `ball`.

## Archivos subidos a GitHub

```text
experiments/test_002_sam3_segmentation/video_836_prompt_comparison_120_180/summary.md
experiments/test_002_sam3_segmentation/video_836_prompt_comparison_120_180/comparison.csv
experiments/test_002_sam3_segmentation/video_836_prompt_comparison_120_180/visual_review.md
experiments/test_002_sam3_segmentation/video_836_prompt_comparison_120_180/*/*/summary.md
experiments/test_002_sam3_segmentation/video_836_prompt_comparison_120_180/*/*/metrics.csv
experiments/test_002_sam3_segmentation/video_836_prompt_comparison_120_180/{ball/ball,robot/small_robot,field/green_soccer_field}/overlay_frame_*_filtered_roi.png
```

## Conclusion

Prompts base seleccionados para CopaFutMX: `green soccer field`, `small robot`, `ball`. La deteccion de balon sigue perdiendo frames `135` y `147`; esta limitacion debe considerarse en tracking y eventos.

## Siguiente accion

Evaluar tracking real con frames consecutivos filtrados por ROI usando los prompts base seleccionados.

---

## Test ID

`test_003_tracking_real_video_836`

## Fecha

`2026-05-30`

## Equipo utilizado

Laptop MSI Thin GF63 12VE con RTX 4050.

## Codigo usado

Commit base: `5789842`.

## Video utilizado

Ruta local:

```text
/home/guillermo/Vídeos/CopaFutMX/17 Abril/video-836_singular_display.mov
```

## Configuracion

- Detecciones: `experiments/test_002_sam3_segmentation/video_836_temporal_stability_120_180/stride_1/detections_filtered_roi.json`.
- Ventana: frames `120-180`.
- ROI ya aplicado: `x=0..1360`, `y=620..1808`.
- Tracker simple: `max-distance-px=120`, `max-lost-frames=15`.
- ByteTrack: `supervision.ByteTrack`, `track_activation_threshold=0.25`, `lost_track_buffer=30`, `minimum_matching_threshold=0.8`, `frame_rate=59.707724425887264`.

## Resultados

- Tracker simple:
  - Balon: `1` track, longitud `59`, salto maximo `5.1px`.
  - Robots: `4` tracks, `1` inicio tardio, longitud media `37.25`, salto maximo `95.7px`.
- ByteTrack:
  - Balon: `1` track, longitud `59`, salto maximo `5.1px`.
  - Robots: `3` tracks, `0` inicios tardios, longitud media `48.67`, salto maximo `33.7px`.
- Revision visual ligera en frames `120`, `150` y `180`: no se observan cambios de ID incorrectos obvios; sin ground truth, se mantiene como validacion provisional.
- Tracker recomendado para la siguiente etapa: `ByteTrack`.

## Archivos subidos a GitHub

```text
experiments/test_003_tracking/video_836_real_tracking_120_180/summary.md
experiments/test_003_tracking/video_836_real_tracking_120_180/metrics.csv
experiments/test_003_tracking/video_836_real_tracking_120_180/tracks_simple.csv
experiments/test_003_tracking/video_836_real_tracking_120_180/tracks_bytetrack.csv
experiments/test_003_tracking/video_836_real_tracking_120_180/heatmap_simple.png
experiments/test_003_tracking/video_836_real_tracking_120_180/heatmap_bytetrack.png
experiments/test_003_tracking/video_836_real_tracking_120_180/overlay_*_frame_*.png
```

## Conclusion

ByteTrack mejora la continuidad de robots frente al tracker simple en la ventana real `120-180`, reduciendo fragmentacion y saltos maximos. El tracker simple sigue siendo suficiente como fallback ligero, pero eventos y posesion deben recalcularse con ByteTrack.

## Siguiente accion

Recalcular eventos Nivel 1 con tracks reales filtrados y revisar falsos positivos de `shot`.

---

## Test ID

`test_004_events_real_video_836`

## Fecha

`2026-05-30`

## Equipo utilizado

Laptop MSI Thin GF63 12VE con RTX 4050.

## Codigo usado

Commit base: `adbdf2b`.

## Video utilizado

Ruta local:

```text
/home/guillermo/Vídeos/CopaFutMX/17 Abril/video-836_singular_display.mov
```

## Configuracion

- Tracks: `experiments/test_003_tracking/video_836_real_tracking_120_180/tracks_bytetrack.csv`.
- Ventana: frames `120-180`.
- FPS: `59.707724425887264`.
- Resolucion/cancha usada: `1360x1808`.
- Posesion: `possession_distance_px=190`, `possession_min_frames=8`.
- Tiro: `shot_min_ball_speed_px_per_sec=350`.
- Colision: `collision_distance_px=35`, `collision_min_frames=4`.

## Resultados

- Distancia balon-robot mas cercana: min `113.4px`, p50 `158.3px`, p90 `187.5px`, max `210.0px`.
- Velocidad maxima del balon: `307.3px/s`.
- Con umbral previo `180px/s`, `shot` generaba `11` candidatos; con `350px/s`, genera `0`.
- Eventos generados:
  - `2` posesiones: frames `120-133` y `148-180`.
  - `1` colision: frames `128-142`.
  - `1` zona de actividad: `attacking_third`.
- `shot` queda descartado en esta ventana por falso positivo de jitter/movimiento pequeno cerca del gol.

## Archivos subidos a GitHub

```text
experiments/test_004_events/video_836_real_events_120_180/summary.md
experiments/test_004_events/video_836_real_events_120_180/events.json
experiments/test_004_events/video_836_real_events_120_180/event_metrics.csv
experiments/test_004_events/video_836_real_events_120_180/event_config.json
experiments/test_004_events/video_836_real_events_120_180/nearest_robot_distance.csv
experiments/test_004_events/video_836_real_events_120_180/ball_speed.csv
experiments/test_004_events/video_836_real_events_120_180/overlay_event_frame_*.png
```

## Conclusion

Eventos Nivel 1 quedan recalculados con tracks reales ByteTrack. Posesion queda `provisional_confiable`, colision queda `provisional`, zona de actividad queda `confiable` y tiro queda descartado para esta ventana.

## Siguiente accion

Preparar evidencia ligera final de Nivel 1 y/o ejecutar el mismo flujo en mas clips CopaFutMX.

---

## Test ID

`test_003_tracking`, `test_004_events`, `test_005_visualizations`

## Fecha

`2026-05-28`

## Equipo utilizado

Escritorio Windows.

## Codigo usado

Commit: `aca0ac1`.

## Configuracion

`configs/default.yaml`, con datos sinteticos generados por `scripts/create_synthetic_level1_artifacts.py`.

## Resultados

- `tracks.csv` generado desde detecciones sinteticas.
- `events.json` generado con eventos Nivel 1 sinteticos.
- `heatmap.png` generado desde tracks sinteticos.

## Conclusion

El pipeline base de escritorio funciona para contratos, formatos y flujo ligero. La calidad real depende de SAM 3 y tracking validado en laptop MSI.

## Siguiente accion

Repetir el flujo con detecciones reales generadas por SAM 3 en la laptop.
