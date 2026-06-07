# Calibracion Manual De Cancha

## Resultado

- Estado: `editor_generado`.
- Regla: `manual_field_calibration_v0.1`.
- Clips: `video_595, video_667`.
- Entrada editable: `field_calibration.json`.
- Editor: `calibration_editor.html`.

## Uso

```bash
.venv/bin/python scripts/run_field_calibration_editor.py
```

Abrir el editor local, seleccionar cuatro esquinas en orden `top_left`, `top_right`, `bottom_right`, `bottom_left` y guardar el JSON.

## Integracion

```bash
.venv/bin/python scripts/run_level3_spatial_model.py --calibration-json experiments/test_029_manual_calibration/field_calibration.json --experiment experiments/test_030_manual_spatial_model
```

## Clips

- `video_595` frame `120` overlay `../test_017_level2_closure/video_595/overlay_lvl2_evt_000001_frame_120.png` confianza seed `0.95`.
- `video_667` frame `120` overlay `../test_017_level2_closure/video_667/overlay_lvl2_evt_000001_frame_120.png` confianza seed `0.95`.

## Manifest

- Filas en `calibration_editor_manifest.csv`: `7`.

## Limitaciones

- Los puntos iniciales son una semilla automatica; deben revisarse visualmente antes de tratarlos como calibracion humana.
- El editor trabaja sobre overlays ligeros versionados, no sobre video completo.
