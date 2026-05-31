# test_002_sam3_segmentation

## Estado

Instalacion de codigo oficial y checkpoint completada en laptop MSI. Pendiente prueba con clip real.

## Motivo

SAM 3 requiere clip real local y evidencia visual. El escritorio no debe ejecutar inferencia pesada.

## Instalacion validada

- Repo oficial clonado en `.deps/sam3`.
- `.deps/` agregado a `.gitignore`.
- Paquete `sam3` instalado editable en `.venv`.
- Dependencias adicionales requeridas por imports de inferencia: `einops`, `pycocotools`, `psutil`.
- Hugging Face autenticado como `RomVqz`.
- Checkpoint oficial descargado localmente en `checkpoints/sam3/sam3.pt` (ignorado por Git).
- Validacion fuera del sandbox:
  - `torch 2.12.0+cu130`.
  - `torch.cuda.is_available() == True`.
  - GPU: NVIDIA GeForce RTX 4050 Laptop GPU.
  - Imports: `build_sam3_image_model`, `build_sam3_video_predictor`.
- Carga de checkpoint validada: `Sam3Image` en `cuda:0`.
- `SAM3Segmenter` conectado a inferencia real con autocast BF16.
- Prueba temporal end-to-end ejecutada con video sintetico en `/tmp`; genero `detections.json` sin errores.

## Nota tecnica

El repo oficial `facebookresearch/sam3` declara `numpy>=1.26,<2`. En Python 3.14 esto deja advertencias de dependencia con `pandas 3.0.3` y `opencv-python 4.13.0.92`, aunque los imports y pruebas actuales del proyecto siguen funcionando.

## Siguiente accion

Colocar un clip real local en `data/sample/clip_01.mp4` y ejecutar:

```bash
source .venv/bin/activate
python scripts/run_sam3_test.py --config configs/default.yaml --checkpoint checkpoints/sam3/sam3.pt --frame 0 --prompt ball
```
