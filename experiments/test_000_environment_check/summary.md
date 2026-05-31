# test_000_environment_check

## Estado

Completado para entorno base de escritorio y laptop MSI. Codigo oficial SAM 3 instalado, checkpoint descargado y carga en GPU validada.

## Equipo usado

- Escritorio Windows.
- Laptop MSI Thin GF63 12VE con Ubuntu 26.04 LTS y RTX 4050 Laptop GPU.

## Resultado

- Python 3.12.10 instalado.
- `.venv` creado.
- Dependencias de desarrollo instaladas.
- Imports de escritorio validados.
- Driver NVIDIA 595.71.05 instalado en laptop MSI.
- `nvidia-smi` valida RTX 4050 Laptop GPU con CUDA 13.2 del driver.
- `.venv` de laptop creado con Python 3.14.4.
- Dependencias GPU instaladas desde `requirements-gpu.txt`.
- PyTorch 2.12.0+cu130 valida CUDA fuera del sandbox: `torch.cuda.is_available() == True`.
- Pruebas unitarias del repositorio ejecutadas correctamente en laptop: `Ran 3 tests ... OK`.

## Limitaciones

SAM 3 aun no esta validado con clip real. En ejecuciones dentro del sandbox de Codex, PyTorch puede no ver la GPU aunque fuera del sandbox si la ve.

## Siguiente accion

Ejecutar `scripts/run_sam3_test.py` con un clip real y evidencia ligera en `experiments/test_002_sam3_segmentation/`.
