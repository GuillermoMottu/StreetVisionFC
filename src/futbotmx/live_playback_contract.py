from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any, Iterable


RULE_VERSION = "live_playback_data_contract_v0.1"

LIVE_TRACK_REQUIRED_FIELDS = (
    "clip_id",
    "frame",
    "timestamp_sec",
    "track_id",
    "class",
    "x",
    "y",
    "w",
    "h",
    "center_x",
    "center_y",
    "team",
    "confidence",
)

LIVE_TRACK_OPTIONAL_FIELDS = (
    "x_norm",
    "y_norm",
    "zone",
    "calibration_confidence",
)

LIVE_TRACK_FIELDS = LIVE_TRACK_REQUIRED_FIELDS + LIVE_TRACK_OPTIONAL_FIELDS

LIVE_EVENT_REQUIRED_FIELDS = (
    "event_id",
    "label",
    "start_frame",
    "end_frame",
    "start_time_sec",
    "end_time_sec",
    "confidence",
    "status",
)

LIVE_EVENT_OPTIONAL_FIELDS = (
    "clip_id",
    "track_ids",
    "team",
    "zone",
    "reason",
    "source_event_ids",
)

LIVE_HIGHLIGHT_FIELDS = (
    "clip_id",
    "highlight_id",
    "rank",
    "score",
    "label",
    "start_frame",
    "end_frame",
    "start_time_sec",
    "end_time_sec",
    "primary_track_id",
    "secondary_track_ids",
    "zone",
    "confidence",
    "status",
    "reason",
    "source_event_ids",
)

VALID_LIVE_STATUSES = ("candidate", "provisional", "confirmed", "discarded")


def missing_required_fields(row: dict[str, Any], required_fields: Iterable[str]) -> list[str]:
    missing: list[str] = []
    for field in required_fields:
        if field not in row or row[field] is None or row[field] == "":
            missing.append(field)
    return missing


def validate_live_track_row(row: dict[str, Any]) -> list[str]:
    errors = [f"missing:{field}" for field in missing_required_fields(row, LIVE_TRACK_REQUIRED_FIELDS)]
    errors.extend(_validate_int(row, "frame"))
    for field in ("timestamp_sec", "x", "y", "w", "h", "center_x", "center_y"):
        errors.extend(_validate_float(row, field))
    errors.extend(_validate_float(row, "confidence", minimum=0.0, maximum=1.0))
    for field in ("x_norm", "y_norm", "calibration_confidence"):
        if row.get(field, "") != "":
            errors.extend(_validate_float(row, field))
    return errors


def validate_live_event(event: dict[str, Any]) -> list[str]:
    errors = [f"missing:{field}" for field in missing_required_fields(event, LIVE_EVENT_REQUIRED_FIELDS)]
    errors.extend(_validate_int(event, "start_frame"))
    errors.extend(_validate_int(event, "end_frame"))
    errors.extend(_validate_float(event, "start_time_sec"))
    errors.extend(_validate_float(event, "end_time_sec"))
    errors.extend(_validate_float(event, "confidence", minimum=0.0, maximum=1.0))
    if event.get("status") not in VALID_LIVE_STATUSES:
        errors.append(f"invalid_status:{event.get('status')}")
    if "track_ids" in event and not isinstance(event["track_ids"], list):
        errors.append("invalid_track_ids:not_list")
    if _as_float(event.get("end_time_sec")) < _as_float(event.get("start_time_sec")):
        errors.append("invalid_time_range")
    if _as_int(event.get("end_frame")) < _as_int(event.get("start_frame")):
        errors.append("invalid_frame_range")
    return errors


def validate_live_highlight_row(row: dict[str, Any]) -> list[str]:
    errors = [f"missing:{field}" for field in missing_required_fields(row, LIVE_HIGHLIGHT_FIELDS)]
    errors.extend(_validate_int(row, "rank"))
    errors.extend(_validate_float(row, "score"))
    errors.extend(_validate_int(row, "start_frame"))
    errors.extend(_validate_int(row, "end_frame"))
    errors.extend(_validate_float(row, "start_time_sec"))
    errors.extend(_validate_float(row, "end_time_sec"))
    errors.extend(_validate_float(row, "confidence", minimum=0.0, maximum=1.0))
    if row.get("status") not in VALID_LIVE_STATUSES:
        errors.append(f"invalid_status:{row.get('status')}")
    return errors


def validate_minimap_payload(payload: dict[str, Any]) -> list[str]:
    errors = [f"missing:{field}" for field in missing_required_fields(payload, ("clip_id", "frame", "timestamp_sec", "points"))]
    errors.extend(_validate_int(payload, "frame"))
    errors.extend(_validate_float(payload, "timestamp_sec"))
    if "calibration_confidence" in payload and payload.get("calibration_confidence", "") != "":
        errors.extend(_validate_float(payload, "calibration_confidence", minimum=0.0, maximum=1.0))
    points = payload.get("points", [])
    if not isinstance(points, list):
        return errors + ["invalid_points:not_list"]
    for index, point in enumerate(points):
        if not isinstance(point, dict):
            errors.append(f"invalid_point:{index}:not_object")
            continue
        for field in ("track_id", "class", "x_norm", "y_norm"):
            if point.get(field, "") == "":
                errors.append(f"missing_point:{index}:{field}")
        for field in ("x_norm", "y_norm"):
            errors.extend(f"point:{index}:{error}" for error in _validate_float(point, field, minimum=0.0, maximum=1.0))
    return errors


def normalize_track_row(row: dict[str, Any], clip_id: str = "", fps: float | None = None) -> dict[str, Any]:
    frame = _as_int(row.get("frame"))
    timestamp = _first_value(row, ("timestamp_sec", "time_sec"))
    if timestamp == "" and fps:
        timestamp = frame / fps

    if row.get("bbox_x1", "") != "" and row.get("bbox_x2", "") != "":
        x = _as_float(row.get("bbox_x1"))
        y = _as_float(row.get("bbox_y1"))
        w = _as_float(row.get("bbox_x2")) - x
        h = _as_float(row.get("bbox_y2")) - y
        center_x = _first_value(row, ("center_x", "x"))
        center_y = _first_value(row, ("center_y", "y"))
    else:
        x = _first_value(row, ("x", "bbox_x1"))
        y = _first_value(row, ("y", "bbox_y1"))
        w = _first_value(row, ("w", "width"))
        h = _first_value(row, ("h", "height"))
        center_x = _first_value(row, ("center_x",))
        center_y = _first_value(row, ("center_y",))
        if center_x == "" and x != "" and w != "":
            center_x = _as_float(x) + _as_float(w) / 2.0
        if center_y == "" and y != "" and h != "":
            center_y = _as_float(y) + _as_float(h) / 2.0

    return {
        "clip_id": _first_value(row, ("clip_id",)) or clip_id,
        "frame": frame,
        "timestamp_sec": _format_number(timestamp),
        "track_id": _first_value(row, ("track_id", "source_track_id")),
        "class": _first_value(row, ("class", "class_name", "label")),
        "x": _format_number(x),
        "y": _format_number(y),
        "w": _format_number(w),
        "h": _format_number(h),
        "center_x": _format_number(center_x),
        "center_y": _format_number(center_y),
        "team": _first_value(row, ("team",)) or "unknown",
        "confidence": _format_number(_first_value(row, ("confidence", "score"))),
        "x_norm": _format_number(_first_value(row, ("x_norm",))),
        "y_norm": _format_number(_first_value(row, ("y_norm",))),
        "zone": _first_value(row, ("zone",)),
        "calibration_confidence": _format_number(_first_value(row, ("calibration_confidence",))),
    }


def normalize_track_rows(rows: Iterable[dict[str, Any]], clip_id: str = "", fps: float | None = None) -> list[dict[str, Any]]:
    return [normalize_track_row(row, clip_id=clip_id, fps=fps) for row in rows]


def normalize_event(event: dict[str, Any]) -> dict[str, Any]:
    primary_track = _first_value(event, ("primary_track_id", "primary_object_id"))
    secondary_tracks = _as_list(_first_value(event, ("secondary_track_ids", "secondary_object_ids")))
    ball_id = _first_value(event, ("ball_id",))
    track_ids = _unique_nonempty([primary_track, *secondary_tracks, ball_id])
    source_event_ids = _as_list(_first_value(event, ("source_event_ids",)))

    return {
        "event_id": _first_value(event, ("event_id", "highlight_id")),
        "label": _first_value(event, ("label", "event_type", "event_subtype")),
        "start_frame": _first_value(event, ("start_frame", "frame_start")),
        "end_frame": _first_value(event, ("end_frame", "frame_end")),
        "start_time_sec": _format_number(_first_value(event, ("start_time_sec", "time_start_sec"))),
        "end_time_sec": _format_number(_first_value(event, ("end_time_sec", "time_end_sec"))),
        "confidence": _format_number(_first_value(event, ("confidence",))),
        "status": normalize_status(_first_value(event, ("status", "reliability"))),
        "clip_id": _first_value(event, ("clip_id",)),
        "track_ids": track_ids,
        "team": _first_value(event, ("team",)) or "unknown",
        "zone": _first_value(event, ("zone",)),
        "reason": _reason_from_event(event),
        "source_event_ids": source_event_ids,
    }


def normalize_events(events: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    return [normalize_event(event) for event in events]


def normalize_highlight_row(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "clip_id": _first_value(row, ("clip_id",)),
        "highlight_id": _first_value(row, ("highlight_id", "event_id")),
        "rank": _first_value(row, ("rank",)),
        "score": _format_number(_first_value(row, ("score", "highlight_score"))),
        "label": _first_value(row, ("label", "event_type", "event_subtype")),
        "start_frame": _first_value(row, ("start_frame", "frame_start")),
        "end_frame": _first_value(row, ("end_frame", "frame_end")),
        "start_time_sec": _format_number(_first_value(row, ("start_time_sec", "time_start_sec"))),
        "end_time_sec": _format_number(_first_value(row, ("end_time_sec", "time_end_sec"))),
        "primary_track_id": _first_value(row, ("primary_track_id", "primary_object_id")),
        "secondary_track_ids": _pipe_join(_as_list(_first_value(row, ("secondary_track_ids", "secondary_object_ids", "ball_id")))),
        "zone": _first_value(row, ("zone",)),
        "confidence": _format_number(_first_value(row, ("confidence",))),
        "status": normalize_status(_first_value(row, ("status", "reliability"))),
        "reason": _first_value(row, ("reason", "narrative")),
        "source_event_ids": _pipe_join(_as_list(_first_value(row, ("source_event_ids",)))),
    }


def normalize_highlight_rows(rows: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    return [normalize_highlight_row(row) for row in rows]


def build_minimap_payload(
    track_rows: Iterable[dict[str, Any]],
    clip_id: str,
    frame: int,
    timestamp_sec: float,
    calibration_status: str = "unknown",
) -> dict[str, Any]:
    points: list[dict[str, Any]] = []
    calibration_values: list[float] = []
    for row in track_rows:
        if _as_int(row.get("frame")) != frame:
            continue
        if row.get("x_norm", "") == "" or row.get("y_norm", "") == "":
            continue
        if row.get("calibration_confidence", "") != "":
            calibration_values.append(_as_float(row["calibration_confidence"]))
        points.append(
            {
                "track_id": row.get("track_id", ""),
                "class": row.get("class", ""),
                "team": row.get("team", "unknown"),
                "x_norm": _format_number(row.get("x_norm")),
                "y_norm": _format_number(row.get("y_norm")),
                "confidence": _format_number(row.get("confidence", "")),
            }
        )
    calibration_confidence = min(calibration_values) if calibration_values else ""
    return {
        "clip_id": clip_id,
        "frame": frame,
        "timestamp_sec": _format_number(timestamp_sec),
        "calibration_status": calibration_status,
        "calibration_confidence": _format_number(calibration_confidence),
        "points": points,
    }


def normalize_status(value: Any) -> str:
    text = str(value or "").strip().lower()
    mapping = {
        "candidate": "candidate",
        "candidato": "candidate",
        "dudoso": "candidate",
        "unknown": "candidate",
        "": "candidate",
        "provisional": "provisional",
        "confirmed": "confirmed",
        "confiable": "confirmed",
        "validado": "confirmed",
        "discarded": "discarded",
        "descartado": "discarded",
        "fallo": "discarded",
    }
    return mapping.get(text, "candidate")


def read_csv_rows(path: str | Path) -> list[dict[str, str]]:
    with Path(path).open("r", newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def read_json_events(path: str | Path) -> list[dict[str, Any]]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if isinstance(payload, dict):
        events = payload.get("events", [])
    else:
        events = payload
    if not isinstance(events, list):
        raise ValueError("live events payload must be a list or contain an events list")
    return events


def write_csv_rows(path: str | Path, rows: Iterable[dict[str, Any]], fieldnames: Iterable[str]) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(fieldnames), lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in writer.fieldnames or []})


def write_live_tracks_csv(path: str | Path, rows: Iterable[dict[str, Any]]) -> None:
    normalized_rows = list(rows)
    _raise_if_invalid("live_tracks.csv", normalized_rows, validate_live_track_row)
    write_csv_rows(path, normalized_rows, LIVE_TRACK_FIELDS)


def write_live_highlights_csv(path: str | Path, rows: Iterable[dict[str, Any]]) -> None:
    normalized_rows = list(rows)
    _raise_if_invalid("live_highlights.csv", normalized_rows, validate_live_highlight_row)
    write_csv_rows(path, normalized_rows, LIVE_HIGHLIGHT_FIELDS)


def write_live_events_json(path: str | Path, events: Iterable[dict[str, Any]]) -> None:
    normalized_events = list(events)
    _raise_if_invalid("live_events.json", normalized_events, validate_live_event)
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(normalized_events, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")


def _raise_if_invalid(label: str, rows: list[dict[str, Any]], validator: Any) -> None:
    for index, row in enumerate(rows):
        errors = validator(row)
        if errors:
            raise ValueError(f"{label} row {index} invalid: {', '.join(errors)}")


def _validate_int(row: dict[str, Any], field: str) -> list[str]:
    if field not in row or row[field] == "":
        return []
    try:
        int(float(row[field]))
    except (TypeError, ValueError):
        return [f"invalid_int:{field}"]
    return []


def _validate_float(row: dict[str, Any], field: str, minimum: float | None = None, maximum: float | None = None) -> list[str]:
    if field not in row or row[field] == "":
        return []
    try:
        value = float(row[field])
    except (TypeError, ValueError):
        return [f"invalid_float:{field}"]
    errors: list[str] = []
    if minimum is not None and value < minimum:
        errors.append(f"below_min:{field}")
    if maximum is not None and value > maximum:
        errors.append(f"above_max:{field}")
    return errors


def _first_value(row: dict[str, Any], keys: Iterable[str]) -> Any:
    for key in keys:
        if key in row and row[key] not in (None, ""):
            return row[key]
    return ""


def _as_float(value: Any) -> float:
    if value in (None, ""):
        return 0.0
    return float(value)


def _as_int(value: Any) -> int:
    if value in (None, ""):
        return 0
    return int(float(value))


def _as_list(value: Any) -> list[str]:
    if value in (None, ""):
        return []
    if isinstance(value, list):
        return [str(item) for item in value if str(item)]
    if isinstance(value, tuple):
        return [str(item) for item in value if str(item)]
    text = str(value)
    separator = "|" if "|" in text else ";"
    return [part.strip() for part in text.split(separator) if part.strip()]


def _format_number(value: Any) -> str:
    if value in (None, ""):
        return ""
    number = float(value)
    return f"{number:.6f}".rstrip("0").rstrip(".")


def _unique_nonempty(values: Iterable[Any]) -> list[str]:
    seen: set[str] = set()
    output: list[str] = []
    for value in values:
        text = str(value or "").strip()
        if text and text not in seen:
            seen.add(text)
            output.append(text)
    return output


def _pipe_join(values: Iterable[str]) -> str:
    return "|".join(_unique_nonempty(values))


def _reason_from_event(event: dict[str, Any]) -> str:
    reason = _first_value(event, ("reason", "narrative"))
    if reason:
        return str(reason)
    spatial_context = event.get("spatial_context")
    if isinstance(spatial_context, dict):
        context_reason = spatial_context.get("reason")
        if isinstance(context_reason, list):
            return "; ".join(str(item) for item in context_reason)
        if context_reason:
            return str(context_reason)
    return ""
