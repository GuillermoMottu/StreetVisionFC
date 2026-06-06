# Eventos Avanzados Nivel 3

## Resultado

- Estado: `generado`.
- Regla: `level3_advanced_events_v0.1`.
- Tracks fuente: `experiments/test_026_level3_multiclip/video_667/spatial_model/level3_tracks.csv`.
- Eventos avanzados: `61`.
- Highlights rankeados: `60`.
- Segmentos de posesion candidata: `51`.
- Segmentos de posesion Nivel 2 reutilizables: `0`.
- Segmentos fallback desde interacciones Nivel 3: `51`.
- Segmentos de velocidad de balon: `60`.
- Overlays ligeros generados: `6`.

## Eventos Por Tipo

- `advanced_highlight`: `60`.
- `pass_chain`: `1`.

## Confiabilidad

- `dudoso`: `1`.
- `provisional`: `60`.

## Highlights Clip Principal `video_667`

- Criterio cumplido: al menos tres highlights rankeados para el clip principal.
- Rank `1` frames `175-176` score `74.044923` confianza `0.850961`: velocidad_norm=0.070; presion_o_disputa; posesion_candidata; zona=defensive_third; respaldo_level2.
- Rank `2` frames `173-174` score `73.58386` confianza `0.853891`: velocidad_norm=0.066; presion_o_disputa; posesion_candidata; zona=defensive_third; respaldo_level2.
- Rank `3` frames `176-177` score `73.011213` confianza `0.854867`: velocidad_norm=0.062; presion_o_disputa; posesion_candidata; zona=defensive_third; respaldo_level2.

## Top Highlights Globales

- Rank `1` `video_667` frames `175-176` score `74.044923` confiabilidad `provisional`.
- Rank `2` `video_667` frames `173-174` score `73.58386` confiabilidad `provisional`.
- Rank `3` `video_667` frames `176-177` score `73.011213` confiabilidad `provisional`.
- Rank `4` `video_667` frames `163-164` score `72.905934` confiabilidad `provisional`.
- Rank `5` `video_667` frames `169-170` score `72.697326` confiabilidad `provisional`.
- Rank `6` `video_667` frames `167-168` score `72.637181` confiabilidad `provisional`.

## Cadenas De Pase

- `level2_metrics.json` no trae `possession_timeline` reutilizable en estos clips; se usa fallback desde `interaction_metrics.csv`.
- Como las etiquetas de equipo siguen `neutral/unknown`, las cadenas se marcan como `dudoso_sin_equipo` cuando no hay cambio confiable del mismo equipo.

## Fuentes Nivel 2

- `video_667` eventos Nivel 2 usados como respaldo: `2`.

## Limitaciones

- La narrativa no afirma goles, faltas, tiros oficiales ni pases confirmados sin evidencia suficiente.
- Los highlights son candidatos por reglas: velocidad normalizada, presion/interaccion, zona y confianza.
- Los overlays son mini-mapas de validacion generados desde tracks rectificados, no frames de video pesado.

## Artefactos

- `config.yaml`
- `level3_events.json`
- `level3_highlights.csv`
- `level3_narrative.md`
- `overlay_validation.csv`
- `overlay_highlight_*.png`
- `summary.md`

## Comando

```bash
.venv/bin/python scripts/run_level3_advanced_events.py
```
