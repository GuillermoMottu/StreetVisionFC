# TODO Nivel 2

Nivel 2 queda desbloqueado despues de la validacion Nivel 1 con `10 pass`, `0 warn`, `0 fail` en `experiments/evidence_level1/validation_report.md`.

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

- [ ] Crear timeline de eventos.
- [ ] Crear timeline de posesion.
- [ ] Crear mapas de calor separados por clase/robot.
- [ ] Crear resumen visual ligero por clip.
- [ ] Mantener videos completos fuera de Git.

## Prioridad 4 - Multi-Clip Real

- [ ] Ejecutar tracking/eventos en `video_595`.
- [ ] Ejecutar tracking/eventos en `video_667`.
- [ ] Comparar metricas contra `video_836`.
- [ ] Documentar diferencias por camara, iluminacion y oclusion.
- [ ] Mantener `video_480` como diagnostico de balon.

## Prioridad 5 - Demo Nivel 2

- [ ] Generar demo local con timeline/metricas.
- [ ] Versionar solo capturas ligeras y resumen.
- [ ] Preparar resumen final Nivel 2 para entrega.

## Comando De Gate

```bash
python scripts/check_level2_readiness.py
```
