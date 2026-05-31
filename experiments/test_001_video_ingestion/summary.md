# test_001_video_ingestion

## Estado

Validado con clip real local en laptop MSI.

## Equipo recomendado

Escritorio para prueba ligera inicial. Laptop MSI si el clip es mas grande.

## Resultado actual

La ingesta fue validada por prueba unitaria con video sintetico y con clips reales locales de CopaFutMX.

## Clip principal

- Ruta local: `/home/guillermo/Vídeos/CopaFutMX/17 Abril/video-836_singular_display.mov`
- FPS: `59.707724425887264`
- Resolucion: `1360x1808`
- Frames: `286`
- Duracion: `4.79` segundos

## Artefactos ligeros

- `video_836_metadata.json`
- `video_480_metadata.json`
- `video_595_metadata.json`

## Siguiente accion

Usar `video-836_singular_display.mov` como primer clip de validacion SAM 3 y seleccionar mas clips por tamano/duracion conforme avance el benchmark.
