# Contrato De Datos Playback Vivo

Este documento cierra la Actividad 22 de `docs/TODO_LIVE_PLAYBACK.md`. Define los formatos ligeros que usaran frontend y backend para sincronizar overlays con un video local por frame o timestamp.

La implementacion ejecutable del contrato vive en `src/futbotmx/live_playback_contract.py`. Los fixtures minimos estan en `tests/fixtures/live_playback/`.

## Principios

- El reloj principal es el video.
- Todo dato visible debe poder resolverse por `frame` o `timestamp_sec`.
- El frontend no debe adivinar columnas internas de Nivel 1, Nivel 2 o Nivel 3.
- Los eventos durante playback se muestran como candidatos, provisionales, confirmados o descartados.
- El contrato acepta artefactos existentes y los normaliza hacia nombres estables para UI.
- Los videos completos siguen fuera de Git; este contrato solo cubre CSV, JSON y payloads ligeros.

## Version

`live_playback_data_contract_v0.1`

## `live_tracks.csv`

Formato CSV para dibujar tracks por frame.

### Campos obligatorios

| Campo | Tipo | Descripcion |
|---|---|---|
| `clip_id` | string | Identificador del clip. |
| `frame` | int | Frame al que pertenece el track. |
| `timestamp_sec` | float | Tiempo aproximado en segundos. |
| `track_id` | string | ID persistente del objeto. |
| `class` | string | Clase visible para UI, por ejemplo `ball` o `small_robot`. |
| `x` | float | Coordenada X superior izquierda del bbox en pixeles. |
| `y` | float | Coordenada Y superior izquierda del bbox en pixeles. |
| `w` | float | Ancho del bbox en pixeles. |
| `h` | float | Alto del bbox en pixeles. |
| `center_x` | float | Centro X del objeto en pixeles. |
| `center_y` | float | Centro Y del objeto en pixeles. |
| `team` | string | Equipo aproximado o `neutral`/`unknown`. |
| `confidence` | float | Confianza entre `0` y `1`. |

### Campos opcionales

| Campo | Tipo | Descripcion |
|---|---|---|
| `x_norm` | float | Coordenada X rectificada en cancha normalizada. |
| `y_norm` | float | Coordenada Y rectificada en cancha normalizada. |
| `zone` | string | Zona aproximada de cancha. |
| `calibration_confidence` | float | Confianza de calibracion entre `0` y `1`. |

### Conversion desde formatos existentes

| Origen | Conversion |
|---|---|
| `tracks.csv` o `tracks_level2.csv` | `class_name -> class`; `bbox_x1/bbox_y1/bbox_x2/bbox_y2 -> x/y/w/h`; `x/y -> center_x/center_y`; `timestamp_sec` se calcula con FPS si no existe. |
| `level3_tracks.csv` | `time_sec -> timestamp_sec`; `class_name -> class`; conserva `x_norm`, `y_norm`, `zone` y `calibration_confidence`. |

## `live_events.json`

Formato JSON para eventos activos o historicos durante playback. Puede ser una lista directa o un objeto con llave `events`.

### Campos obligatorios

| Campo | Tipo | Descripcion |
|---|---|---|
| `event_id` | string | ID estable del evento. |
| `label` | string | Etiqueta corta visible para UI. |
| `start_frame` | int | Frame inicial. |
| `end_frame` | int | Frame final. |
| `start_time_sec` | float | Tiempo inicial en segundos. |
| `end_time_sec` | float | Tiempo final en segundos. |
| `confidence` | float | Confianza entre `0` y `1`. |
| `status` | enum | `candidate`, `provisional`, `confirmed` o `discarded`. |

### Campos opcionales recomendados

| Campo | Tipo | Descripcion |
|---|---|---|
| `clip_id` | string | Clip asociado. |
| `track_ids` | list[string] | Tracks participantes, incluyendo balon si aplica. |
| `team` | string | Equipo aproximado o `unknown`. |
| `zone` | string | Zona aproximada. |
| `reason` | string | Motivo resumido del evento. |
| `source_event_ids` | list[string] | IDs de eventos batch que respaldan el evento vivo. |

### Conversion desde formatos existentes

| Origen | Conversion |
|---|---|
| `events.json` | `event_type -> label`; frames y tiempos se copian si existen. |
| `level2_events.json` | Se conserva el evento como candidato o provisional segun confianza disponible. |
| `level3_events.json` | `frame_start/frame_end -> start_frame/end_frame`; `time_start_sec/time_end_sec -> start_time_sec/end_time_sec`; `reliability -> status`; objetos primarios/secundarios se agrupan en `track_ids`. |

## `live_highlights.csv`

Formato CSV para ranking de jugadas destacadas sincronizables con video.

| Campo | Tipo | Descripcion |
|---|---|---|
| `clip_id` | string | Clip asociado. |
| `highlight_id` | string | ID estable del highlight. |
| `rank` | int | Posicion en ranking. |
| `score` | float | Score de highlight. |
| `label` | string | Etiqueta visible para UI. |
| `start_frame` | int | Frame inicial. |
| `end_frame` | int | Frame final. |
| `start_time_sec` | float | Tiempo inicial en segundos. |
| `end_time_sec` | float | Tiempo final en segundos. |
| `primary_track_id` | string | Track principal si existe. |
| `secondary_track_ids` | string | IDs secundarios separados por `|`. |
| `zone` | string | Zona aproximada. |
| `confidence` | float | Confianza entre `0` y `1`. |
| `status` | enum | `candidate`, `provisional`, `confirmed` o `discarded`. |
| `reason` | string | Motivo resumido. |
| `source_event_ids` | string | IDs fuente separados por `|`. |

### Conversion desde `level3_highlights.csv`

- `event_type -> label`.
- `frame_start/frame_end -> start_frame/end_frame`.
- `time_start_sec/time_end_sec -> start_time_sec/end_time_sec`.
- `reliability -> status`.
- `secondary_track_ids` se conserva como lista serializada por `|`.

## Payload De Mini-Mapa

El mini-mapa se envia como JSON por frame. Puede generarse desde `live_tracks.csv` si existen `x_norm` y `y_norm`.

```json
{
  "clip_id": "video_595",
  "frame": 120,
  "timestamp_sec": 2.0,
  "calibration_status": "rectified",
  "calibration_confidence": 0.82,
  "points": [
    {
      "track_id": "ball_bt_01",
      "class": "ball",
      "team": "neutral",
      "x_norm": 0.746,
      "y_norm": 0.191,
      "confidence": 0.82
    }
  ]
}
```

Reglas:

- `points` solo debe incluir objetos con coordenadas rectificadas disponibles.
- Si no hay calibracion confiable, el frontend puede ocultar mini-mapa o marcarlo como fallback.
- `calibration_confidence` debe estar entre `0` y `1` cuando exista.

## Estados

| Estado | Uso |
|---|---|
| `candidate` | Evento o highlight detectado con evidencia inicial insuficiente. |
| `provisional` | Evidencia util para demo, pero sin revision humana final. |
| `confirmed` | Evidencia revisada o suficientemente estable para mostrar con mayor confianza. |
| `discarded` | Evento descartado por reglas, revision o contradiccion posterior. |

## Validacion

Los validadores unitarios cubren:

- Presencia de campos obligatorios.
- Tipos numericos para frames, tiempos, coordenadas y confianza.
- Rangos de confianza entre `0` y `1`.
- Estados permitidos.
- Payload de mini-mapa con puntos rectificados.
- Conversion desde formatos Nivel 2 y Nivel 3.

Comando recomendado:

```bash
.venv/bin/python -m unittest tests.test_live_playback_contract
```

## Artefactos De Actividad 22

- `docs/LIVE_PLAYBACK_DATA_CONTRACT.md`.
- `src/futbotmx/live_playback_contract.py`.
- `tests/test_live_playback_contract.py`.
- `tests/fixtures/live_playback/live_tracks.csv`.
- `tests/fixtures/live_playback/live_events.json`.
- `tests/fixtures/live_playback/live_highlights.csv`.
- `tests/fixtures/live_playback/minimap_frame_120.json`.
