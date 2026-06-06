# Validacion Multi-Clip Nivel 3

## Resultado

- Estado: `generado`.
- Regla: `level3_multiclip_v0.1`.
- Fuente Nivel 2: `experiments/test_017_level2_closure`.
- Clips procesados: `video_595, video_667`.
- Clips con salida Nivel 3 documentada: `2`.
- Revision visual ligera: `{'provisional': 2}`.

## Comparacion

| clip | highlights | score top | interacciones | aristas | homografia | revision | limitaciones |
| --- | ---: | ---: | ---: | ---: | --- | --- | --- |
| `video_595` | `82` | `82.868076` | `57.0` | `1.0` | `usable (0.824417)` | `provisional` | `revision_visual_provisional|equipos_neutrales` |
| `video_667` | `60` | `74.044923` | `428.0` | `8.0` | `usable (0.738172)` | `provisional` | `homografia_provisional|revision_visual_provisional|equipos_neutrales` |

## Hallazgos

- `video_595` conserva el rol de clip principal: produce highlights con score mas alto y trayectoria mas simple, pero con menos diversidad de robots e interacciones.
- `video_667` valida que las reglas corren en un segundo clip sin reescritura: aparecen mas interacciones y aristas, aunque la homografia queda mas provisional.
- Las diferencias de camara, iluminacion y oclusion se reportan de forma indirecta mediante confianza de calibracion, estabilidad de tracks, conteo de interacciones y revision de overlays ligeros.
- Los falsos positivos mas probables son presiones/disputas sobrerrepresentadas en frames con robots cercanos y posesion candidata cuando los equipos siguen `neutral`.
- La homografia aproximada es suficiente para demo tactica comparativa, no para mediciones oficiales ni arbitraje.

## Revision Humana Ligera

- Cada subcarpeta incluye `human_review.csv` con estado `confiable`, `provisional` o `descartado` por highlight top.
- La clasificacion usa overlays versionables, confianza y respaldo Nivel 2; no abre videos completos ni genera MP4.
- Los clips con `revision_visual_provisional` quedan aceptados como evidencia de demo, pero no como verdad de cancha.

## Artefactos

- `config.yaml`
- `level3_multiclip_comparison.csv`
- `level3_multiclip_manifest.csv`
- `summary.md`
- `video_595/` con config, resumen y evidencia ligera.
- `video_667/` con config, resumen y evidencia ligera.

## Comando

```bash
.venv/bin/python scripts/run_level3_multiclip.py
```
