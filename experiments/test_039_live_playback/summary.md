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
- Frames procesados por loop online: `61`.
- Frames saltados por backpressure: `0`.
- Latencia promedio loop hasta overlay: `1.233279` ms.
- Modo de inferencia seleccionado: `precomputed`.
- Modo recomendado para demo: `precomputed`.
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
- `frame_loop_summary.json`.
- `frame_loop_metrics.csv`.
- `inference_modes.json`.
- `config.yaml`.
- `live_playback_manifest.csv`.

## Backend Local

- Endpoints fijos: `/manifest.json`, `/stream`, `/stream-summary.json`, `/stream-messages.jsonl`, `/stream-latency.csv`, `/frame-loop-summary.json`, `/frame-loop-metrics.csv`, `/inference-modes.json`, `/tracks.csv`, `/events.json`, `/highlights.csv`, `/minimap.json`, `/calibration.json`, `/video-metadata.json` y `/video?clip_id=...`.
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

## Motor Online De Frames

- Modo: `precomputed_online_loop`.
- Pipeline: leer frame solicitado, recuperar detecciones precomputadas, actualizar snapshot incremental, actualizar eventos activos y emitir overlay parcial.
- Controles soportados: `pause`, `resume`, `seek`, `stop` y salto de frames por backpressure.
- Inferencia online real: diferida; el hook existe y usa fallback precomputado determinista para esta actividad.
- Metricas por etapa: lectura de frame, deteccion, tracking, eventos, overlay y total hasta overlay.
- Evidencia: `frame_loop_summary.json` y `frame_loop_metrics.csv`.

## Modos De Inferencia

- Modo seleccionado por configuracion: `precomputed`, `sam3_sampling` o `lightweight_detector`.
- Recomendado para demo fluida: `precomputed`, porque carga detecciones SAM 3/Level 3 ya generadas y sincroniza por frame o frame cercano.
- `sam3_sampling`: ejecuta SAM 3 solo cada N frames cuando exista GPU MSI autorizada; entre muestras reusa detecciones y registra latencia/VRAM cuando este disponible.
- `lightweight_detector`: hook experimental mas rapido para robots y balon; mantiene compatibilidad con tracker incremental pero documenta degradacion frente a SAM 3 offline.
- Evidencia: `inference_modes.json` y endpoint `/inference-modes.json`.

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
