# Playback Vivo Con Overlays Precomputados

## Resultado

- Estado: `pass`.
- Regla: `live_playback_app_v0.1`.
- Modo: `playback_precomputado`.
- Clip: `video_595`.
- Frames: `120-180`.
- FPS configurado: `59.71505265331406`.
- Video local existe: `true`.
- Tracks normalizados: `206`.
- Eventos normalizados: `83`.
- Highlights normalizados: `82`.
- Errores de validacion: `0`.

## Capas

- Tracks, IDs, balon, trails, eventos, posesion candidata, mini-mapa, highlights y debug.

## Artefactos

- `playback.html`.
- `live_tracks.csv`.
- `live_events.json`.
- `live_highlights.csv`.
- `minimap_frame_sample.json`.
- `config.yaml`.
- `live_playback_manifest.csv`.

## Comando

```bash
.venv/bin/python scripts/run_live_playback_app.py
```
