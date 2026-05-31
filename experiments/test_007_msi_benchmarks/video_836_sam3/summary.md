# test_007_msi_benchmarks

## Configuracion

- Video: `/home/guillermo/Vídeos/CopaFutMX/17 Abril/video-836_singular_display.mov`
- Resolucion: `1360x1808`.
- FPS video: `59.707724425887264`.
- Checkpoint: `checkpoints/sam3/sam3.pt`.
- Prompts: `ball, small robot, green soccer field`.
- Frames single: `120`.
- Frames multi: `120, 130, 140, 150, 160`.

## Hardware/software

- SO: `Linux-7.0.0-15-generic-x86_64-with-glibc2.43`.
- Python: `3.14.4`.
- GPU: `NVIDIA GeForce RTX 4050 Laptop GPU`.
- Driver NVIDIA: `595.71.05`.
- VRAM total: `6141.0 MB`.
- PyTorch: `2.12.0+cu130`.
- CUDA disponible para PyTorch: `True`.
- CUDA runtime PyTorch: `13.0`.

## Resultados

- Carga SAM 3: `15.5693s`; VRAM nvidia-smi antes/despues `12.0` -> `3626.0` MB.
- `single_frame`: `1` frames, `2.237s`, `2.237s/frame`, `0.447` FPS efectivos, detecciones `5`, pico CUDA allocated/reserved `3877.86`/`4236.0` MB, nvidia-smi `3626.0` -> `4372.0` MB.
- `multi_frame`: `5` frames, `6.0157s`, `1.2031s/frame`, `0.8312` FPS efectivos, detecciones `26`, pico CUDA allocated/reserved `3878.11`/`4236.0` MB, nvidia-smi `4372.0` -> `4372.0` MB.

## Comparacion

- Multi-frame queda en `0.54x` del tiempo por frame de la corrida single-frame.

## Artefactos

- `benchmark.json`
- `metrics.csv`
- `config.yaml`
