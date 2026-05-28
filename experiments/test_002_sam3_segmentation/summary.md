# test_002_sam3_segmentation

## Estado

Bloqueado hasta ejecutar en laptop MSI.

## Motivo

SAM 3 requiere instalacion oficial, GPU compatible y evidencia visual. El escritorio no debe ejecutar inferencia pesada.

## Siguiente accion

En laptop MSI, instalar SAM 3, validar PyTorch CUDA y ejecutar:

```bash
python scripts/run_sam3_test.py --config configs/default.yaml
```
