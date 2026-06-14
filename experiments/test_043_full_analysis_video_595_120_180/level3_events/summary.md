# Eventos Avanzados Nivel 3

## Resultado

- Estado: `generado`.
- Regla: `level3_advanced_events_v0.1`.
- Tracks fuente: `experiments/test_043_full_analysis_video_595_120_180/team_assignment/level3_tracks_with_teams.csv`.
- Eventos avanzados: `83`.
- Highlights rankeados: `82`.
- Segmentos de posesion candidata: `1`.
- Segmentos de posesion Nivel 2 reutilizables: `0`.
- Segmentos fallback desde interacciones Nivel 3: `1`.
- Segmentos de velocidad de balon: `82`.
- Overlays ligeros generados: `6`.

## Eventos Por Tipo

- `advanced_highlight`: `82`.
- `pass_chain`: `1`.

## Confiabilidad

- `provisional`: `83`.

## Equipos Aproximados

- `team_right`: `83` eventos.

## Highlights Clip Principal `video_595`

- Criterio cumplido: al menos tres highlights rankeados para el clip principal.
- Rank `1` frames `122-123` score `82.868076` confianza `0.893107`: velocidad_norm=0.272; posesion_candidata; zona=defensive_third; respaldo_level2.
- Rank `2` frames `128-129` score `81.414667` confianza `0.828654`: velocidad_norm=0.271; posesion_candidata; zona=defensive_third; respaldo_level2.
- Rank `3` frames `133-135` score `81.0541` confianza `0.812052`: velocidad_norm=0.271; posesion_candidata; zona=defensive_third; respaldo_level2.

## Top Highlights Globales

- Rank `1` `video_595` frames `122-123` score `82.868076` confiabilidad `provisional`.
- Rank `2` `video_595` frames `128-129` score `81.414667` confiabilidad `provisional`.
- Rank `3` `video_595` frames `133-135` score `81.0541` confiabilidad `provisional`.
- Rank `4` `video_595` frames `124-125` score `80.892784` confiabilidad `provisional`.
- Rank `5` `video_595` frames `121-122` score `80.471567` confiabilidad `provisional`.
- Rank `6` `video_595` frames `129-130` score `79.717895` confiabilidad `provisional`.

## Cadenas De Pase

- `level2_metrics.json` no trae `possession_timeline` reutilizable en estos clips; se usa fallback desde `interaction_metrics.csv`.
- Cuando existen etiquetas de equipo aproximadas, las cadenas usan esa informacion; si no, se mantienen como `dudoso_sin_equipo`.

## Fuentes Nivel 2

- `video_595` eventos Nivel 2 usados como respaldo: `2`.

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
