# Rectificacion Espacial Y Mini-Mapa Nivel 3

## Resultado

- Estado: `usable`.
- Regla: `level3_spatial_model_v0.1`.
- Fuente Nivel 2: `experiments/test_017_level2_closure`.
- Clips procesados: `video_595, video_667`.
- Filas exportadas: `512`.
- Filas rectificadas por homografia: `512`.

## Modelo De Cancha

- Coordenadas: `x_norm` y `y_norm` en rango `[0, 1]` sobre la cancha visible aproximada.
- Origen: esquina superior izquierda de la cancha visible calibrada.
- Direccion: `x_norm` crece de izquierda a derecha; `y_norm` crece de arriba hacia abajo.
- Zonas tacticas: `defensive_third`, `middle_third`, `attacking_third` calculadas sobre `y_norm`, conservando la direccion de `zone_axis: y` de Nivel 2.
- Porterias relativas: lineas centradas en `y_norm=0` y `y_norm=1`, con ancho normalizado `0.22`.

## Calibracion

### video_595

- Metodo: `field_bbox_homography_seed`.
- Estado: `usable`.
- Confianza: `0.824417`.
- ID calibracion: `video_595_field_bbox_homography_v0.1`.
- Notas: Median green field bbox from 61 rows; mean confidence 0.749, image coverage 0.725.

### video_667

- Metodo: `field_bbox_homography_seed`.
- Estado: `usable`.
- Confianza: `0.738172`.
- ID calibracion: `video_667_field_bbox_homography_v0.1`.
- Notas: Median green field bbox from 61 rows; mean confidence 0.626, image coverage 0.618.

## Validacion Visual Ligera

- `minimap_base.png` muestra el modelo normalizado de cancha, tercios y porterias relativas.
- `minimap_tracks.png` dibuja trayectorias rectificadas de robots y balon por clip.
- `spatial_validation.csv` resume rangos, filas rectificadas, fallback y calidad por clip.
- `overlay_comparison.csv` referencia `10` overlays originales ligeros de Nivel 2 para comparar frames seleccionados.
- No se abrieron videos completos ni se genero overlay pesado nuevo; `level3_tracks.csv` conserva `x`, `y`, bboxes, frames e IDs para trazabilidad contra los overlays Nivel 2.

## Limitaciones Y Supuestos

- La homografia usa una semilla de caja mediana de `green_soccer_field`; es suficiente para demo tactica aproximada, no para medicion oficial.
- La orientacion real de equipos sigue desconocida, por lo que `defensive_third` y `attacking_third` son convenciones de eje, no lados reales de equipo.
- Si la cancha visible es insuficiente o la caja cae bajo umbral, el script conserva fallback `image_extent_normalization` y marca filas con baja calidad.

## Artefactos

- `config.yaml`
- `field_calibration.json`
- `level3_tracks.csv`
- `minimap_base.png`
- `minimap_tracks.png`
- `overlay_comparison.csv`
- `spatial_validation.csv`
- `summary.md`

## Comando

```bash
.venv/bin/python scripts/run_level3_spatial_model.py
```
