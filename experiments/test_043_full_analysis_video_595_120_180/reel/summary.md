# Reel Final Y Demo De Presentacion Nivel 3

## Resultado

- Estado: `generado`.
- Regla: `level3_reel_v0.1`.
- Segmentos seleccionados: `4`.
- Clips incluidos: `video_595`.
- Duracion sugerida: `12.0` segundos.
- Score top: `82.9`.
- Confianza minima seleccionada: `0.81`.
- Highlights con revision humana: `0`.
- Highlights descartados por revision: `0`.
- Manifest rows: `21`.
- MP4 final: local y no versionado.

## Segmentos

- `reel_segment_01` rank `1` `video_595` frames `122-123` score `82.9` conf `0.89`.
- `reel_segment_02` rank `2` `video_595` frames `128-129` score `81.4` conf `0.83`.
- `reel_segment_03` rank `3` `video_595` frames `133-135` score `81.1` conf `0.81`.
- `reel_segment_04` rank `4` `video_595` frames `124-125` score `80.9` conf `0.84`.

## Narrativa

- Cada thumbnail combina overlay de evento, mini-mapa y texto breve.
- Los overlays muestran IDs/trails cuando existen en la evidencia Nivel 3.
- Si existe `human_review.csv`, los highlights descartados no entran al reel.
- El lenguaje queda como highlight/proximidad/posesion candidata; no afirma goles ni decisiones oficiales.

## Render Local

```bash
cd experiments/test_043_full_analysis_video_595_120_180/reel
bash render_reel_local.sh
```

- Salida esperada fuera de Git: `local_outputs/full_analysis/video_595_120_180_reel.mp4`.
- `*.mp4` esta ignorado por `.gitignore` y no se genera durante esta actividad.

## Artefactos

- `config.yaml`
- `summary.md`
- `reel_segments.csv`
- `reel_manifest.csv`
- `reel_narrative.md`
- `reel_render_plan.md`
- `render_reel_local.sh`
- `reel_ffmpeg_inputs.txt`
- `reel_demo.html`
- `reel_contact_sheet.png`
- `reel_thumb_rank_*.png`

## Limitaciones

- El paquete versiona capturas estaticas ligeras; el MP4 se renderiza localmente si se necesita.
- La seleccion usa highlights rankeados y evidencia visual disponible, no revision arbitral.
- Para un reel con video real, usar `reel_segments.csv` sobre videos locales fuera de Git.

## Comando De Generacion

```bash
.venv/bin/python scripts/run_level3_reel.py
```
