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

Commit: pendiente hasta commit inicial.

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

Hacer commit/push inicial y ejecutar validacion GPU en laptop MSI.

---

## Test ID

`test_003_tracking`, `test_004_events`, `test_005_visualizations`

## Fecha

`2026-05-28`

## Equipo utilizado

Escritorio Windows.

## Codigo usado

Commit: pendiente hasta commit inicial.

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
