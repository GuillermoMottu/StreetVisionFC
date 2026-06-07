# Playback Vivo Con Overlays Precomputados

## Resultado

- Estado: `pass`.
- Regla: `live_playback_app_v0.1`.
- Modo: `playback_precomputado`.
- Clip: `video_595`.
- Frames: `120-180`.
- FPS configurado: `59.71505265331406`.
- Duracion configurada: `1.021518` segundos.
- Frames configurados aproximados: `61`.
- Frames con datos disponibles: `61`.
- Mayor salto entre frames disponibles: `1`.
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
- `video_metadata.json`.
- `config.yaml`.
- `live_playback_manifest.csv`.

## Sincronizacion

- Conversion: `frame = round(currentTime * fps)`.
- Resolucion: frame exacto si existe; si no existe, frame anterior disponible por stride.
- Interpolacion: deshabilitada por defecto hasta que un modo explicito la active.
- Seek: el frontend recalcula el overlay y limpia trails si detecta salto temporal grande.
- Duracion real del elemento `<video>` se lee en navegador; el JSON guarda duracion configurada del rango de frames.

## Comando

```bash
.venv/bin/python scripts/run_live_playback_app.py
```
