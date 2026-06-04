# TODO Nivel 2

Nivel 2 fue implementado despues de la validacion Nivel 1 con `10 pass`, `0 warn`, `0 fail` en `experiments/evidence_level1/validation_report.md`. El cierre tecnico se valida con `scripts/check_level2_closure.py`.

## Estado De Desbloqueo

- [x] Nivel 1 ejecutado exitosamente en laptop MSI.
- [x] Resultados ligeros versionados.
- [x] Commit hash y pruebas registradas en `FutBotMX_documentacion_markdown/TESTING_LOG.md`.
- [x] Configuraciones guardadas en `experiments/test_*/config.yaml`.
- [x] Validacion humana/visual documentada con overlays y demo local.
- [x] Archivos pesados fuera de Git.
- [x] Gate reproducible generado en `experiments/test_011_level2_unlock/`.

## Prioridad 1 - Metricas Deportivas Intermedias

- [x] Calcular posesion temporal por robot/equipo.
- [x] Calcular distancia recorrida por robot y balon.
- [x] Calcular velocidad aproximada por track.
- [x] Exportar `level2_metrics.csv` y `level2_metrics.json`.
- [x] Documentar supuestos y limitaciones por perspectiva de camara.

Evidencia: `experiments/test_012_level2_metrics/video_836_real_metrics_120_180/`.

## Prioridad 2 - Eventos Intermedios

- [x] Detectar recuperacion de balon.
- [x] Detectar intercepcion aproximada.
- [x] Detectar jugada destacada basada en zona, velocidad o cambio de posesion.
- [x] Marcar confiabilidad de cada evento: `confiable`, `provisional`, `descartado`.
- [x] Validar eventos con overlays representativos.

Evidencia: `experiments/test_013_level2_events/video_836_real_events_120_180/`.

## Prioridad 3 - Visualizaciones Nivel 2

- [x] Crear timeline de eventos.
- [x] Crear timeline de posesion.
- [x] Crear mapas de calor separados por clase/robot.
- [x] Crear resumen visual ligero por clip.
- [x] Mantener videos completos fuera de Git.

Evidencia: `experiments/test_014_level2_visualizations/video_836_real_visuals_120_180/`.

## Prioridad 4 - Multi-Clip Real

- [x] Ejecutar tracking/eventos en `video_595`.
- [x] Ejecutar tracking/eventos en `video_667`.
- [x] Comparar metricas contra `video_836`.
- [x] Documentar diferencias por camara, iluminacion y oclusion.
- [x] Mantener `video_480` como diagnostico de balon.

Evidencia: `experiments/test_015_level2_multiclip/`.

## Prioridad 5 - Demo Nivel 2

- [x] Generar demo local con timeline/metricas.
- [x] Versionar solo capturas ligeras y resumen.
- [x] Preparar resumen final Nivel 2 para entrega.

Evidencia: `experiments/test_016_level2_demo/`.

## Prioridad 6 - Cierre Tecnico Nivel 2

- [x] Resolver discrepancias de documentacion vivas.
- [x] Centralizar lectura de tracks.
- [x] Extraer ByteTrack reutilizable.
- [x] Evitar velocidades de balon cruzando `track_id`.
- [x] Configurar eje de zonas Nivel 2 con `zone_axis`.
- [x] Crear gate de cierre Nivel 2.
- [ ] Generar evidencia densa final en `experiments/test_017_level2_closure/`.

## Comandos De Gate

```bash
env MPLCONFIGDIR=/tmp/matplotlib .venv/bin/python -m unittest discover -s tests -q
.venv/bin/python scripts/check_level2_readiness.py
.venv/bin/python scripts/check_level2_closure.py
```
