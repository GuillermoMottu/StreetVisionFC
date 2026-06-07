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
- Mensajes SSE emitibles: `289`.
- Resultados frame a frame SSE: `61`.
- Warnings SSE: `0`.
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
- `endpoint_manifest.json`.
- `stream_messages.jsonl`.
- `stream_latency_metrics.csv`.
- `stream_summary.json`.
- `config.yaml`.
- `live_playback_manifest.csv`.

## Backend Local

- Endpoints fijos: `/manifest.json`, `/stream`, `/stream-summary.json`, `/stream-messages.jsonl`, `/stream-latency.csv`, `/tracks.csv`, `/events.json`, `/highlights.csv`, `/minimap.json`, `/calibration.json`, `/video-metadata.json` y `/video?clip_id=...`.
- Politica de video: solo se sirve el `clip_id` configurado; no se aceptan rutas arbitrarias por query.
- Video pesado: permanece fuera de Git y queda marcado como `is_versioned=false`.
- Si el video no existe en otro equipo, el reproductor muestra aviso local y conserva datos/overlays versionados.

## Canal SSE

- Transporte seleccionado: `SSE` por flujo local unidireccional backend->frontend.
- WebSocket: diferido hasta requerir comandos bidireccionales del motor online.
- Mensajes: `session_status`, `frame_result`, `event_update`, `latency_metrics` y `warning`.
- Reconexion frontend: `EventSource` usa reconexion automatica y cierra el canal al recibir `session_status=complete`.
- Log ligero: `stream_messages.jsonl`.
- Metricas: `stream_latency_metrics.csv`.

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
