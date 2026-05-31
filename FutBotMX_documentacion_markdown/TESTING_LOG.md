# TESTING_LOG

Este documento registra pruebas relevantes del proyecto FutBotMX.

Toda prueba pesada ejecutada en la laptop MSI debe documentarse aquí o en un archivo `summary.md` dentro de `experiments/test_xxx/`.

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
