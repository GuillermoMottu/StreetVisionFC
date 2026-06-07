from __future__ import annotations

import csv
import html
import io
import json
import mimetypes
import sys
from dataclasses import asdict, dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, unquote, urlparse

from futbotmx.config import load_config, write_config_snapshot
from futbotmx.live_playback_contract import (
    LIVE_HIGHLIGHT_FIELDS,
    LIVE_TRACK_FIELDS,
    build_minimap_payload,
    normalize_event,
    normalize_highlight_row,
    normalize_track_row,
    read_csv_rows,
    read_json_events,
    validate_live_event,
    validate_live_highlight_row,
    validate_live_track_row,
    validate_minimap_payload,
    write_live_events_json,
    write_live_highlights_csv,
    write_live_tracks_csv,
)


RULE_VERSION = "live_playback_app_v0.1"
DEFAULT_EXPERIMENT_DIR = Path("experiments/test_039_live_playback")
DEFAULT_TRACKS_CANDIDATES = (
    Path("experiments/test_034_full_analysis/level3_spatial/level3_tracks.csv"),
    Path("experiments/test_020_level3_spatial_model/level3_tracks.csv"),
)
DEFAULT_EVENTS_CANDIDATES = (
    Path("experiments/test_034_full_analysis/level3_events/level3_events.json"),
    Path("experiments/test_022_level3_advanced_events/level3_events.json"),
)
DEFAULT_HIGHLIGHTS_CANDIDATES = (
    Path("experiments/test_034_full_analysis/level3_events/level3_highlights.csv"),
    Path("experiments/test_022_level3_advanced_events/level3_highlights.csv"),
)
MANIFEST_FIELDS = ["asset_id", "asset_type", "path", "source_artifact", "is_versioned", "role", "notes"]
DEFAULT_TRAIL_LENGTH = 16
STREAM_MESSAGE_TYPES = ("session_status", "frame_result", "event_update", "latency_metrics", "warning")
STREAM_LATENCY_FIELDS = [
    "sequence",
    "message_id",
    "clip_id",
    "frame",
    "timestamp_sec",
    "resolved_frame",
    "resolution_status",
    "track_count",
    "event_count",
    "highlight_count",
    "lookup_latency_ms",
    "emit_latency_ms",
    "queue_depth",
    "backpressure",
    "source",
]


@dataclass(frozen=True)
class PlaybackClip:
    clip_id: str
    role: str
    video_path: str
    start_frame: int
    end_frame: int
    fps: float
    width: int
    height: int


@dataclass(frozen=True)
class LivePlaybackConfig:
    clip_id: str
    video_path: str
    fps: float
    width: int
    height: int
    start_frame: int
    end_frame: int
    tracks_csv: str
    events_json: str
    highlights_csv: str
    output_dir: str
    trail_length: int = DEFAULT_TRAIL_LENGTH


@dataclass(frozen=True)
class FrameResolution:
    target_frame: int
    resolved_frame: int | None
    status: str
    frame_gap: int | None


@dataclass(frozen=True)
class VideoMetadata:
    clip_id: str
    fps_nominal: float
    width: int
    height: int
    frame_start: int
    frame_end: int
    configured_frame_count: int
    configured_duration_sec: float
    video_path: str
    video_exists: bool
    video_size_bytes: int
    metadata_source: str
    notes: str


def playback_clips_from_config(config: dict[str, Any]) -> list[PlaybackClip]:
    closure = config.get("level2_closure", {})
    raw_clips = closure.get("clips", []) if isinstance(closure, dict) else []
    clips: list[PlaybackClip] = []
    for raw in raw_clips:
        if not isinstance(raw, dict):
            continue
        clips.append(
            PlaybackClip(
                clip_id=str(raw.get("clip_id", "clip")),
                role=str(raw.get("role", "")),
                video_path=str(raw.get("video", "")),
                start_frame=_coerce_int(raw.get("start_frame"), 0),
                end_frame=_coerce_int(raw.get("end_frame"), 0),
                fps=float(raw.get("fps", 0.0) or 0.0),
                width=_coerce_int(raw.get("width"), 0),
                height=_coerce_int(raw.get("height"), 0),
            )
        )
    return clips


def selected_playback_clip(clips: list[PlaybackClip], clip_id: str | None = None) -> PlaybackClip:
    if not clips:
        return PlaybackClip("manual", "manual", "", 0, 0, 30.0, 0, 0)
    for clip in clips:
        if clip.clip_id == clip_id:
            return clip
    return clips[0]


def live_playback_config_from_project(
    root: Path,
    config: dict[str, Any],
    output_dir: Path,
    clip_id: str | None = None,
    video_path: str | None = None,
    tracks_csv: str | None = None,
    events_json: str | None = None,
    highlights_csv: str | None = None,
) -> LivePlaybackConfig:
    clip = selected_playback_clip(playback_clips_from_config(config), clip_id)
    return LivePlaybackConfig(
        clip_id=clip.clip_id,
        video_path=video_path if video_path is not None else clip.video_path,
        fps=clip.fps or 30.0,
        width=clip.width,
        height=clip.height,
        start_frame=clip.start_frame,
        end_frame=clip.end_frame,
        tracks_csv=tracks_csv or _first_existing(root, DEFAULT_TRACKS_CANDIDATES).as_posix(),
        events_json=events_json or _first_existing(root, DEFAULT_EVENTS_CANDIDATES).as_posix(),
        highlights_csv=highlights_csv or _first_existing(root, DEFAULT_HIGHLIGHTS_CANDIDATES).as_posix(),
        output_dir=output_dir.as_posix(),
    )


def frame_from_timestamp(
    timestamp_sec: float,
    fps: float,
    start_frame: int = 0,
    end_frame: int | None = None,
) -> int:
    frame = int(round(max(0.0, timestamp_sec) * fps))
    if frame < start_frame:
        return start_frame
    if end_frame is not None and frame > end_frame:
        return end_frame
    return frame


def timestamp_from_frame(frame: int, fps: float) -> float:
    if fps <= 0:
        return 0.0
    return frame / fps


def available_frame_numbers(tracks: list[dict[str, Any]]) -> list[int]:
    return sorted({_coerce_int(row.get("frame"), 0) for row in tracks})


def resolve_overlay_frame(
    target_frame: int,
    available_frames: list[int],
    max_gap_frames: int | None = None,
) -> FrameResolution:
    if not available_frames:
        return FrameResolution(target_frame, None, "missing", None)
    if target_frame in set(available_frames):
        return FrameResolution(target_frame, target_frame, "exact", 0)

    previous_frames = [frame for frame in available_frames if frame <= target_frame]
    if previous_frames:
        previous = previous_frames[-1]
        gap = target_frame - previous
        if max_gap_frames is None or gap <= max_gap_frames:
            return FrameResolution(target_frame, previous, "previous", gap)

    future_frames = [frame for frame in available_frames if frame > target_frame]
    if future_frames:
        future = future_frames[0]
        gap = future - target_frame
        if max_gap_frames is None or gap <= max_gap_frames:
            return FrameResolution(target_frame, future, "future", gap)
    return FrameResolution(target_frame, None, "missing", None)


def video_metadata_from_config(playback_config: LivePlaybackConfig) -> VideoMetadata:
    video = resolve_configured_video(playback_config)
    exists = bool(video and video.exists() and video.is_file())
    size = video.stat().st_size if exists and video else 0
    frame_count = max(0, playback_config.end_frame - playback_config.start_frame + 1)
    duration = frame_count / playback_config.fps if playback_config.fps else 0.0
    return VideoMetadata(
        clip_id=playback_config.clip_id,
        fps_nominal=playback_config.fps,
        width=playback_config.width,
        height=playback_config.height,
        frame_start=playback_config.start_frame,
        frame_end=playback_config.end_frame,
        configured_frame_count=frame_count,
        configured_duration_sec=round(duration, 6),
        video_path=playback_config.video_path,
        video_exists=exists,
        video_size_bytes=size,
        metadata_source="configs/default.yaml:level2_closure",
        notes="Browser duration is read at runtime; saved duration is derived from configured frame range and FPS.",
    )


def sync_summary_from_frames(playback_config: LivePlaybackConfig, frames: list[int]) -> dict[str, Any]:
    if not frames:
        return {
            "available_frame_count": 0,
            "first_available_frame": "",
            "last_available_frame": "",
            "max_frame_gap": 0,
            "jump_reset_threshold_frames": max(8, playback_config.trail_length * 2),
            "interpolation_enabled": False,
            "interpolation_policy": "disabled; no frames available",
        }
    gaps = [frames[index] - frames[index - 1] for index in range(1, len(frames))]
    max_gap = max(gaps, default=0)
    return {
        "available_frame_count": len(frames),
        "first_available_frame": frames[0],
        "last_available_frame": frames[-1],
        "max_frame_gap": max_gap,
        "jump_reset_threshold_frames": max(8, playback_config.trail_length * 2),
        "interpolation_enabled": False,
        "interpolation_policy": "disabled; use exact frame or previous available frame for stride",
    }


def build_stream_messages(context: dict[str, Any]) -> list[dict[str, Any]]:
    config: LivePlaybackConfig = context["config"]
    tracks_by_frame = _tracks_by_frame(context["tracks"])
    frames = context["available_frames"]
    messages: list[dict[str, Any]] = []
    sequence = 0

    def add(message_type: str, payload: dict[str, Any]) -> dict[str, Any]:
        nonlocal sequence
        sequence += 1
        message = {
            "id": f"{config.clip_id}:{sequence:05d}",
            "type": message_type,
            "sequence": sequence,
            "clip_id": config.clip_id,
            "transport": "sse",
            "rule_version": RULE_VERSION,
        }
        message.update(payload)
        messages.append(message)
        return message

    add(
        "session_status",
        {
            "status": "open",
            "mode": "playback_precomputado",
            "fps": config.fps,
            "frame_start": config.start_frame,
            "frame_end": config.end_frame,
            "available_frame_count": len(frames),
            "endpoint": "/stream",
        },
    )
    video_metadata: VideoMetadata = context["video_metadata"]
    if not video_metadata.video_exists:
        add(
            "warning",
            {
                "severity": "warn",
                "warning_code": "video_missing",
                "message": "Video local no disponible; el canal SSE emite datos precomputados sin servir video.",
            },
        )
    if not frames:
        add(
            "warning",
            {
                "severity": "warn",
                "warning_code": "no_frame_data",
                "message": "No hay frames con tracks normalizados para emitir resultados frame a frame.",
            },
        )

    for event in context["events"]:
        add("event_update", _event_update_payload(event, "event"))
    for highlight in context["highlights"]:
        add("event_update", _event_update_payload(highlight, "highlight"))

    for frame in frames:
        rows = tracks_by_frame.get(frame, [])
        events = _active_events_for_frame(context["events"], frame)
        highlights = _active_events_for_frame(context["highlights"], frame)
        resolution = resolve_overlay_frame(frame, frames)
        timestamp = round(timestamp_from_frame(frame, config.fps), 6)
        add(
            "frame_result",
            {
                "frame": frame,
                "timestamp_sec": timestamp,
                "target_frame": resolution.target_frame,
                "resolved_frame": resolution.resolved_frame,
                "resolution_status": resolution.status,
                "frame_gap": resolution.frame_gap,
                "track_count": len(rows),
                "track_ids": [str(row.get("track_id", "")) for row in rows[:24]],
                "ball_count": sum(1 for row in rows if row.get("class") == "ball"),
                "event_count": len(events),
                "highlight_count": len(highlights),
            },
        )
        add(
            "latency_metrics",
            {
                "frame": frame,
                "timestamp_sec": timestamp,
                "resolved_frame": resolution.resolved_frame,
                "resolution_status": resolution.status,
                "track_count": len(rows),
                "event_count": len(events),
                "highlight_count": len(highlights),
                "lookup_latency_ms": 0.0,
                "emit_latency_ms": 0.0,
                "queue_depth": 0,
                "backpressure": False,
                "source": "precomputed_artifacts",
            },
        )

    completion = add(
        "session_status",
        {
            "status": "complete",
            "mode": "playback_precomputado",
            "emitted_frame_count": len(frames),
            "message_count": 0,
            "endpoint": "/stream",
        },
    )
    completion["message_count"] = len(messages)
    return messages


def stream_summary_from_messages(context: dict[str, Any], messages: list[dict[str, Any]]) -> dict[str, Any]:
    message_counts = {message_type: 0 for message_type in STREAM_MESSAGE_TYPES}
    for message in messages:
        message_type = str(message.get("type", ""))
        if message_type in message_counts:
            message_counts[message_type] += 1
    warnings = [message for message in messages if message.get("type") == "warning"]
    latency_messages = [message for message in messages if message.get("type") == "latency_metrics"]
    return {
        "transport": "sse",
        "selected_transport_reason": "SSE cubre el flujo backend->frontend local sin comandos bidireccionales ni dependencias extra.",
        "websocket_status": "deferred_until_bidirectional_commands",
        "message_types": list(STREAM_MESSAGE_TYPES),
        "message_count": len(messages),
        "message_counts": message_counts,
        "frame_result_count": message_counts["frame_result"],
        "latency_metric_count": len(latency_messages),
        "warning_count": len(warnings),
        "warning_codes": [str(message.get("warning_code", "")) for message in warnings],
        "average_lookup_latency_ms": _average_metric(latency_messages, "lookup_latency_ms"),
        "max_emit_latency_ms": _max_metric(latency_messages, "emit_latency_ms"),
        "frontend_reconnect_policy": "EventSource automatic reconnect; the client closes the stream after session_status=complete.",
        "log_artifact": "stream_messages.jsonl",
        "latency_artifact": "stream_latency_metrics.csv",
        "summary_artifact": "stream_summary.json",
        "clip_id": context["config"].clip_id,
    }


def stream_messages_jsonl(messages: list[dict[str, Any]]) -> str:
    return "\n".join(json.dumps(message, ensure_ascii=True, separators=(",", ":")) for message in messages) + "\n"


def stream_latency_metrics_csv(messages: list[dict[str, Any]]) -> str:
    handle = io.StringIO()
    writer = csv.DictWriter(handle, fieldnames=STREAM_LATENCY_FIELDS, lineterminator="\n")
    writer.writeheader()
    for message in messages:
        if message.get("type") != "latency_metrics":
            continue
        row = {field: message.get(field, "") for field in STREAM_LATENCY_FIELDS}
        row["message_id"] = message.get("id", "")
        writer.writerow(row)
    return handle.getvalue()


def sse_format_message(message: dict[str, Any]) -> str:
    message_type = str(message.get("type", "message"))
    message_id = str(message.get("id", ""))
    data = json.dumps(message, ensure_ascii=True, separators=(",", ":"))
    return f"id: {message_id}\nevent: {message_type}\ndata: {data}\n\n"


def sse_stream_text(messages: list[dict[str, Any]]) -> str:
    return "retry: 3000\n\n" + "".join(sse_format_message(message) for message in messages)


def backend_endpoint_manifest(context: dict[str, Any]) -> dict[str, Any]:
    config: LivePlaybackConfig = context["config"]
    video_metadata: VideoMetadata = context["video_metadata"]
    endpoints = [
        _endpoint_row("/health", "text/plain", "status", "Backend health check."),
        _endpoint_row("/playback.html", "text/html", "ui", "Playback UI with video and canvas overlay."),
        _endpoint_row("/data.json", "application/json", "combined_data", "Combined payload for simple clients."),
        _endpoint_row("/manifest.json", "application/json", "manifest", "Endpoint and artifact manifest."),
        _endpoint_row("/stream", "text/event-stream", "stream", "SSE channel for session_status, frame_result, event_update, latency_metrics and warning messages."),
        _endpoint_row("/stream-summary.json", "application/json", "stream_summary", "SSE message counts, latency summary and transport decision."),
        _endpoint_row("/stream-messages.jsonl", "application/x-ndjson", "stream_log", "Lightweight log of emitted SSE messages."),
        _endpoint_row("/stream-latency.csv", "text/csv", "stream_metrics", "Latency metrics emitted by the SSE channel."),
        _endpoint_row("/tracks.csv", "text/csv", "tracks", "Normalized live tracks."),
        _endpoint_row("/events.json", "application/json", "events", "Normalized live events."),
        _endpoint_row("/highlights.csv", "text/csv", "highlights", "Normalized live highlights."),
        _endpoint_row("/minimap.json?frame=120", "application/json", "minimap", "Frame-specific minimap payload."),
        _endpoint_row("/calibration.json", "application/json", "calibration", "Calibration status inferred from normalized tracks."),
        _endpoint_row("/video-metadata.json", "application/json", "video_metadata", "Configured video metadata."),
        _endpoint_row(f"/video?clip_id={config.clip_id}", "video/*", "local_video", "Configured local video; heavy file is not versioned."),
    ]
    return {
        "rule_version": RULE_VERSION,
        "mode": "playback_precomputado",
        "backend": "stdlib_http_server",
        "clip_id": config.clip_id,
        "experiment_dir": config.output_dir,
        "channel": {
            "selected": "sse",
            "websocket_status": "deferred_until_bidirectional_commands",
            "reason": "Playback local solo requiere flujo backend->frontend; WebSocket queda reservado para comandos online bidireccionales.",
            "message_types": list(STREAM_MESSAGE_TYPES),
        },
        "video": {
            "path": config.video_path,
            "exists": video_metadata.video_exists,
            "size_bytes": video_metadata.video_size_bytes,
            "is_versioned": False,
            "missing_note": "" if video_metadata.video_exists else "Video local no disponible en esta maquina; copiarlo fuera de Git o ajustar --video.",
        },
        "artifacts": {
            "tracks": "live_tracks.csv",
            "events": "live_events.json",
            "highlights": "live_highlights.csv",
            "minimap_sample": "minimap_frame_sample.json",
            "video_metadata": "video_metadata.json",
            "stream_messages": "stream_messages.jsonl",
            "stream_latency_metrics": "stream_latency_metrics.csv",
            "stream_summary": "stream_summary.json",
            "config": "config.yaml",
            "summary": "summary.md",
        },
        "endpoints": endpoints,
        "path_policy": {
            "video": "only the configured clip_id is served; arbitrary path query parameters are rejected",
            "artifacts": "fixed endpoint names only; no arbitrary filesystem path endpoint",
        },
    }


def calibration_payload(context: dict[str, Any]) -> dict[str, Any]:
    tracks = context["tracks"]
    confidences = [
        float(row["calibration_confidence"])
        for row in tracks
        if row.get("calibration_confidence", "") != ""
    ]
    zones = sorted({str(row.get("zone", "")) for row in tracks if row.get("zone", "")})
    return {
        "clip_id": context["config"].clip_id,
        "status": "rectified" if confidences else "unavailable",
        "confidence": round(min(confidences), 6) if confidences else "",
        "source": context["config"].tracks_csv,
        "zones": zones,
        "notes": "Calibration is inferred from normalized track columns x_norm, y_norm and calibration_confidence.",
    }


def minimap_payload_for_frame(context: dict[str, Any], frame: int | None = None) -> dict[str, Any]:
    config: LivePlaybackConfig = context["config"]
    if frame is None:
        frame = context["available_frames"][0] if context["available_frames"] else config.start_frame
    return build_minimap_payload(
        context["tracks"],
        config.clip_id,
        frame,
        timestamp_from_frame(frame, config.fps),
        calibration_status=calibration_payload(context)["status"],
    )


def csv_response_text(rows: list[dict[str, Any]], fieldnames: tuple[str, ...]) -> str:
    handle = io.StringIO()
    writer = csv.DictWriter(handle, fieldnames=list(fieldnames), lineterminator="\n")
    writer.writeheader()
    for row in rows:
        writer.writerow({field: row.get(field, "") for field in fieldnames})
    return handle.getvalue()


def resolve_requested_video(playback_config: LivePlaybackConfig, params: dict[str, list[str]]) -> Path:
    if "path" in params:
        raise PermissionError("path query is not allowed for video endpoint")
    clip_id = _first(params, "clip_id", "")
    if clip_id and clip_id != playback_config.clip_id:
        raise FileNotFoundError("clip not configured")
    video = resolve_configured_video(playback_config)
    if not video or not video.exists() or not video.is_file():
        raise FileNotFoundError("configured video not found")
    return video


def build_live_playback_package(root: Path, config_path: Path, playback_config: LivePlaybackConfig) -> dict[str, Any]:
    context = build_live_playback_context(root, playback_config)
    output_dir = root / playback_config.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    write_live_tracks_csv(output_dir / "live_tracks.csv", context["tracks"])
    write_live_events_json(output_dir / "live_events.json", context["events"])
    write_live_highlights_csv(output_dir / "live_highlights.csv", context["highlights"])
    (output_dir / "minimap_frame_sample.json").write_text(
        json.dumps(context["minimap_sample"], indent=2, ensure_ascii=True) + "\n",
        encoding="utf-8",
    )
    (output_dir / "video_metadata.json").write_text(
        json.dumps(asdict(context["video_metadata"]), indent=2, ensure_ascii=True) + "\n",
        encoding="utf-8",
    )
    (output_dir / "endpoint_manifest.json").write_text(
        json.dumps(backend_endpoint_manifest(context), indent=2, ensure_ascii=True) + "\n",
        encoding="utf-8",
    )
    (output_dir / "stream_messages.jsonl").write_text(
        stream_messages_jsonl(context["stream_messages"]),
        encoding="utf-8",
    )
    (output_dir / "stream_latency_metrics.csv").write_text(
        stream_latency_metrics_csv(context["stream_messages"]),
        encoding="utf-8",
    )
    (output_dir / "stream_summary.json").write_text(
        json.dumps(context["stream_summary"], indent=2, ensure_ascii=True) + "\n",
        encoding="utf-8",
    )
    (output_dir / "playback.html").write_text(render_playback_html(context), encoding="utf-8")
    write_live_playback_config(root, config_path, playback_config, context)
    write_live_playback_manifest(root, playback_config, context)
    write_live_playback_summary(root, playback_config, context)
    return context


def build_live_playback_context(root: Path, playback_config: LivePlaybackConfig) -> dict[str, Any]:
    tracks_source = _read_csv_if_exists(root / playback_config.tracks_csv)
    normalized_tracks = [
        normalize_track_row(row, clip_id=playback_config.clip_id, fps=playback_config.fps)
        for row in tracks_source
        if _row_matches_clip_and_range(row, playback_config)
    ]
    events_source = _read_json_events_if_exists(root / playback_config.events_json)
    normalized_events = [
        normalize_event(row)
        for row in events_source
        if _event_matches_clip_and_range(row, playback_config)
    ]
    highlights_source = _read_csv_if_exists(root / playback_config.highlights_csv)
    normalized_highlights = [
        normalize_highlight_row(row)
        for row in highlights_source
        if _highlight_matches_clip_and_range(row, playback_config)
    ]
    frame_sample = normalized_tracks[0]["frame"] if normalized_tracks else playback_config.start_frame
    minimap_sample = build_minimap_payload(
        normalized_tracks,
        playback_config.clip_id,
        int(frame_sample),
        int(frame_sample) / playback_config.fps if playback_config.fps else 0.0,
        calibration_status="rectified" if any(row.get("x_norm") for row in normalized_tracks) else "unavailable",
    )
    validation = validate_playback_payload(normalized_tracks, normalized_events, normalized_highlights, minimap_sample)
    frames = available_frame_numbers(normalized_tracks)
    video_metadata = video_metadata_from_config(playback_config)
    sync = sync_summary_from_frames(playback_config, frames)
    context = {
        "rule_version": RULE_VERSION,
        "config": playback_config,
        "tracks": normalized_tracks,
        "events": normalized_events,
        "highlights": normalized_highlights,
        "minimap_sample": minimap_sample,
        "video_metadata": video_metadata,
        "sync": sync,
        "available_frames": frames,
        "validation": validation,
        "summary": {
            "clip_id": playback_config.clip_id,
            "track_rows": len(normalized_tracks),
            "event_count": len(normalized_events),
            "highlight_count": len(normalized_highlights),
            "frame_start": playback_config.start_frame,
            "frame_end": playback_config.end_frame,
            "fps": playback_config.fps,
            "video_path": playback_config.video_path,
            "video_exists": video_metadata.video_exists,
            "video_size_bytes": video_metadata.video_size_bytes,
            "configured_duration_sec": video_metadata.configured_duration_sec,
            "configured_frame_count": video_metadata.configured_frame_count,
            "available_frame_count": sync["available_frame_count"],
            "max_frame_gap": sync["max_frame_gap"],
            "tracks_csv": playback_config.tracks_csv,
            "events_json": playback_config.events_json,
            "highlights_csv": playback_config.highlights_csv,
            "validation_errors": sum(len(row["errors"]) for row in validation),
        },
    }
    stream_messages = build_stream_messages(context)
    context["stream_messages"] = stream_messages
    context["stream_summary"] = stream_summary_from_messages(context, stream_messages)
    context["summary"]["stream_message_count"] = context["stream_summary"]["message_count"]
    context["summary"]["stream_warning_count"] = context["stream_summary"]["warning_count"]
    context["summary"]["stream_frame_result_count"] = context["stream_summary"]["frame_result_count"]
    return context


def validate_playback_payload(
    tracks: list[dict[str, Any]],
    events: list[dict[str, Any]],
    highlights: list[dict[str, Any]],
    minimap_sample: dict[str, Any],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for index, row in enumerate(tracks):
        errors = validate_live_track_row(row)
        if errors:
            rows.append({"artifact": "live_tracks.csv", "index": index, "errors": errors})
    for index, event in enumerate(events):
        errors = validate_live_event(event)
        if errors:
            rows.append({"artifact": "live_events.json", "index": index, "errors": errors})
    for index, row in enumerate(highlights):
        errors = validate_live_highlight_row(row)
        if errors:
            rows.append({"artifact": "live_highlights.csv", "index": index, "errors": errors})
    minimap_errors = validate_minimap_payload(minimap_sample)
    if minimap_errors:
        rows.append({"artifact": "minimap_frame_sample.json", "index": 0, "errors": minimap_errors})
    return rows


def render_playback_html(context: dict[str, Any]) -> str:
    config: LivePlaybackConfig = context["config"]
    payload = client_payload(context)
    payload_json = json.dumps(payload, ensure_ascii=True, separators=(",", ":"))
    return "\n".join(
        [
            "<!doctype html>",
            '<html lang="es">',
            "<head>",
            '<meta charset="utf-8">',
            '<meta name="viewport" content="width=device-width, initial-scale=1">',
            "<title>FutBotMX Playback Vivo</title>",
            f"<style>{_css()}</style>",
            "</head>",
            "<body>",
            '<main class="shell">',
            "<header>",
            "<div>",
            "<p>FutBotMX</p>",
            "<h1>Playback vivo</h1>",
            "</div>",
            f'<span id="syncState" class="state">{_esc("replaying_cache")}</span>',
            "</header>",
            '<section class="workbench">',
            '<div class="stage">',
            '<video id="video" controls preload="metadata" playsinline data-clip-id="' + _esc(config.clip_id) + '">',
            '<source src="/video?clip_id=' + _esc(config.clip_id) + '" type="video/mp4">',
            "</video>",
            '<canvas id="overlay"></canvas>',
            '<div id="videoMissing" class="missing" hidden>Video local no disponible en esta maquina.</div>',
            "</div>",
            '<aside class="panel">',
            '<label class="field">Clip<select id="clipSelect"><option value="' + _esc(config.clip_id) + '">' + _esc(config.clip_id) + "</option></select></label>",
            '<label class="field">Experimento<select id="experimentSelect"><option value="' + _esc(config.output_dir) + '">' + _esc(config.output_dir) + "</option></select></label>",
            '<div class="stats">',
            '<span>Frame objetivo <strong id="frameReadout">0</strong></span>',
            '<span>Frame overlay <strong id="resolvedFrameReadout">sin datos</strong></span>',
            '<span>Tiempo <strong id="timeReadout">0.000s</strong></span>',
            '<span>Duracion <strong id="durationReadout">config</strong></span>',
            '<span>Velocidad <strong id="rateReadout">1.00x</strong></span>',
            '<span>Datos <strong id="dataReadout">sin datos</strong></span>',
            '<span>Canal <strong id="streamReadout">sse pendiente</strong></span>',
            '<span>Mensajes <strong id="streamMessageReadout">0</strong></span>',
            '<span>Latencia <strong id="latencyReadout">n/a</strong></span>',
            "</div>",
            '<div class="toggles">',
            _toggle("layerTracks", "Tracks", True),
            _toggle("layerIds", "IDs", True),
            _toggle("layerBall", "Balon", True),
            _toggle("layerTrails", "Trails", True),
            _toggle("layerEvents", "Eventos", True),
            _toggle("layerPossession", "Posesion", True),
            _toggle("layerMinimap", "Mini-mapa", True),
            _toggle("layerHighlights", "Highlights", True),
            _toggle("layerDebug", "Debug", False),
            "</div>",
            '<div class="timeline" id="eventList"></div>',
            '<div class="timeline stream" id="streamList"></div>',
            "</aside>",
            "</section>",
            "</main>",
            f"<script>window.FUTBOT_PLAYBACK_DATA={payload_json};{_js()}</script>",
            "</body>",
            "</html>",
        ]
    ) + "\n"


def client_payload(context: dict[str, Any]) -> dict[str, Any]:
    config: LivePlaybackConfig = context["config"]
    return {
        "rule_version": context["rule_version"],
        "config": {
            "clip_id": config.clip_id,
            "fps": config.fps,
            "width": config.width,
            "height": config.height,
            "start_frame": config.start_frame,
            "end_frame": config.end_frame,
            "trail_length": config.trail_length,
            "video_exists": context["summary"]["video_exists"],
        },
        "sync": context["sync"],
        "available_frames": context["available_frames"],
        "video_metadata": asdict(context["video_metadata"]),
        "stream_summary": context["stream_summary"],
        "endpoints": {
            "manifest": "/manifest.json",
            "stream": "/stream",
            "stream_summary": "/stream-summary.json",
            "stream_messages": "/stream-messages.jsonl",
            "stream_latency": "/stream-latency.csv",
            "tracks": "/tracks.csv",
            "events": "/events.json",
            "highlights": "/highlights.csv",
            "minimap": "/minimap.json",
            "calibration": "/calibration.json",
            "video_metadata": "/video-metadata.json",
            "video": f"/video?clip_id={config.clip_id}",
        },
        "tracks": context["tracks"],
        "events": context["events"],
        "highlights": context["highlights"],
        "summary": context["summary"],
    }


def write_live_playback_config(root: Path, config_path: Path, playback_config: LivePlaybackConfig, context: dict[str, Any]) -> None:
    config = load_config(root / config_path)
    config["live_playback"] = {
        "rule_version": RULE_VERSION,
        "mode": "playback_precomputado",
        "clock_source": "video_currentTime",
        "contract": "live_playback_data_contract_v0.1",
        "config": asdict(playback_config),
        "summary": context["summary"],
        "video_metadata": asdict(context["video_metadata"]),
        "sync": context["sync"],
        "stream": context["stream_summary"],
        "outputs": [
            "playback.html",
            "live_tracks.csv",
            "live_events.json",
            "live_highlights.csv",
            "minimap_frame_sample.json",
            "video_metadata.json",
            "endpoint_manifest.json",
            "stream_messages.jsonl",
            "stream_latency_metrics.csv",
            "stream_summary.json",
            "live_playback_manifest.csv",
            "summary.md",
        ],
    }
    write_config_snapshot(config, root / playback_config.output_dir / "config.yaml")


def write_live_playback_manifest(root: Path, playback_config: LivePlaybackConfig, context: dict[str, Any]) -> None:
    rows = [
        _manifest_row("playback_html", "html", "playback.html", "render_playback_html", True, "ui", "Video element plus synchronized canvas overlay."),
        _manifest_row("config", "yaml", "config.yaml", "configs/default.yaml", True, "config", "Live playback configuration snapshot."),
        _manifest_row("summary", "md", "summary.md", "live_playback", True, "summary", "Live playback summary."),
        _manifest_row("manifest", "csv", "live_playback_manifest.csv", "live_playback", True, "manifest", "Live playback artifact manifest."),
        _manifest_row("live_tracks", "csv", "live_tracks.csv", playback_config.tracks_csv, True, "data", f"{len(context['tracks'])} normalized track rows."),
        _manifest_row("live_events", "json", "live_events.json", playback_config.events_json, True, "data", f"{len(context['events'])} normalized events."),
        _manifest_row("live_highlights", "csv", "live_highlights.csv", playback_config.highlights_csv, True, "data", f"{len(context['highlights'])} normalized highlights."),
        _manifest_row("minimap_sample", "json", "minimap_frame_sample.json", "live_tracks.csv", True, "data", "Sample minimap payload for first frame with rectified points."),
        _manifest_row("video_metadata", "json", "video_metadata.json", "configs/default.yaml", True, "sync", "FPS, dimensions, configured duration and approximate frame count."),
        _manifest_row("endpoint_manifest", "json", "endpoint_manifest.json", "live_playback_backend", True, "backend", "Local backend endpoints and path policy."),
        _manifest_row("stream_messages", "jsonl", "stream_messages.jsonl", "live_playback_stream", True, "stream", f"{context['stream_summary']['message_count']} emitted SSE messages."),
        _manifest_row("stream_latency_metrics", "csv", "stream_latency_metrics.csv", "live_playback_stream", True, "stream", f"{context['stream_summary']['latency_metric_count']} latency metric rows."),
        _manifest_row("stream_summary", "json", "stream_summary.json", "live_playback_stream", True, "stream", "SSE transport decision, message counts and warning summary."),
        _manifest_row("source_video", "video", playback_config.video_path, "local video path", False, "local_input", "Heavy/local input; never versioned."),
    ]
    output = root / playback_config.output_dir / "live_playback_manifest.csv"
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=MANIFEST_FIELDS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def write_live_playback_summary(root: Path, playback_config: LivePlaybackConfig, context: dict[str, Any]) -> None:
    summary = context["summary"]
    validation_rows = context["validation"]
    lines = [
        "# Playback Vivo Con Overlays Precomputados",
        "",
        "## Resultado",
        "",
        f"- Estado: `{'pass' if not validation_rows else 'warn'}`.",
        f"- Regla: `{RULE_VERSION}`.",
        "- Modo: `playback_precomputado`.",
        f"- Clip: `{summary['clip_id']}`.",
        f"- Frames: `{summary['frame_start']}-{summary['frame_end']}`.",
        f"- FPS configurado: `{summary['fps']}`.",
        f"- Duracion configurada: `{summary['configured_duration_sec']}` segundos.",
        f"- Frames configurados aproximados: `{summary['configured_frame_count']}`.",
        f"- Frames con datos disponibles: `{summary['available_frame_count']}`.",
        f"- Mayor salto entre frames disponibles: `{summary['max_frame_gap']}`.",
        f"- Video local existe: `{str(summary['video_exists']).lower()}`.",
        f"- Tracks normalizados: `{summary['track_rows']}`.",
        f"- Eventos normalizados: `{summary['event_count']}`.",
        f"- Highlights normalizados: `{summary['highlight_count']}`.",
        f"- Mensajes SSE emitibles: `{summary['stream_message_count']}`.",
        f"- Resultados frame a frame SSE: `{summary['stream_frame_result_count']}`.",
        f"- Warnings SSE: `{summary['stream_warning_count']}`.",
        f"- Errores de validacion: `{summary['validation_errors']}`.",
        "",
        "## Capas",
        "",
        "- Tracks, IDs, balon, trails, eventos, posesion candidata, mini-mapa, highlights y debug.",
        "",
        "## Artefactos",
        "",
        "- `playback.html`.",
        "- `live_tracks.csv`.",
        "- `live_events.json`.",
        "- `live_highlights.csv`.",
        "- `minimap_frame_sample.json`.",
        "- `video_metadata.json`.",
        "- `endpoint_manifest.json`.",
        "- `stream_messages.jsonl`.",
        "- `stream_latency_metrics.csv`.",
        "- `stream_summary.json`.",
        "- `config.yaml`.",
        "- `live_playback_manifest.csv`.",
        "",
        "## Backend Local",
        "",
        "- Endpoints fijos: `/manifest.json`, `/stream`, `/stream-summary.json`, `/stream-messages.jsonl`, `/stream-latency.csv`, `/tracks.csv`, `/events.json`, `/highlights.csv`, `/minimap.json`, `/calibration.json`, `/video-metadata.json` y `/video?clip_id=...`.",
        "- Politica de video: solo se sirve el `clip_id` configurado; no se aceptan rutas arbitrarias por query.",
        "- Video pesado: permanece fuera de Git y queda marcado como `is_versioned=false`.",
        "- Si el video no existe en otro equipo, el reproductor muestra aviso local y conserva datos/overlays versionados.",
        "",
        "## Canal SSE",
        "",
        "- Transporte seleccionado: `SSE` por flujo local unidireccional backend->frontend.",
        "- WebSocket: diferido hasta requerir comandos bidireccionales del motor online.",
        "- Mensajes: `session_status`, `frame_result`, `event_update`, `latency_metrics` y `warning`.",
        "- Reconexion frontend: `EventSource` usa reconexion automatica y cierra el canal al recibir `session_status=complete`.",
        "- Log ligero: `stream_messages.jsonl`.",
        "- Metricas: `stream_latency_metrics.csv`.",
        "",
        "## Sincronizacion",
        "",
        "- Conversion: `frame = round(currentTime * fps)`.",
        "- Resolucion: frame exacto si existe; si no existe, frame anterior disponible por stride.",
        "- Interpolacion: deshabilitada por defecto hasta que un modo explicito la active.",
        "- Seek: el frontend recalcula el overlay y limpia trails si detecta salto temporal grande.",
        "- Duracion real del elemento `<video>` se lee en navegador; el JSON guarda duracion configurada del rango de frames.",
        "",
        "## Comando",
        "",
        "```bash",
        ".venv/bin/python scripts/run_live_playback_app.py",
        "```",
    ]
    if validation_rows:
        lines.extend(["", "## Validacion", ""])
        for row in validation_rows[:12]:
            lines.append(f"- `{row['artifact']}` fila `{row['index']}`: `{';'.join(row['errors'])}`.")
    output = root / playback_config.output_dir / "summary.md"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run_smoke_test(
    root: Path,
    config_path: Path,
    output_dir: Path,
    clip_id: str | None = None,
    video_path: str | None = None,
) -> dict[str, Any]:
    project_config = load_config(root / config_path)
    playback_config = live_playback_config_from_project(root, project_config, output_dir, clip_id=clip_id, video_path=video_path)
    return build_live_playback_package(root, config_path, playback_config)


def serve_live_playback_app(
    root: Path,
    config_path: Path,
    output_dir: Path,
    host: str,
    port: int,
    clip_id: str | None = None,
    video_path: str | None = None,
) -> None:
    context = run_smoke_test(root, config_path, output_dir, clip_id=clip_id, video_path=video_path)
    handler = make_handler(root, context)
    server = ThreadingHTTPServer((host, port), handler)
    actual_host, actual_port = server.server_address
    display_host = host if host != "0.0.0.0" else actual_host
    print(f"FutBotMX live playback: http://{display_host}:{actual_port}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("Stopping FutBotMX live playback", flush=True)
    finally:
        server.server_close()


def make_handler(root: Path, context: dict[str, Any]) -> type[BaseHTTPRequestHandler]:
    class LivePlaybackHandler(BaseHTTPRequestHandler):
        server_version = "FutBotMXLivePlayback/0.1"

        def do_GET(self) -> None:
            parsed = urlparse(self.path)
            if parsed.path == "/health":
                self._send_text("ok\n", "text/plain; charset=utf-8")
                return
            if parsed.path == "/data.json":
                self._send_json(client_payload(context))
                return
            if parsed.path == "/manifest.json":
                self._send_json(backend_endpoint_manifest(context))
                return
            if parsed.path == "/stream":
                self._send_sse_stream()
                return
            if parsed.path == "/stream-summary.json":
                self._send_json(context["stream_summary"])
                return
            if parsed.path == "/stream-messages.jsonl":
                self._send_text(stream_messages_jsonl(context["stream_messages"]), "application/x-ndjson; charset=utf-8")
                return
            if parsed.path == "/stream-latency.csv":
                self._send_text(stream_latency_metrics_csv(context["stream_messages"]), "text/csv; charset=utf-8")
                return
            if parsed.path == "/tracks.csv":
                self._send_text(csv_response_text(context["tracks"], LIVE_TRACK_FIELDS), "text/csv; charset=utf-8")
                return
            if parsed.path == "/events.json":
                self._send_json(context["events"])
                return
            if parsed.path == "/highlights.csv":
                self._send_text(csv_response_text(context["highlights"], LIVE_HIGHLIGHT_FIELDS), "text/csv; charset=utf-8")
                return
            if parsed.path == "/minimap.json":
                params = parse_qs(parsed.query)
                frame = _coerce_int(_first(params, "frame", ""), 0) if "frame" in params else None
                self._send_json(minimap_payload_for_frame(context, frame=frame))
                return
            if parsed.path == "/calibration.json":
                self._send_json(calibration_payload(context))
                return
            if parsed.path == "/video-metadata.json":
                self._send_json(asdict(context["video_metadata"]))
                return
            if parsed.path == "/video":
                self._send_video(parsed.query)
                return
            if parsed.path in {"/", "/playback.html"}:
                self._send_text(render_playback_html(context), "text/html; charset=utf-8")
                return
            self.send_error(404)

        def log_message(self, format: str, *args: Any) -> None:
            sys.stderr.write("live_playback: " + format % args + "\n")

        def _send_text(self, payload: str, content_type: str) -> None:
            body = payload.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _send_json(self, payload: Any) -> None:
            self._send_text(json.dumps(payload, ensure_ascii=True), "application/json; charset=utf-8")

        def _send_sse_stream(self) -> None:
            body = sse_stream_text(context["stream_messages"]).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream; charset=utf-8")
            self.send_header("Cache-Control", "no-cache")
            self.send_header("Connection", "keep-alive")
            self.end_headers()
            self.wfile.write(body)
            self.wfile.flush()

        def _send_video(self, query: str) -> None:
            params = parse_qs(query)
            config: LivePlaybackConfig = context["config"]
            try:
                video = resolve_requested_video(config, params)
            except PermissionError as exc:
                self.send_error(403, str(exc))
                return
            except FileNotFoundError as exc:
                self.send_error(404, str(exc))
                return
            self._send_file_with_range(video)

        def _send_file_with_range(self, path: Path) -> None:
            content_type = mimetypes.guess_type(path.as_posix())[0] or "application/octet-stream"
            size = path.stat().st_size
            range_header = self.headers.get("Range")
            if not range_header:
                body = path.read_bytes()
                self.send_response(200)
                self.send_header("Content-Type", content_type)
                self.send_header("Content-Length", str(len(body)))
                self.send_header("Accept-Ranges", "bytes")
                self.end_headers()
                self.wfile.write(body)
                return
            start, end = _parse_range(range_header, size)
            length = end - start + 1
            with path.open("rb") as handle:
                handle.seek(start)
                body = handle.read(length)
            self.send_response(206)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Content-Range", f"bytes {start}-{end}/{size}")
            self.send_header("Accept-Ranges", "bytes")
            self.end_headers()
            self.wfile.write(body)

    return LivePlaybackHandler


def resolve_configured_video(playback_config: LivePlaybackConfig) -> Path | None:
    if not playback_config.video_path:
        return None
    return Path(unquote(playback_config.video_path)).expanduser()


def _row_matches_clip_and_range(row: dict[str, Any], config: LivePlaybackConfig) -> bool:
    clip_id = str(row.get("clip_id", config.clip_id) or config.clip_id)
    frame = _coerce_int(row.get("frame"), 0)
    return clip_id == config.clip_id and config.start_frame <= frame <= config.end_frame


def _event_matches_clip_and_range(event: dict[str, Any], config: LivePlaybackConfig) -> bool:
    clip_id = str(event.get("clip_id", config.clip_id) or config.clip_id)
    start = _coerce_int(event.get("start_frame", event.get("frame_start", 0)), 0)
    end = _coerce_int(event.get("end_frame", event.get("frame_end", start)), start)
    return clip_id == config.clip_id and end >= config.start_frame and start <= config.end_frame


def _highlight_matches_clip_and_range(row: dict[str, Any], config: LivePlaybackConfig) -> bool:
    clip_id = str(row.get("clip_id", config.clip_id) or config.clip_id)
    start = _coerce_int(row.get("start_frame", row.get("frame_start", 0)), 0)
    end = _coerce_int(row.get("end_frame", row.get("frame_end", start)), start)
    return clip_id == config.clip_id and end >= config.start_frame and start <= config.end_frame


def _read_csv_if_exists(path: Path) -> list[dict[str, str]]:
    return read_csv_rows(path) if path.exists() else []


def _read_json_events_if_exists(path: Path) -> list[dict[str, Any]]:
    return read_json_events(path) if path.exists() else []


def _first_existing(root: Path, candidates: tuple[Path, ...]) -> Path:
    for candidate in candidates:
        if (root / candidate).exists():
            return candidate
    return candidates[0]


def _parse_range(range_header: str, size: int) -> tuple[int, int]:
    unit, _, value = range_header.partition("=")
    if unit.strip() != "bytes" or "-" not in value:
        return 0, size - 1
    start_text, _, end_text = value.partition("-")
    start = _coerce_int(start_text, 0)
    end = _coerce_int(end_text, size - 1) if end_text else size - 1
    return max(0, start), min(size - 1, end)


def _manifest_row(asset_id: str, asset_type: str, path: str, source: str, versioned: bool, role: str, notes: str) -> dict[str, str]:
    return {
        "asset_id": asset_id,
        "asset_type": asset_type,
        "path": path,
        "source_artifact": source,
        "is_versioned": str(versioned).lower(),
        "role": role,
        "notes": notes,
    }


def _endpoint_row(path: str, content_type: str, role: str, notes: str) -> dict[str, str]:
    return {
        "method": "GET",
        "path": path,
        "content_type": content_type,
        "role": role,
        "notes": notes,
    }


def _toggle(element_id: str, label: str, checked: bool) -> str:
    state = " checked" if checked else ""
    return f'<label><input type="checkbox" id="{element_id}"{state}> {_esc(label)}</label>'


def _css() -> str:
    return """
:root{color-scheme:dark;--bg:#10130f;--panel:#171d18;--line:#2e3b31;--text:#edf2e9;--muted:#aab6a4;--accent:#f4c430;--blue:#48a6ff;--red:#ff6b6b;--green:#64d47c}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--text);font-family:Inter,system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;letter-spacing:0}
.shell{min-height:100vh;padding:18px;display:flex;flex-direction:column;gap:14px}
header{display:flex;justify-content:space-between;align-items:center;border-bottom:1px solid var(--line);padding-bottom:12px}
header p{margin:0 0 3px;color:var(--muted);font-size:13px}h1{margin:0;font-size:24px;font-weight:700}
.state{border:1px solid var(--line);border-radius:999px;padding:7px 10px;color:var(--accent);font-size:12px}
.workbench{display:grid;grid-template-columns:minmax(0,1fr) 320px;gap:14px;align-items:start}
.stage{position:relative;min-height:360px;background:#050605;border:1px solid var(--line);overflow:hidden}
video{display:block;width:100%;max-height:calc(100vh - 130px);background:#050605}
canvas{position:absolute;inset:0;width:100%;height:100%;pointer-events:none}
.missing{position:absolute;left:16px;bottom:16px;background:rgba(16,19,15,.86);border:1px solid var(--line);padding:10px 12px;color:var(--muted);font-size:13px}
.panel{border:1px solid var(--line);background:var(--panel);padding:12px;display:flex;flex-direction:column;gap:12px}
.field{display:flex;flex-direction:column;gap:5px;color:var(--muted);font-size:12px}select{width:100%;background:#0d100d;color:var(--text);border:1px solid var(--line);padding:8px}
.stats{display:grid;grid-template-columns:1fr;gap:7px;font-size:13px}.stats span{display:flex;justify-content:space-between;border-bottom:1px solid var(--line);padding-bottom:6px}
.toggles{display:grid;grid-template-columns:1fr 1fr;gap:8px}.toggles label{font-size:13px;color:var(--text)}
.timeline{display:flex;flex-direction:column;gap:8px;max-height:260px;overflow:auto}.stream{max-height:180px}.event{border-left:3px solid var(--accent);background:#111611;padding:8px;font-size:12px;color:var(--muted)}.event strong{color:var(--text)}.stream-event{border-left-color:var(--blue)}
@media(max-width:900px){.shell{padding:10px}.workbench{grid-template-columns:1fr}.panel{order:-1}.stage{min-height:280px}h1{font-size:20px}}
"""


def _js() -> str:
    return """
const data=window.FUTBOT_PLAYBACK_DATA;
const video=document.getElementById('video');
const canvas=document.getElementById('overlay');
const ctx=canvas.getContext('2d');
const missing=document.getElementById('videoMissing');
const frameReadout=document.getElementById('frameReadout');
const resolvedFrameReadout=document.getElementById('resolvedFrameReadout');
const timeReadout=document.getElementById('timeReadout');
const durationReadout=document.getElementById('durationReadout');
const rateReadout=document.getElementById('rateReadout');
const dataReadout=document.getElementById('dataReadout');
const streamReadout=document.getElementById('streamReadout');
const streamMessageReadout=document.getElementById('streamMessageReadout');
const latencyReadout=document.getElementById('latencyReadout');
const streamList=document.getElementById('streamList');
const syncState=document.getElementById('syncState');
const byFrame=new Map();
for(const row of data.tracks){const f=Number(row.frame);if(!byFrame.has(f))byFrame.set(f,[]);byFrame.get(f).push(row);}
const availableFrames=(data.available_frames||[]).map(Number).sort((a,b)=>a-b);
let lastTargetFrame=null;
let suppressTrails=0;
let eventSource=null;
let streamComplete=false;
let streamMessageCount=0;
let streamOpenCount=0;
function enabled(id){return document.getElementById(id)?.checked;}
function frameFromVideoTime(timeSec){const fps=Number(data.config.fps)||30;const raw=Math.round(Math.max(0,timeSec||0)*fps);const end=Number(data.config.end_frame)||raw;return Math.min(raw,end);}
function frameNow(){return frameFromVideoTime(video.currentTime||0);}
function resolveOverlayFrame(targetFrame){if(byFrame.has(targetFrame))return{target_frame:targetFrame,resolved_frame:targetFrame,status:'exact',frame_gap:0};let previous=null;let future=null;for(const frame of availableFrames){if(frame<=targetFrame)previous=frame;if(frame>targetFrame){future=frame;break;}}const maxGap=Number(data.sync?.max_frame_gap||0)||Number.MAX_SAFE_INTEGER;if(previous!==null&&targetFrame-previous<=maxGap)return{target_frame:targetFrame,resolved_frame:previous,status:'previous',frame_gap:targetFrame-previous};if(future!==null&&future-targetFrame<=maxGap)return{target_frame:targetFrame,resolved_frame:future,status:'future',frame_gap:future-targetFrame};return{target_frame:targetFrame,resolved_frame:null,status:'missing',frame_gap:null};}
function resizeCanvas(){const rect=video.getBoundingClientRect();const fallbackW=data.config.width||960;const fallbackH=data.config.height||540;canvas.width=Math.max(1,Math.round(rect.width||fallbackW));canvas.height=Math.max(1,Math.round(rect.height||fallbackH));}
function scaleX(x){return Number(x)*(canvas.width/(data.config.width||canvas.width));}
function scaleY(y){return Number(y)*(canvas.height/(data.config.height||canvas.height));}
function activeEvents(frame){return data.events.filter(e=>Number(e.start_frame)<=frame&&Number(e.end_frame)>=frame);}
function activeHighlights(frame){return data.highlights.filter(e=>Number(e.start_frame)<=frame&&Number(e.end_frame)>=frame);}
function draw(){resizeCanvas();ctx.clearRect(0,0,canvas.width,canvas.height);const target=frameNow();const resolved=resolveOverlayFrame(target);const frame=resolved.resolved_frame;const rows=frame===null?[]:(byFrame.get(frame)||[]);const events=activeEvents(target);const highlights=activeHighlights(target);if(lastTargetFrame!==null&&Math.abs(target-lastTargetFrame)>Number(data.sync?.jump_reset_threshold_frames||32))suppressTrails=2;lastTargetFrame=target;frameReadout.textContent=String(target);resolvedFrameReadout.textContent=frame===null?'sin datos':String(frame)+' ('+resolved.status+')';timeReadout.textContent=(video.currentTime||0).toFixed(3)+'s';durationReadout.textContent=Number.isFinite(video.duration)?video.duration.toFixed(3)+'s':Number(data.video_metadata?.configured_duration_sec||0).toFixed(3)+'s config';rateReadout.textContent=(video.playbackRate||1).toFixed(2)+'x';dataReadout.textContent=rows.length+' tracks | '+events.length+' eventos';syncState.textContent=resolved.status==='missing'?'missing_data':(resolved.status==='exact'?'replaying_cache':'stride_fallback');if(resolved.status==='missing')badge('sin datos para frame '+target,14,14,'#ff6b6b');if(enabled('layerTrails')&&suppressTrails<=0)drawTrails(frame===null?target:frame);else if(suppressTrails>0)suppressTrails-=1;if(enabled('layerTracks'))drawTracks(rows);if(enabled('layerBall'))drawBall(rows);if(enabled('layerEvents'))drawEvents(events);if(enabled('layerPossession'))drawPossession(events);if(enabled('layerHighlights'))drawHighlights(highlights);if(enabled('layerMinimap'))drawMinimap(rows);if(enabled('layerDebug'))drawDebug(target,rows,resolved);renderEventList(events,highlights);requestAnimationFrame(draw);}
function drawTracks(rows){for(const row of rows){if(row.class==='ball')continue;const x=scaleX(row.x),y=scaleY(row.y),w=scaleX(row.w),h=scaleY(row.h);ctx.strokeStyle=row.team==='blue'?'#48a6ff':(row.team==='red'?'#ff6b6b':'#64d47c');ctx.lineWidth=2;ctx.strokeRect(x,y,w,h);ctx.fillStyle=ctx.strokeStyle;ctx.beginPath();ctx.arc(scaleX(row.center_x),scaleY(row.center_y),3,0,Math.PI*2);ctx.fill();if(enabled('layerIds'))label(row.track_id,x,y-6,ctx.strokeStyle);}}
function drawBall(rows){for(const row of rows.filter(r=>r.class==='ball')){const x=scaleX(row.center_x),y=scaleY(row.center_y);ctx.fillStyle='#f4c430';ctx.strokeStyle='#10130f';ctx.lineWidth=3;ctx.beginPath();ctx.arc(x,y,8,0,Math.PI*2);ctx.fill();ctx.stroke();if(enabled('layerIds'))label(row.track_id,x+10,y,'#f4c430');}}
function drawTrails(frame){const start=frame-(data.config.trail_length||16);const trails=new Map();for(const row of data.tracks){const f=Number(row.frame);if(f<start||f>frame)continue;if(!trails.has(row.track_id))trails.set(row.track_id,[]);trails.get(row.track_id).push(row);}for(const points of trails.values()){if(points.length<2)continue;ctx.beginPath();points.forEach((p,i)=>{const x=scaleX(p.center_x),y=scaleY(p.center_y);if(i===0)ctx.moveTo(x,y);else ctx.lineTo(x,y);});ctx.strokeStyle='rgba(244,196,48,.42)';ctx.lineWidth=2;ctx.stroke();}}
function drawEvents(events){let top=14;for(const event of events){const text=event.label+' '+event.status;badge(text,14,top,'#f4c430');top+=30;}}
function drawPossession(events){const possession=events.find(e=>(e.label||'').includes('possession')||(e.reason||'').includes('posesion'));if(!possession)return;badge('posesion candidata: '+(possession.team||'unknown'),14,canvas.height-42,'#64d47c');}
function drawHighlights(highlights){for(const hl of highlights){badge('highlight #'+hl.rank+' '+Number(hl.score).toFixed(1),canvas.width-190,14,'#ff6b6b');}}
function drawMinimap(rows){const w=150,h=96,x=canvas.width-w-14,y=canvas.height-h-14;ctx.fillStyle='rgba(13,16,13,.86)';ctx.fillRect(x,y,w,h);ctx.strokeStyle='#aab6a4';ctx.strokeRect(x,y,w,h);ctx.strokeStyle='rgba(170,182,164,.3)';ctx.beginPath();ctx.moveTo(x+w/2,y);ctx.lineTo(x+w/2,y+h);ctx.stroke();for(const row of rows){if(row.x_norm===''||row.y_norm==='')continue;ctx.fillStyle=row.class==='ball'?'#f4c430':(row.team==='blue'?'#48a6ff':'#64d47c');ctx.beginPath();ctx.arc(x+Number(row.x_norm)*w,y+Number(row.y_norm)*h,row.class==='ball'?4:3,0,Math.PI*2);ctx.fill();}}
function drawDebug(frame,rows,resolved){label('fps='+data.config.fps+' rows='+rows.length+' target='+frame+' resolved='+(resolved.resolved_frame??'none')+' status='+resolved.status,12,canvas.height-12,'#edf2e9');}
function label(text,x,y,color){ctx.font='12px system-ui';ctx.fillStyle='rgba(5,6,5,.78)';const width=ctx.measureText(text).width+8;ctx.fillRect(x,y-13,width,17);ctx.fillStyle=color;ctx.fillText(text,x+4,y);}
function badge(text,x,y,color){ctx.font='13px system-ui';const width=Math.min(canvas.width-24,ctx.measureText(text).width+18);ctx.fillStyle='rgba(5,6,5,.82)';ctx.fillRect(x,y,width,24);ctx.strokeStyle=color;ctx.strokeRect(x,y,width,24);ctx.fillStyle='#edf2e9';ctx.fillText(text,x+8,y+16);}
function renderEventList(events,highlights){const list=document.getElementById('eventList');list.innerHTML='';for(const item of [...events,...highlights].slice(0,6)){const div=document.createElement('div');div.className='event';div.innerHTML='<strong>'+escapeHtml(item.label||item.highlight_id)+'</strong><br>frames '+(item.start_frame||item.start_frame)+'-'+(item.end_frame||item.end_frame)+' | '+(item.status||'provisional');list.appendChild(div);}}
function connectEventStream(){if(!data.endpoints?.stream||!window.EventSource){streamReadout.textContent='sse no disponible';appendStreamMessage({type:'warning',warning_code:'eventsource_unavailable',message:'EventSource no disponible en este navegador'});return;}streamOpenCount+=1;streamReadout.textContent=streamOpenCount===1?'sse conectando':'sse reconectando '+streamOpenCount;eventSource=new EventSource(data.endpoints.stream);eventSource.onopen=()=>{streamReadout.textContent='sse activo';};for(const type of ['session_status','frame_result','event_update','latency_metrics','warning']){eventSource.addEventListener(type,event=>handleStreamMessage(type,event.data));}eventSource.onerror=()=>{if(streamComplete){eventSource.close();return;}streamReadout.textContent='sse reconexion pendiente';};}
function handleStreamMessage(type,raw){let message;try{message=JSON.parse(raw);}catch(error){message={type:'warning',warning_code:'bad_stream_payload',message:String(error)};}streamMessageCount+=1;streamMessageReadout.textContent=String(streamMessageCount);if(type==='latency_metrics'){latencyReadout.textContent=Number(message.emit_latency_ms||0).toFixed(1)+'ms';}if(type==='frame_result'){streamReadout.textContent='frame '+message.frame;}if(type==='warning'){streamReadout.textContent='warning '+(message.warning_code||'stream');}if(type==='session_status'&&message.status==='complete'){streamComplete=true;streamReadout.textContent='sse completo';if(eventSource)eventSource.close();}appendStreamMessage(message);}
function appendStreamMessage(message){if(!streamList)return;const div=document.createElement('div');div.className='event stream-event';const type=message.type||'message';const frame=message.frame!==undefined?'frame '+message.frame:'seq '+(message.sequence||'-');const detail=message.status||message.warning_code||message.label||message.resolution_status||message.source||'';div.innerHTML='<strong>'+escapeHtml(type)+'</strong><br>'+escapeHtml(frame)+' | '+escapeHtml(detail);streamList.prepend(div);while(streamList.children.length>8)streamList.removeChild(streamList.lastElementChild);}
function escapeHtml(text){return String(text).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',\"'\":'&#39;'}[c]));}
function markTemporalJump(){suppressTrails=2;resizeCanvas();}
if(!data.config.video_exists){missing.hidden=false;}
video.addEventListener('loadedmetadata',()=>{resizeCanvas();durationReadout.textContent=Number.isFinite(video.duration)?video.duration.toFixed(3)+'s':durationReadout.textContent;});
video.addEventListener('seeking',markTemporalJump);
video.addEventListener('seeked',markTemporalJump);
video.addEventListener('ratechange',()=>{rateReadout.textContent=(video.playbackRate||1).toFixed(2)+'x';});
video.addEventListener('play',()=>{syncState.textContent='playing';});
video.addEventListener('pause',()=>{syncState.textContent='paused';});
video.addEventListener('ended',()=>{syncState.textContent='ended';suppressTrails=2;});
window.addEventListener('resize',resizeCanvas);
for(const input of document.querySelectorAll('input[type=checkbox]'))input.addEventListener('change',()=>{suppressTrails=1;});
connectEventStream();
requestAnimationFrame(draw);
"""


def _tracks_by_frame(tracks: list[dict[str, Any]]) -> dict[int, list[dict[str, Any]]]:
    by_frame: dict[int, list[dict[str, Any]]] = {}
    for row in tracks:
        frame = _coerce_int(row.get("frame"), 0)
        by_frame.setdefault(frame, []).append(row)
    return by_frame


def _active_events_for_frame(events: list[dict[str, Any]], frame: int) -> list[dict[str, Any]]:
    active = []
    for event in events:
        start = _coerce_int(event.get("start_frame", event.get("frame_start", 0)), 0)
        end = _coerce_int(event.get("end_frame", event.get("frame_end", start)), start)
        if start <= frame <= end:
            active.append(event)
    return active


def _event_update_payload(event: dict[str, Any], source_type: str) -> dict[str, Any]:
    start = _coerce_int(event.get("start_frame", event.get("frame_start", 0)), 0)
    end = _coerce_int(event.get("end_frame", event.get("frame_end", start)), start)
    return {
        "source_type": source_type,
        "event_id": str(event.get("event_id", event.get("highlight_id", ""))),
        "label": str(event.get("label", event.get("event_type", event.get("highlight_id", source_type)))),
        "status": str(event.get("status", event.get("reliability", "provisional"))),
        "team": str(event.get("team", "")),
        "start_frame": start,
        "end_frame": end,
        "timestamp_sec": round(float(event.get("time_start_sec", timestamp_from_frame(start, 30.0)) or 0.0), 6),
        "confidence": event.get("confidence", ""),
        "update_kind": "provisional_window",
    }


def _average_metric(messages: list[dict[str, Any]], key: str) -> float:
    values = [float(message[key]) for message in messages if message.get(key) not in {"", None}]
    if not values:
        return 0.0
    return round(sum(values) / len(values), 6)


def _max_metric(messages: list[dict[str, Any]], key: str) -> float:
    values = [float(message[key]) for message in messages if message.get(key) not in {"", None}]
    return round(max(values), 6) if values else 0.0


def _coerce_int(value: Any, default: int) -> int:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


def _first(params: dict[str, list[str]], key: str, default: str) -> str:
    values = params.get(key)
    if not values:
        return default
    return values[0]


def _esc(value: Any) -> str:
    return html.escape(str(value), quote=True)
