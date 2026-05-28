# test_001_video_ingestion

## Estado

Pendiente con clip real local.

## Equipo recomendado

Escritorio para prueba ligera inicial. Laptop MSI si el clip es mas grande.

## Resultado actual

La ingesta fue validada por prueba unitaria con video sintetico. Falta ejecutar `scripts/inspect_video.py` contra un clip real local que no debe subirse a GitHub.

## Siguiente accion

Ejecutar:

```powershell
.\.venv\Scripts\python.exe scripts\inspect_video.py --video data\sample\clip_01.mp4 --output experiments\test_001_video_ingestion\metadata.json
```
