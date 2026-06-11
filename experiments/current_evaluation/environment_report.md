# Environment Report — FutBotMX / StreetVisionFC
> Generated: 2026-06-10 (Fase 0 baseline)

## Sistema operativo

| Campo | Valor |
|---|---|
| OS | Ubuntu 26.04 LTS (Codename: resolute) |
| Kernel | Linux 7.0.0-22-generic |
| Arquitectura | x86_64 |
| Host | guillermo-Thin-GF63-12VE (MSI Thin GF63) |

## Python

| Campo | Valor |
|---|---|
| Versión (.venv) | 3.14.4 |
| Versión (sistema) | 3.14.4 |
| Compilador | GCC 15.2.0 |

**Nota:** El proyecto usa `.venv/` con todos los paquetes instalados. La invocación `python3 -m unittest discover -s tests` usa el Python del sistema (sin venv), lo que causa 21 errores de ImportError por `cv2`, `matplotlib` y `numpy`. Esto es una condición pre-existente de baseline (ver `baseline_tests.log`). Para ejecución funcional, usar `.venv/bin/python`.

## GPU

| Campo | Valor |
|---|---|
| Nombre | NVIDIA GeForce RTX 4050 Laptop GPU |
| VRAM total | 5772 MiB (~5.6 GB) |
| VRAM en uso (baseline) | 23 MiB |
| Driver NVIDIA | 595.71.05 |
| CUDA (driver) | 13.2 |

## PyTorch / CUDA

| Campo | Valor |
|---|---|
| PyTorch | 2.12.0+cu130 |
| CUDA (torch) | 13.0 |
| `torch.cuda.is_available()` | **True** |
| Dispositivo 0 | NVIDIA GeForce RTX 4050 Laptop GPU |

## Dependencias clave instaladas en .venv

| Paquete | Versión |
|---|---|
| torch | 2.12.0 |
| torchvision | 0.27.0 |
| numpy | 1.26.4 |
| opencv-python | 4.13.0.92 |
| matplotlib | 3.10.9 |
| pandas | 3.0.3 |
| pillow | 12.2.0 |
| einops | 0.8.2 |
| pycocotools | 2.0.11 |
| psutil | 7.2.2 |
| supervision | 0.28.0 |
| scipy | 1.17.1 |
| timm | 1.0.27 |
| pyyaml | 6.0.3 |
| tqdm | 4.67.3 |
| sam3 | (editable, git: facebookresearch/sam3@8e451d5) |
| futbotmx | 0.1.0 (editable, git: GuillermoMottu/StreetVisionFC@6761ff7) |

## Herramientas externas

| Herramienta | Estado | Impacto |
|---|---|---|
| `ffmpeg` | **NO ENCONTRADO** | **BLOQUEANTE para Fase 3** (generación de video demo) |
| `ffprobe` | **NO ENCONTRADO** | **BLOQUEANTE para Fase 3** (validación de duración del MP4) |
| `nvidia-smi` | Disponible (driver 595.71.05) | OK |

### BLOQUEO REGISTRADO — Fase 3

`ffmpeg` y `ffprobe` no están instalados en el sistema. La Fase 3 (generación del video demo con overlays) depende de estas herramientas. Antes de iniciar la Fase 3 se debe instalar:

```bash
sudo apt-get install ffmpeg
```

Esto debe hacerse antes de la Fase 3. Se registra aquí en el baseline para no descubrirlo en la Fase 3.

## Freeze completo de .venv

Ver archivo: `requirements-freeze.txt` en este directorio.
