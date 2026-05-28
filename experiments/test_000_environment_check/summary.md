# test_000_environment_check

## Estado

Parcialmente completado en escritorio. La validacion de GPU queda pendiente en la laptop MSI.

## Equipo usado

Escritorio Windows.

## Resultado

- Python 3.12.10 instalado.
- `.venv` creado.
- Dependencias de desarrollo instaladas.
- Imports de escritorio validados.

## Limitaciones

No valida CUDA, PyTorch GPU ni SAM 3. Esa validacion debe hacerse en la laptop MSI.

## Siguiente accion

Hacer pull en la laptop MSI, crear `.venv`, instalar `requirements-gpu.txt`, validar `nvidia-smi`, PyTorch CUDA y SAM 3.
