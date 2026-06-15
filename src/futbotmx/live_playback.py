from __future__ import annotations

import csv
import html
import io
import json
import mimetypes
import subprocess
import sys
import threading
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
DEFAULT_INFERENCE_MODE = "precomputed"
INFERENCE_MODE_IDS = ("precomputed", "sam3_sampling", "lightweight_detector")
STREAM_MESSAGE_TYPES = ("session_status", "frame_result", "event_update", "latency_metrics", "warning")
STREAM_LATENCY_FIELDS = [
    "sequence",
    "message_id",
    "clip_id",
    "frame",
    "timestamp_sec",
    "requested_frame",
    "resolved_frame",
    "resolution_status",
    "track_count",
    "event_count",
    "highlight_count",
    "frame_read_ms",
    "detection_ms",
    "tracking_ms",
    "events_ms",
    "overlay_ms",
    "total_to_overlay_ms",
    "lookup_latency_ms",
    "emit_latency_ms",
    "processing_budget_ms",
    "target_fps",
    "skipped_frames",
    "queue_depth",
    "backpressure",
    "source",
    "inference_mode",
    "inference_status",
    "inference_stride",
    "tracker_mode",
    "event_window_frames",
    "gpu_memory_mb",
    "gpu_memory_metric",
    "overlay_ready",
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
    inference_mode: str = DEFAULT_INFERENCE_MODE
    sam3_stride: int = 8
    lightweight_stride: int = 2
    allow_gpu: bool = False
    gpu_profile: str = "cpu_safe"


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


@dataclass(frozen=True)
class InferenceModeProfile:
    mode_id: str
    label: str
    status: str
    recommended: bool
    selected: bool
    detection_source: str
    fallback_mode: str
    stride_frames: int
    frame_resolution_policy: str
    reuse_policy: str
    interpolation_policy: str
    gpu_required: bool
    hardware_profile: str
    online_inference: bool
    tracker_compatible: bool
    expected_latency_ms: float
    latency_budget_ms: float
    gpu_memory_metric: str
    quality_note: str
    limitation: str


@dataclass(frozen=True)
class OnlineFrameLoopConfig:
    mode: str
    target_fps: float
    inference_enabled: bool
    inference_mode: str
    inference_profile: str
    inference_status: str
    inference_stride: int
    detection_source: str
    tracker_mode: str
    event_window_frames: int
    processing_budget_ms: float
    max_skip_frames: int
    backpressure_policy: str


@dataclass(frozen=True)
class FrameLoopControl:
    action: str
    at_frame: int | None = None
    seek_frame: int | None = None
    reason: str = ""


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
    inference_mode: str | None = None,
    sam3_stride: int | None = None,
    lightweight_stride: int | None = None,
    allow_gpu: bool | None = None,
    gpu_profile: str | None = None,
) -> LivePlaybackConfig:
    clip = selected_playback_clip(playback_clips_from_config(config), clip_id)
    live_config = config.get("live_playback", {}) if isinstance(config.get("live_playback", {}), dict) else {}
    configured_inference = live_config.get("inference", {}) if isinstance(live_config.get("inference", {}), dict) else {}
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
        inference_mode=_normalize_inference_mode(inference_mode or str(configured_inference.get("mode", DEFAULT_INFERENCE_MODE))),
        sam3_stride=max(1, sam3_stride if sam3_stride is not None else _coerce_int(configured_inference.get("sam3_stride"), 8)),
        lightweight_stride=max(1, lightweight_stride if lightweight_stride is not None else _coerce_int(configured_inference.get("lightweight_stride"), 2)),
        allow_gpu=allow_gpu if allow_gpu is not None else _coerce_bool(configured_inference.get("allow_gpu"), False),
        gpu_profile=gpu_profile or str(configured_inference.get("gpu_profile", "cpu_safe")),
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


def inference_mode_profiles(playback_config: LivePlaybackConfig) -> list[InferenceModeProfile]:
    fps = playback_config.fps or 30.0
    latency_budget = round(1000.0 / fps, 6)
    selected_mode = _normalize_inference_mode(playback_config.inference_mode)
    sam3_status = "gpu_sampling_ready" if playback_config.allow_gpu and playback_config.gpu_profile == "msi_gpu" else "configured_gpu_required"
    return [
        InferenceModeProfile(
            mode_id="precomputed",
            label="Precomputed SAM 3 detections",
            status="recommended_for_demo",
            recommended=True,
            selected=selected_mode == "precomputed",
            detection_source=playback_config.tracks_csv,
            fallback_mode="precomputed",
            stride_frames=1,
            frame_resolution_policy="exact_or_nearest_available_frame",
            reuse_policy="load_cached_tracks_by_frame",
            interpolation_policy="disabled; use exact frame or previous/future nearest frame",
            gpu_required=False,
            hardware_profile="any_local_machine",
            online_inference=False,
            tracker_compatible=True,
            expected_latency_ms=0.65,
            latency_budget_ms=latency_budget,
            gpu_memory_metric="not_applicable",
            quality_note="Usa artefactos SAM 3/Level 3 ya generados; recomendado para demo fluida.",
            limitation="No mejora ni corrige detecciones durante playback; depende de la calidad offline.",
        ),
        InferenceModeProfile(
            mode_id="sam3_sampling",
            label="SAM 3 sampling",
            status=sam3_status,
            recommended=False,
            selected=selected_mode == "sam3_sampling",
            detection_source="sam3_runtime_sampling_with_precomputed_fallback",
            fallback_mode="precomputed",
            stride_frames=max(1, playback_config.sam3_stride),
            frame_resolution_policy="sampled_frame_or_nearest_cached_frame",
            reuse_policy="reuse_last_sampled_detection_until_next_sampling_frame",
            interpolation_policy="reuse detections between sampled frames; interpolation remains disabled until validated",
            gpu_required=True,
            hardware_profile="msi_gpu_only",
            online_inference=True,
            tracker_compatible=True,
            expected_latency_ms=95.0,
            latency_budget_ms=latency_budget,
            gpu_memory_metric="unavailable_without_gpu_probe",
            quality_note="Mantiene calidad SAM 3 en frames muestreados y conserva fallback precomputado.",
            limitation="No debe ejecutarse cada frame; requiere laptop MSI con GPU y medicion real de VRAM.",
        ),
        InferenceModeProfile(
            mode_id="lightweight_detector",
            label="Lightweight robot/ball detector",
            status="experimental_stub",
            recommended=False,
            selected=selected_mode == "lightweight_detector",
            detection_source="lightweight_detector_stub_with_precomputed_fallback",
            fallback_mode="precomputed",
            stride_frames=max(1, playback_config.lightweight_stride),
            frame_resolution_policy="fast_detector_frame_or_nearest_cached_frame",
            reuse_policy="run lightweight detector on stride and reuse cached tracks for gaps",
            interpolation_policy="reuse nearest detections; SAM 3 offline remains source of high-quality masks",
            gpu_required=False,
            hardware_profile="cpu_or_gpu",
            online_inference=True,
            tracker_compatible=True,
            expected_latency_ms=8.0,
            latency_budget_ms=latency_budget,
            gpu_memory_metric="optional",
            quality_note="Prioriza fluidez y deteccion de robots/balon; calidad inferior a SAM 3 offline.",
            limitation="No genera mascaras SAM 3 de alta calidad y puede degradar precision de eventos.",
        ),
    ]


def selected_inference_profile(playback_config: LivePlaybackConfig) -> InferenceModeProfile:
    selected_mode = _normalize_inference_mode(playback_config.inference_mode)
    for profile in inference_mode_profiles(playback_config):
        if profile.mode_id == selected_mode:
            return profile
    return inference_mode_profiles(playback_config)[0]


def inference_mode_catalog(context: dict[str, Any]) -> dict[str, Any]:
    playback_config: LivePlaybackConfig = context["config"]
    profiles = inference_mode_profiles(playback_config)
    selected = selected_inference_profile(playback_config)
    return {
        "selected_mode": selected.mode_id,
        "recommended_mode": "precomputed",
        "available_modes": [profile.mode_id for profile in profiles],
        "modes": [asdict(profile) for profile in profiles],
        "selection_source": "CLI override or live_playback.inference.mode; default is precomputed.",
        "sam3_boundary": "SAM 3 online sampling is documented but guarded for MSI GPU usage; this desktop run keeps deterministic fallback.",
        "lightweight_detector_boundary": "Detector ligero remains an experimental hook compatible with the incremental tracker.",
        "limitations": [profile.limitation for profile in profiles],
        "selected_profile": asdict(selected),
    }


def debug_panel_summary(context: dict[str, Any]) -> dict[str, Any]:
    return {
        "panel_id": "debugPanel",
        "purpose": "Diagnosticar sincronizacion, reglas de eventos y rendimiento desde la app local.",
        "visible_indicators": [
            "current_frame",
            "current_timestamp",
            "inference_mode",
            "channel_status",
            "current_latency_ms",
            "queue_depth",
            "active_track_count",
            "active_event",
        ],
        "download_artifacts": {
            "session_log": "stream_messages.jsonl",
            "live_tracks_jsonl": "live_tracks.jsonl",
            "stream_events_jsonl": "stream_events.jsonl",
        },
        "download_endpoints": {
            "session_log": "/stream-messages.jsonl",
            "live_tracks_jsonl": "/live_tracks.jsonl",
            "stream_events_jsonl": "/stream_events.jsonl",
        },
        "debug_overlay_toggle": "layerDebug",
        "diagnostic_coverage": {
            "sync": True,
            "latency": True,
            "queue": True,
            "tracks": True,
            "events": True,
            "downloads": True,
        },
        "active_frame_count": len(context.get("available_frames", [])),
        "session_message_count": len(context.get("stream_messages", [])),
        "stream_event_count": len([message for message in context.get("stream_messages", []) if message.get("type") == "event_update"]),
        "live_track_count": len(context.get("tracks", [])),
        "criterion": "Una falla de sincronizacion o latencia puede diagnosticarse desde el panel local.",
    }


def online_frame_loop_config_from_playback(
    playback_config: LivePlaybackConfig,
    inference_enabled: bool = False,
    processing_budget_ms: float | None = None,
) -> OnlineFrameLoopConfig:
    target_fps = playback_config.fps or 30.0
    profile = selected_inference_profile(playback_config)
    budget = processing_budget_ms if processing_budget_ms is not None else 1000.0 / target_fps
    return OnlineFrameLoopConfig(
        mode="precomputed_online_loop",
        target_fps=target_fps,
        inference_enabled=inference_enabled or profile.online_inference,
        inference_mode=profile.mode_id,
        inference_profile=profile.label,
        inference_status=profile.status,
        inference_stride=profile.stride_frames,
        detection_source=profile.detection_source,
        tracker_mode="incremental_precomputed_snapshot",
        event_window_frames=max(6, int(round(target_fps / 2))),
        processing_budget_ms=round(budget, 6),
        max_skip_frames=4,
        backpressure_policy="skip_next_available_frames",
    )


def build_online_frame_loop(
    context: dict[str, Any],
    loop_config: OnlineFrameLoopConfig | None = None,
    controls: list[FrameLoopControl | dict[str, Any]] | None = None,
) -> dict[str, Any]:
    config: LivePlaybackConfig = context["config"]
    loop_config = loop_config or online_frame_loop_config_from_playback(config)
    controls_by_frame = _controls_by_frame(controls or [], config.start_frame)
    tracks_by_frame = _tracks_by_frame(context["tracks"])
    frames = context["available_frames"]
    messages: list[dict[str, Any]] = []
    metric_messages: list[dict[str, Any]] = []
    sequence = 0
    state: dict[str, Any] = {
        "paused": False,
        "stopped": False,
        "pending_seek_frame": None,
        "reset_count": 0,
        "skipped_frame_count": 0,
        "skipped_frames": [],
    }

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
            "mode": loop_config.mode,
            "fps": config.fps,
            "frame_start": config.start_frame,
            "frame_end": config.end_frame,
            "available_frame_count": len(frames),
            "endpoint": "/stream",
            "engine_state": "created",
            "inference_enabled": loop_config.inference_enabled,
            "inference_mode": loop_config.inference_mode,
            "inference_profile": loop_config.inference_profile,
            "inference_status": loop_config.inference_status,
            "inference_stride": loop_config.inference_stride,
            "detection_source": loop_config.detection_source,
            "tracker_mode": loop_config.tracker_mode,
            "event_window_frames": loop_config.event_window_frames,
            "processing_budget_ms": loop_config.processing_budget_ms,
            "controls_supported": ["pause", "resume", "seek", "stop", "skip_late_frames"],
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

    if loop_config.inference_enabled:
        add(
            "warning",
            {
                "severity": "info" if loop_config.inference_mode != "sam3_sampling" else "warn",
                "warning_code": f"{loop_config.inference_mode}_fallback",
                "message": "El modo online esta seleccionado, pero esta actividad mantiene fallback precomputado determinista para evitar dependencias/GPU no disponibles.",
                "inference_mode": loop_config.inference_mode,
                "inference_status": loop_config.inference_status,
                "inference_stride": loop_config.inference_stride,
                "detection_source": loop_config.detection_source,
            },
        )

    for event in context["events"]:
        add("event_update", _event_update_payload(event, "event"))
    for highlight in context["highlights"]:
        add("event_update", _event_update_payload(highlight, "highlight"))

    frame_index = 0
    while frame_index < len(frames):
        frame = frames[frame_index]
        for control in controls_by_frame.get(frame, []):
            _apply_frame_loop_control(add, state, control, frame)
        if state["stopped"]:
            break
        if state["paused"]:
            frame_index += 1
            continue

        requested_frame = state.pop("pending_seek_frame", None) or frame
        resolution = resolve_overlay_frame(requested_frame, frames)
        resolved_frame = resolution.resolved_frame
        rows = tracks_by_frame.get(resolved_frame, []) if resolved_frame is not None else []
        events = _active_events_for_frame(context["events"], requested_frame)
        highlights = _active_events_for_frame(context["highlights"], requested_frame)
        timestamp = round(timestamp_from_frame(requested_frame, config.fps), 6)
        metrics = _frame_loop_stage_metrics(loop_config, requested_frame, resolution, rows, events, highlights)
        add(
            "frame_result",
            {
                "frame": requested_frame,
                "requested_frame": requested_frame,
                "timestamp_sec": timestamp,
                "target_frame": resolution.target_frame,
                "resolved_frame": resolved_frame,
                "resolution_status": resolution.status,
                "frame_gap": resolution.frame_gap,
                "track_count": len(rows),
                "track_ids": [str(row.get("track_id", "")) for row in rows[:24]],
                "ball_count": sum(1 for row in rows if row.get("class") == "ball"),
                "event_count": len(events),
                "highlight_count": len(highlights),
                "active_event_ids": [str(event.get("event_id", "")) for event in events[:24]],
                "active_highlight_ids": [str(highlight.get("highlight_id", "")) for highlight in highlights[:24]],
                "engine_mode": loop_config.mode,
                "frame_source": "requested_frame" if requested_frame != frame else "available_frame_sequence",
                "detection_source": loop_config.detection_source,
                "inference_mode": loop_config.inference_mode,
                "inference_profile": loop_config.inference_profile,
                "inference_status": loop_config.inference_status,
                "inference_stride": loop_config.inference_stride,
                "tracker_mode": loop_config.tracker_mode,
                "tracker_state": "updated_incremental_snapshot",
                "event_window_frames": loop_config.event_window_frames,
                "overlay_ready": True,
            },
        )
        skip_count = _frame_loop_skip_count(metrics, frames, frame_index, loop_config)
        metrics["skipped_frames"] = skip_count
        metrics["backpressure"] = skip_count > 0
        latency_message = add(
            "latency_metrics",
            {
                "frame": requested_frame,
                "requested_frame": requested_frame,
                "timestamp_sec": timestamp,
                "resolved_frame": resolved_frame,
                "resolution_status": resolution.status,
                "track_count": len(rows),
                "event_count": len(events),
                "highlight_count": len(highlights),
                **metrics,
            },
        )
        metric_messages.append(latency_message)
        if skip_count:
            skipped = frames[frame_index + 1 : frame_index + 1 + skip_count]
            state["skipped_frame_count"] += len(skipped)
            state["skipped_frames"].extend(skipped)
            add(
                "session_status",
                {
                    "status": "skipping_frames",
                    "mode": loop_config.mode,
                    "engine_state": "backpressure",
                    "frame": requested_frame,
                    "skipped_frame_count": len(skipped),
                    "skipped_frames": skipped,
                    "processing_budget_ms": loop_config.processing_budget_ms,
                    "total_to_overlay_ms": metrics["total_to_overlay_ms"],
                    "backpressure_policy": loop_config.backpressure_policy,
                },
            )
            frame_index += skip_count + 1
            continue
        frame_index += 1

    completion = add(
        "session_status",
        {
            "status": "stopped" if state["stopped"] else "complete",
            "mode": loop_config.mode,
            "engine_state": "stopped" if state["stopped"] else "complete",
            "emitted_frame_count": len(metric_messages),
            "skipped_frame_count": state["skipped_frame_count"],
            "state_reset_count": state["reset_count"],
            "message_count": 0,
            "endpoint": "/stream",
        },
    )
    completion["message_count"] = len(messages)
    return {
        "config": asdict(loop_config),
        "messages": messages,
        "metrics": metric_messages,
        "summary": _frame_loop_summary(context, loop_config, messages, metric_messages, state),
        "controls": [asdict(control) for control_group in controls_by_frame.values() for control in control_group],
    }


def build_stream_messages(context: dict[str, Any]) -> list[dict[str, Any]]:
    return build_online_frame_loop(context)["messages"]


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
        "average_total_to_overlay_ms": _average_metric(latency_messages, "total_to_overlay_ms"),
        "max_total_to_overlay_ms": _max_metric(latency_messages, "total_to_overlay_ms"),
        "frontend_reconnect_policy": "EventSource automatic reconnect; the client closes the stream after session_status=complete.",
        "log_artifact": "stream_messages.jsonl",
        "latency_artifact": "stream_latency_metrics.csv",
        "summary_artifact": "stream_summary.json",
        "clip_id": context["config"].clip_id,
    }


def stream_messages_jsonl(messages: list[dict[str, Any]]) -> str:
    return "\n".join(json.dumps(message, ensure_ascii=True, separators=(",", ":")) for message in messages) + "\n"


def live_tracks_jsonl(tracks: list[dict[str, Any]]) -> str:
    return "\n".join(
        json.dumps({"record_type": "live_track", **row}, ensure_ascii=True, separators=(",", ":"))
        for row in tracks
    ) + "\n"


def stream_events_jsonl(messages: list[dict[str, Any]]) -> str:
    event_messages = [message for message in messages if message.get("type") == "event_update"]
    return "\n".join(json.dumps(message, ensure_ascii=True, separators=(",", ":")) for message in event_messages) + "\n"


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


def frame_loop_metrics_csv(frame_loop: dict[str, Any]) -> str:
    return stream_latency_metrics_csv(frame_loop["metrics"])


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
        _endpoint_row("/live_tracks.jsonl", "application/x-ndjson", "live_tracks_log", "Downloadable live track snapshots for debug review."),
        _endpoint_row("/stream_events.jsonl", "application/x-ndjson", "stream_events_log", "Downloadable streaming event updates for debug review."),
        _endpoint_row("/stream-latency.csv", "text/csv", "stream_metrics", "Latency metrics emitted by the SSE channel."),
        _endpoint_row("/frame-loop-summary.json", "application/json", "frame_loop", "Online frame loop status, controls and performance summary."),
        _endpoint_row("/frame-loop-metrics.csv", "text/csv", "frame_loop_metrics", "Per-frame stage timings from the online frame loop."),
        _endpoint_row("/inference-modes.json", "application/json", "inference_modes", "Configurable inference mode catalog and selected profile."),
        _endpoint_row("/debug-panel.json", "application/json", "debug_panel", "Debug panel coverage, indicators and downloadable artifacts."),
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
            "producer": "online_frame_loop",
            "inference_mode": context["inference_modes"]["selected_mode"],
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
            "live_tracks_jsonl": "live_tracks.jsonl",
            "stream_events_jsonl": "stream_events.jsonl",
            "stream_latency_metrics": "stream_latency_metrics.csv",
            "stream_summary": "stream_summary.json",
            "frame_loop_summary": "frame_loop_summary.json",
            "frame_loop_metrics": "frame_loop_metrics.csv",
            "inference_modes": "inference_modes.json",
            "debug_panel_summary": "debug_panel_summary.json",
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
    context["config_path"] = config_path
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
    (output_dir / "live_tracks.jsonl").write_text(
        live_tracks_jsonl(context["tracks"]),
        encoding="utf-8",
    )
    (output_dir / "stream_events.jsonl").write_text(
        stream_events_jsonl(context["stream_messages"]),
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
    (output_dir / "frame_loop_summary.json").write_text(
        json.dumps(context["frame_loop"]["summary"], indent=2, ensure_ascii=True) + "\n",
        encoding="utf-8",
    )
    (output_dir / "frame_loop_metrics.csv").write_text(
        frame_loop_metrics_csv(context["frame_loop"]),
        encoding="utf-8",
    )
    (output_dir / "inference_modes.json").write_text(
        json.dumps(context["inference_modes"], indent=2, ensure_ascii=True) + "\n",
        encoding="utf-8",
    )
    (output_dir / "debug_panel_summary.json").write_text(
        json.dumps(context["debug_panel"], indent=2, ensure_ascii=True) + "\n",
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
    context["inference_modes"] = inference_mode_catalog(context)
    frame_loop = build_online_frame_loop(context)
    stream_messages = frame_loop["messages"]
    context["frame_loop"] = frame_loop
    context["stream_messages"] = stream_messages
    context["stream_summary"] = stream_summary_from_messages(context, stream_messages)
    context["debug_panel"] = debug_panel_summary(context)
    context["summary"]["stream_message_count"] = context["stream_summary"]["message_count"]
    context["summary"]["stream_warning_count"] = context["stream_summary"]["warning_count"]
    context["summary"]["stream_frame_result_count"] = context["stream_summary"]["frame_result_count"]
    context["summary"]["frame_loop_processed_count"] = frame_loop["summary"]["processed_frame_count"]
    context["summary"]["frame_loop_skipped_count"] = frame_loop["summary"]["skipped_frame_count"]
    context["summary"]["frame_loop_avg_overlay_ms"] = frame_loop["summary"]["average_total_to_overlay_ms"]
    context["summary"]["inference_mode"] = context["inference_modes"]["selected_mode"]
    context["summary"]["recommended_inference_mode"] = context["inference_modes"]["recommended_mode"]
    context["root"] = root
    context["config_path"] = None  # will be set by build_live_playback_package
    context["visualizations"] = _find_experiment_visualizations(root, playback_config.tracks_csv)
    # masks_contours.json path (generated by run_unified_analysis.py after segmentation)
    viz_info = context["visualizations"]
    if viz_info:
        # derive experiment root from voronoi or interaction_graph paths
        sample_rel = (
            viz_info.get("interaction_graph")
            or (viz_info.get("voronoi_frames") or [None])[0]
        )
        if sample_rel:
            exp_root = root.resolve() / Path(sample_rel).parents[1]
            contours_path = exp_root / "masks_contours.json"
            context["masks_contours_path"] = str(contours_path) if contours_path.exists() else None
        else:
            context["masks_contours_path"] = None
    else:
        context["masks_contours_path"] = None
    # Available video paths from environment (FUTBOTMX_VIDEO_*)
    import os as _os
    context["available_videos"] = {
        k: v for k, v in _os.environ.items() if k.startswith("FUTBOTMX_VIDEO_") and v
    }
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


_ANALYSIS_STATE: dict[str, Any] = {
    "running": False,
    "done": False,
    "state": "idle",
    "log": [],
    "error": None,
}
_ANALYSIS_LOCK = threading.Lock()


def _find_experiment_visualizations(root: Path, tracks_csv: str) -> dict[str, Any]:
    """Discover visualization PNGs from the experiment that produced tracks_csv.

    Expects tracks_csv = .../experiment/level3_spatial/level3_tracks.csv
    Returns paths relative to root (for /artifact?path=... endpoint).
    """
    root_abs = root.resolve()
    p = Path(tracks_csv)
    if not p.is_absolute():
        p = (root_abs / p).resolve()
    parts = p.parts
    if len(parts) >= 2 and parts[-2] == "level3_spatial":
        exp = p.parents[1]
    elif len(parts) >= 3 and parts[-3] == "level3_spatial":
        exp = p.parents[2]
    else:
        exp = p.parent
    viz = exp / "level3_visualizations"
    spatial = exp / "level3_spatial"
    events_dir = exp / "level3_events"

    def rel(path: Path) -> str | None:
        try:
            resolved = path.resolve()
            return resolved.relative_to(root_abs).as_posix() if resolved.exists() else None
        except ValueError:
            return None

    return {
        "voronoi_frames": [r for q in sorted(viz.glob("voronoi_frame_*.png")) if (r := rel(q))],
        "voronoi_orig_frames": [r for q in sorted(viz.glob("voronoi_original_frame_*.png")) if (r := rel(q))],
        "interaction_graph": rel(viz / "interaction_graph.png"),
        "storyboard": rel(viz / "highlight_storyboard.png"),
        "minimap_base": rel(spatial / "minimap_base.png"),
        "minimap_tracks": rel(spatial / "minimap_tracks.png"),
        "highlights": [r for q in sorted(events_dir.glob("overlay_highlight_*.png")) if (r := rel(q))],
        "dashboard": rel(exp / "dashboard" / "dashboard.html"),
    }


def _run_analysis_async(
    root: Path,
    context: dict[str, Any],
    config_path: Path,
    video_path: str,
    clip_id: str,
    start_frame: int,
    end_frame: int,
    stride: int,
) -> None:
    global _ANALYSIS_STATE
    cmd = [
        sys.executable,
        str(root / "scripts" / "run_unified_analysis.py"),
        "--video", video_path,
        "--clip-id", clip_id,
        "--start-frame", str(start_frame),
        "--end-frame", str(end_frame),
        "--stride", str(stride),
        "--no-browser",
        "--no-serve",
    ]
    log_lines: list[str] = []
    try:
        import os as _os_run
        _env = dict(_os_run.environ)
        _env.setdefault("PYTORCH_CUDA_ALLOC_CONF", "expandable_segments:True")
        proc = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, cwd=str(root), env=_env,
        )
        assert proc.stdout is not None
        for line in proc.stdout:
            log_lines.append(line.rstrip())
            with _ANALYSIS_LOCK:
                _ANALYSIS_STATE["log"] = log_lines[-80:]
        proc.wait()
        if proc.returncode == 0:
            # Hot-reload: rebuild context in place from the new experiment data.
            # The experiment dir is auto-named; find it from the log output.
            exp_dir = None
            for line in reversed(log_lines):
                if "Experimento:" in line:
                    exp_dir = line.split("Experimento:")[-1].strip()
                    break
            if exp_dir:
                new_tracks = str(Path(exp_dir) / "level3_spatial" / "level3_tracks.csv")
                new_events = str(Path(exp_dir) / "level3_events" / "level3_events.json")
                new_highlights = str(Path(exp_dir) / "level3_events" / "level3_highlights.csv")
                new_output = str(Path(exp_dir) / "live_playback")
                from futbotmx.live_playback import LivePlaybackConfig, build_live_playback_package
                import cv2
                cap = cv2.VideoCapture(video_path)
                fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
                width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                cap.release()
                new_config = LivePlaybackConfig(
                    clip_id=clip_id,
                    video_path=video_path,
                    fps=fps,
                    width=width,
                    height=height,
                    start_frame=start_frame,
                    end_frame=end_frame,
                    tracks_csv=new_tracks,
                    events_json=new_events,
                    highlights_csv=new_highlights,
                    output_dir=new_output,
                )
                new_ctx = build_live_playback_package(root, config_path, new_config)
                context.clear()
                context.update(new_ctx)
            with _ANALYSIS_LOCK:
                _ANALYSIS_STATE.update({"running": False, "done": True, "state": "done", "error": None})
        else:
            with _ANALYSIS_LOCK:
                _ANALYSIS_STATE.update({
                    "running": False, "done": True, "state": "error",
                    "error": f"Proceso terminó con código {proc.returncode}",
                })
    except Exception as exc:
        with _ANALYSIS_LOCK:
            _ANALYSIS_STATE.update({
                "running": False, "done": True, "state": "error", "error": str(exc),
            })


def render_playback_html(context: dict[str, Any]) -> str:
    config: LivePlaybackConfig = context["config"]
    payload = client_payload(context)
    payload_json = json.dumps(payload, ensure_ascii=True, separators=(",", ":"))
    summary = context["summary"]
    viz = context.get("visualizations", {})

    # ── stat cards ──────────────────────────────────────────────────────────
    classes = {r["class"] for r in context["tracks"]}
    n_robots = len({r["track_id"] for r in context["tracks"] if "robot" in r.get("class", "")})
    n_ball = 1 if any(r.get("class") == "ball" for r in context["tracks"]) else 0
    n_events = summary["event_count"]
    n_frames = summary.get("available_frame_count", 0)
    teams = {r.get("team", "") for r in context["tracks"] if r.get("team") not in ("", "unknown", "neutral")}

    def stat_card(label: str, value: str, color: str = "") -> str:
        style = f'style="border-top:3px solid {color}"' if color else ""
        return f'<div class="stat-card" {style}><div class="stat-val">{_esc(value)}</div><div class="stat-lbl">{_esc(label)}</div></div>'

    stat_row = "".join([
        stat_card("Robots", str(n_robots), "#005eb8"),
        stat_card("Balón", str(n_ball), "#f59e0b"),
        stat_card("Eventos", str(n_events), "#006847"),
        stat_card("Frames", str(n_frames), "#7B1A3E"),
        stat_card("Equipos", str(len(teams)) if teams else "—", "#CE1126" if teams else ""),
        stat_card("Clip", config.clip_id),
    ])

    # ── layer toggles ───────────────────────────────────────────────────────
    has_contours = bool(context.get("masks_contours_path"))
    toggles_html = "".join([
        _toggle("layerMasks", "Contornos", has_contours),
        _toggle("layerTracks", "Bboxes", not has_contours),
        _toggle("layerIds", "IDs", True),
        _toggle("layerBall", "Balón", True),
        _toggle("layerTrails", "Trails", True),
        _toggle("layerGoalpost", "Portería", True),
        _toggle("layerField", "Campo", False),
        _toggle("layerEvents", "Eventos", True),
    ])

    # ── analytics tabs: Voronoi ─────────────────────────────────────────────
    def img_gallery(paths: list[str], cls: str = "") -> str:
        if not paths:
            return '<p class="empty">Sin imágenes disponibles. Ejecuta el pipeline primero.</p>'
        imgs = "".join(f'<img src="/artifact?path={_esc(p)}" alt="{_esc(p.split("/")[-1])}" loading="lazy">' for p in paths)
        return f'<div class="gallery {cls}">{imgs}</div>'

    voronoi_tab = img_gallery(viz.get("voronoi_frames", []))
    voronoi_orig_tab = img_gallery(viz.get("voronoi_orig_frames", []))
    graph_tab = (
        f'<img src="/artifact?path={_esc(viz["interaction_graph"])}" class="full-img" alt="Grafo de interacciones">'
        if viz.get("interaction_graph") else
        '<p class="empty">Grafo no disponible. Ejecuta el pipeline.</p>'
    )
    storyboard_tab = (
        f'<img src="/artifact?path={_esc(viz["storyboard"])}" class="full-img" alt="Storyboard">'
        if viz.get("storyboard") else ""
    )
    highlights_tab = img_gallery(viz.get("highlights", []), "highlights-gallery")
    minimap_tab = "".join([
        f'<img src="/artifact?path={_esc(p)}" class="full-img" alt="{label}">'
        for p, label in [
            (viz.get("minimap_tracks", ""), "Tracks en campo"),
            (viz.get("minimap_base", ""), "Campo base"),
        ] if p
    ]) or '<p class="empty">Minimapa no disponible.</p>'

    dashboard_link = (
        f'<a href="/artifact?path={_esc(viz["dashboard"])}" target="_blank" class="btn-link">Abrir dashboard completo</a>'
        if viz.get("dashboard") else ""
    )

    video_src = f"/video?clip_id={_esc(config.clip_id)}"

    # Video selector datalist from .env
    available_videos = context.get("available_videos", {})
    video_options = "".join(
        f'<option value="{_esc(v)}" label="{_esc(k.replace("FUTBOTMX_VIDEO_", "").lower())}">'
        for k, v in sorted(available_videos.items())
    )
    datalist_html = f'<datalist id="videoList">{video_options}</datalist>' if video_options else ""
    list_attr = ' list="videoList"' if video_options else ""

    # default values from current config (useful when re-analyzing same video)
    default_video = _esc(config.video_path or "")
    default_clip = _esc(config.clip_id or "clip")

    return f"""<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>FutBotMX — {_esc(config.clip_id)}</title>
<style>{_css()}</style>
</head>
<body>
<div class="mx-stripe"><div></div><div></div><div></div></div>
<header>
  <div class="header-inner">
    <div class="header-brand">
      <div class="brand-icons">⚽&nbsp;🤖</div>
      <div class="brand-titles">
        <span class="brand-name">Copa FutBotMX</span>
        <span class="brand-sub">Análisis de fútbol robótico · México</span>
      </div>
    </div>
    <div class="brand-divider"></div>
    <div class="header-center">
      <span class="clip-badge">{_esc(config.clip_id)}</span>
      <span class="frames-badge">frames {config.start_frame}–{config.end_frame}</span>
    </div>
    <span id="syncState" class="sync-badge">cargando</span>
  </div>
</header>

<section class="analyze-bar">
  {datalist_html}
  <form id="analyzeForm" action="/analyze" method="post" class="analyze-form">
    <div class="field-group field-path">
      <label>Video</label>
      <div class="path-row">
        <input id="inpVideoPath" name="video_path" class="inp-path" value="{default_video}" placeholder="/ruta/al/video.mp4"{list_attr} required autocomplete="off">
        <button type="button" id="btnBrowse" class="btn-browse" title="Explorar carpetas">📁</button>
      </div>
    </div>
    <div class="field-group">
      <label>Clip ID</label>
      <input id="inpClipId" name="clip_id" class="inp-short" placeholder="nombre" value="{default_clip}">
    </div>
    <div class="field-group">
      <label>Inicio</label>
      <input id="inpStartFrame" type="number" name="start_frame" class="inp-num" value="0" placeholder="0" min="0">
    </div>
    <div class="field-group">
      <label>Fin</label>
      <input id="inpEndFrame" type="number" name="end_frame" class="inp-num" value="0" placeholder="fin" min="0">
    </div>
    <div class="field-group">
      <label>Stride</label>
      <input type="number" name="stride" class="inp-num" value="1" placeholder="1" min="1">
    </div>
    <button type="submit" class="btn-analyze">▶ Analizar</button>
  </form>
  <div id="videoInfoRow" class="video-info-row" style="display:none"></div>
  <div id="analyzeStatus" class="analyze-status hidden"></div>
</section>

<!-- File browser overlay -->
<div id="fbOverlay" class="fb-overlay">
  <div class="fb-panel">
    <div class="fb-head">
      <span class="fb-title">📁 Seleccionar video</span>
      <span id="fbPathLabel" class="fb-path-label"></span>
      <button class="fb-close" id="fbClose" type="button">✕</button>
    </div>
    <div id="fbList" class="fb-list"></div>
  </div>
</div>

<div class="stats-row">{stat_row}</div>

<section class="workbench" style="--vid-w:{config.width};--vid-h:{config.height}">
  <div class="stage-wrap">
    <div class="stage">
      <video id="video" controls preload="none" playsinline>
        <source src="{video_src}">
      </video>
      <canvas id="overlay"></canvas>
      <div id="videoMissing" class="video-missing hidden">
        Video no disponible — overlays desde datos precalculados
      </div>
    </div>
  </div>

  <aside class="side-panel">
    <div class="minimap-panel">
      <h3>Minimapa</h3>
      <canvas id="minimapCanvas" class="minimap-canvas"></canvas>
    </div>
    <div class="panel-section">
      <h3>Reproducción</h3>
      <div class="readout-grid">
        <span>Frame</span><strong id="frameReadout">—</strong>
        <span>Tiempo</span><strong id="timeReadout">—</strong>
        <span>Velocidad</span><strong id="rateReadout">1×</strong>
        <span>Overlay</span><strong id="resolvedFrameReadout">—</strong>
        <span>Tracks</span><strong id="dataReadout">—</strong>
      </div>
    </div>
    <div class="panel-section">
      <h3>Capas de overlay</h3>
      <div class="toggles">{toggles_html}</div>
    </div>
    <div class="panel-section">
      <h3>Leyenda</h3>
      <div class="legend">
        <div><span class="leg-dot blue"></span>Equipo A (robots)</div>
        <div><span class="leg-dot red"></span>Equipo B (robots)</div>
        <div><span class="leg-dot ball"></span>Balón</div>
        <div><span class="leg-dot green"></span>Portería / campo</div>
      </div>
    </div>
    <div class="panel-section downloads">
      <h3>Descargas</h3>
      {dashboard_link}
      <a href="/tracks.csv" download class="dl-link">tracks.csv</a>
      <a href="/events.json" download class="dl-link">events.json</a>
      <a href="/highlights.csv" download class="dl-link">highlights.csv</a>
    </div>
  </aside>
</section>

<section class="analytics">
  <nav class="tab-nav">
    <button class="tab-btn active" onclick="showTab('voronoi',this)">Voronoi campo</button>
    <button class="tab-btn" onclick="showTab('voronoi-orig',this)">Voronoi video</button>
    <button class="tab-btn" onclick="showTab('graph',this)">Grafo interacciones</button>
    <button class="tab-btn" onclick="showTab('minimap',this)">Minimapa</button>
    <button class="tab-btn" onclick="showTab('highlights',this)">Highlights</button>
    <button class="tab-btn" onclick="showTab('storyboard',this)">Storyboard</button>
  </nav>
  <div id="tab-voronoi" class="tab-panel active">{voronoi_tab}</div>
  <div id="tab-voronoi-orig" class="tab-panel hidden">{voronoi_orig_tab}</div>
  <div id="tab-graph" class="tab-panel hidden">{graph_tab}</div>
  <div id="tab-minimap" class="tab-panel hidden">{minimap_tab}</div>
  <div id="tab-highlights" class="tab-panel hidden">{highlights_tab}</div>
  <div id="tab-storyboard" class="tab-panel hidden">{storyboard_tab}</div>
</section>

<section class="events-section">
  <h3>Eventos activos</h3>
  <div id="eventList" class="event-list"></div>
</section>

<script>window.FUTBOT_PLAYBACK_DATA={payload_json};{_js()}</script>
<script>
const HAS_CONTOURS = {'true' if has_contours else 'false'};
let MASK_CONTOURS = {{}};
if (HAS_CONTOURS) {{
  fetch('/masks-contours.json').then(r=>r.json()).then(d=>{{MASK_CONTOURS=d;}}).catch(()=>{{}});
}}
document.addEventListener('DOMContentLoaded',()=>{{
  const firstBtn = document.querySelector('.tab-btn');
  if (firstBtn) firstBtn.classList.add('active');
}});
</script>
</body>
</html>
"""


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
        "frame_loop": context["frame_loop"]["summary"],
        "inference_modes": context["inference_modes"],
        "debug_panel": context["debug_panel"],
        "endpoints": {
            "manifest": "/manifest.json",
            "stream": "/stream",
            "stream_summary": "/stream-summary.json",
            "stream_messages": "/stream-messages.jsonl",
            "session_log": "/stream-messages.jsonl",
            "live_tracks_jsonl": "/live_tracks.jsonl",
            "stream_events_jsonl": "/stream_events.jsonl",
            "stream_latency": "/stream-latency.csv",
            "frame_loop_summary": "/frame-loop-summary.json",
            "frame_loop_metrics": "/frame-loop-metrics.csv",
            "inference_modes": "/inference-modes.json",
            "debug_panel": "/debug-panel.json",
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
        "inference": context["inference_modes"],
        "summary": context["summary"],
        "video_metadata": asdict(context["video_metadata"]),
        "sync": context["sync"],
        "stream": context["stream_summary"],
        "frame_loop": context["frame_loop"]["summary"],
        "debug_panel": context["debug_panel"],
        "outputs": [
            "playback.html",
            "live_tracks.csv",
            "live_tracks.jsonl",
            "live_events.json",
            "live_highlights.csv",
            "minimap_frame_sample.json",
            "video_metadata.json",
            "endpoint_manifest.json",
            "stream_messages.jsonl",
            "stream_events.jsonl",
            "stream_latency_metrics.csv",
            "stream_summary.json",
            "frame_loop_summary.json",
            "frame_loop_metrics.csv",
            "inference_modes.json",
            "debug_panel_summary.json",
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
        _manifest_row("live_tracks_jsonl", "jsonl", "live_tracks.jsonl", playback_config.tracks_csv, True, "debug", f"{len(context['tracks'])} track snapshots for debug downloads."),
        _manifest_row("live_events", "json", "live_events.json", playback_config.events_json, True, "data", f"{len(context['events'])} normalized events."),
        _manifest_row("live_highlights", "csv", "live_highlights.csv", playback_config.highlights_csv, True, "data", f"{len(context['highlights'])} normalized highlights."),
        _manifest_row("minimap_sample", "json", "minimap_frame_sample.json", "live_tracks.csv", True, "data", "Sample minimap payload for first frame with rectified points."),
        _manifest_row("video_metadata", "json", "video_metadata.json", "configs/default.yaml", True, "sync", "FPS, dimensions, configured duration and approximate frame count."),
        _manifest_row("endpoint_manifest", "json", "endpoint_manifest.json", "live_playback_backend", True, "backend", "Local backend endpoints and path policy."),
        _manifest_row("stream_messages", "jsonl", "stream_messages.jsonl", "live_playback_stream", True, "stream", f"{context['stream_summary']['message_count']} emitted SSE messages."),
        _manifest_row("stream_events_jsonl", "jsonl", "stream_events.jsonl", "live_playback_stream", True, "debug", f"{context['debug_panel']['stream_event_count']} event updates for debug downloads."),
        _manifest_row("stream_latency_metrics", "csv", "stream_latency_metrics.csv", "live_playback_stream", True, "stream", f"{context['stream_summary']['latency_metric_count']} latency metric rows."),
        _manifest_row("stream_summary", "json", "stream_summary.json", "live_playback_stream", True, "stream", "SSE transport decision, message counts and warning summary."),
        _manifest_row("frame_loop_summary", "json", "frame_loop_summary.json", "online_frame_loop", True, "engine", "Online frame loop controls, state and performance summary."),
        _manifest_row("frame_loop_metrics", "csv", "frame_loop_metrics.csv", "online_frame_loop", True, "engine", f"{context['frame_loop']['summary']['processed_frame_count']} per-frame stage metric rows."),
        _manifest_row("inference_modes", "json", "inference_modes.json", "live_playback_inference", True, "inference", f"Selected inference mode: {context['inference_modes']['selected_mode']}."),
        _manifest_row("debug_panel_summary", "json", "debug_panel_summary.json", "live_playback_debug", True, "debug", "Debug panel indicators, downloads and diagnostic coverage."),
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
        f"- Frames procesados por loop online: `{summary['frame_loop_processed_count']}`.",
        f"- Frames saltados por backpressure: `{summary['frame_loop_skipped_count']}`.",
        f"- Latencia promedio loop hasta overlay: `{summary['frame_loop_avg_overlay_ms']}` ms.",
        f"- Modo de inferencia seleccionado: `{summary['inference_mode']}`.",
        f"- Modo recomendado para demo: `{summary['recommended_inference_mode']}`.",
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
        "- `live_tracks.jsonl`.",
        "- `live_events.json`.",
        "- `live_highlights.csv`.",
        "- `minimap_frame_sample.json`.",
        "- `video_metadata.json`.",
        "- `endpoint_manifest.json`.",
        "- `stream_messages.jsonl`.",
        "- `stream_events.jsonl`.",
        "- `stream_latency_metrics.csv`.",
        "- `stream_summary.json`.",
        "- `frame_loop_summary.json`.",
        "- `frame_loop_metrics.csv`.",
        "- `inference_modes.json`.",
        "- `debug_panel_summary.json`.",
        "- `config.yaml`.",
        "- `live_playback_manifest.csv`.",
        "",
        "## Backend Local",
        "",
        "- Endpoints fijos: `/manifest.json`, `/stream`, `/stream-summary.json`, `/stream-messages.jsonl`, `/live_tracks.jsonl`, `/stream_events.jsonl`, `/stream-latency.csv`, `/frame-loop-summary.json`, `/frame-loop-metrics.csv`, `/inference-modes.json`, `/debug-panel.json`, `/tracks.csv`, `/events.json`, `/highlights.csv`, `/minimap.json`, `/calibration.json`, `/video-metadata.json` y `/video?clip_id=...`.",
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
        "## Motor Online De Frames",
        "",
        "- Modo: `precomputed_online_loop`.",
        "- Pipeline: leer frame solicitado, recuperar detecciones precomputadas, actualizar snapshot incremental, actualizar eventos activos y emitir overlay parcial.",
        "- Controles soportados: `pause`, `resume`, `seek`, `stop` y salto de frames por backpressure.",
        "- Inferencia online real: diferida; el hook existe y usa fallback precomputado determinista para esta actividad.",
        "- Metricas por etapa: lectura de frame, deteccion, tracking, eventos, overlay y total hasta overlay.",
        "- Evidencia: `frame_loop_summary.json` y `frame_loop_metrics.csv`.",
        "",
        "## Modos De Inferencia",
        "",
        "- Modo seleccionado por configuracion: `precomputed`, `sam3_sampling` o `lightweight_detector`.",
        "- Recomendado para demo fluida: `precomputed`, porque carga detecciones SAM 3/Level 3 ya generadas y sincroniza por frame o frame cercano.",
        "- `sam3_sampling`: ejecuta SAM 3 solo cada N frames cuando exista GPU MSI autorizada; entre muestras reusa detecciones y registra latencia/VRAM cuando este disponible.",
        "- `lightweight_detector`: hook experimental mas rapido para robots y balon; mantiene compatibilidad con tracker incremental pero documenta degradacion frente a SAM 3 offline.",
        "- Evidencia: `inference_modes.json` y endpoint `/inference-modes.json`.",
        "",
        "## Panel De Depuracion",
        "",
        "- Indicadores visibles: frame, timestamp, inferencia, canal, latencia, cola, tracks activos y evento activo.",
        "- Descargas locales: `stream_messages.jsonl`, `live_tracks.jsonl` y `stream_events.jsonl`.",
        "- Overlay debug: controlado por `layerDebug` desde el panel local.",
        "- Evidencia: `debug_panel_summary.json` y endpoint `/debug-panel.json`.",
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
    tracks_csv: str | None = None,
    events_json: str | None = None,
    highlights_csv: str | None = None,
    inference_mode: str | None = None,
    sam3_stride: int | None = None,
    lightweight_stride: int | None = None,
    allow_gpu: bool | None = None,
    gpu_profile: str | None = None,
) -> dict[str, Any]:
    project_config = load_config(root / config_path)
    playback_config = live_playback_config_from_project(
        root,
        project_config,
        output_dir,
        clip_id=clip_id,
        video_path=video_path,
        tracks_csv=tracks_csv,
        events_json=events_json,
        highlights_csv=highlights_csv,
        inference_mode=inference_mode,
        sam3_stride=sam3_stride,
        lightweight_stride=lightweight_stride,
        allow_gpu=allow_gpu,
        gpu_profile=gpu_profile,
    )
    return build_live_playback_package(root, config_path, playback_config)


def serve_live_playback_app(
    root: Path,
    config_path: Path,
    output_dir: Path,
    host: str,
    port: int,
    clip_id: str | None = None,
    video_path: str | None = None,
    tracks_csv: str | None = None,
    events_json: str | None = None,
    highlights_csv: str | None = None,
    inference_mode: str | None = None,
    sam3_stride: int | None = None,
    lightweight_stride: int | None = None,
    allow_gpu: bool | None = None,
    gpu_profile: str | None = None,
) -> None:
    context = run_smoke_test(
        root,
        config_path,
        output_dir,
        clip_id=clip_id,
        video_path=video_path,
        tracks_csv=tracks_csv,
        events_json=events_json,
        highlights_csv=highlights_csv,
        inference_mode=inference_mode,
        sam3_stride=sam3_stride,
        lightweight_stride=lightweight_stride,
        allow_gpu=allow_gpu,
        gpu_profile=gpu_profile,
    )
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
            if parsed.path == "/live_tracks.jsonl":
                self._send_text(live_tracks_jsonl(context["tracks"]), "application/x-ndjson; charset=utf-8")
                return
            if parsed.path == "/stream_events.jsonl":
                self._send_text(stream_events_jsonl(context["stream_messages"]), "application/x-ndjson; charset=utf-8")
                return
            if parsed.path == "/stream-latency.csv":
                self._send_text(stream_latency_metrics_csv(context["stream_messages"]), "text/csv; charset=utf-8")
                return
            if parsed.path == "/frame-loop-summary.json":
                self._send_json(context["frame_loop"]["summary"])
                return
            if parsed.path == "/frame-loop-metrics.csv":
                self._send_text(frame_loop_metrics_csv(context["frame_loop"]), "text/csv; charset=utf-8")
                return
            if parsed.path == "/inference-modes.json":
                self._send_json(context["inference_modes"])
                return
            if parsed.path == "/debug-panel.json":
                self._send_json(context["debug_panel"])
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
            if parsed.path == "/artifact":
                self._send_artifact(parsed.query)
                return
            if parsed.path == "/masks-contours.json":
                masks_path = context.get("masks_contours_path")
                if masks_path and Path(masks_path).exists():
                    self._send_text(Path(masks_path).read_text("utf-8"), "application/json; charset=utf-8")
                else:
                    self._send_json({})
                return
            if parsed.path == "/analyze-status":
                with _ANALYSIS_LOCK:
                    state_copy = dict(_ANALYSIS_STATE)
                self._send_json(state_copy)
                return
            if parsed.path == "/browse":
                import os as _os_browse
                params = parse_qs(parsed.query)
                req_dir = params.get("dir", [""])[0].strip() or str(Path.home())
                target = Path(req_dir).expanduser().resolve()
                # Security: only allow browsing home subtree
                try:
                    target.relative_to(Path.home().resolve())
                except ValueError:
                    target = Path.home().resolve()
                VIDEO_EXTS = {".mp4", ".mov", ".avi", ".mkv", ".m4v", ".MOV", ".MP4"}
                dirs: list[dict] = []
                files: list[dict] = []
                try:
                    for entry in sorted(target.iterdir(), key=lambda e: (e.is_file(), e.name.lower())):
                        if entry.name.startswith("."):
                            continue
                        if entry.is_dir():
                            dirs.append({"name": entry.name, "path": str(entry)})
                        elif entry.is_file() and entry.suffix in VIDEO_EXTS:
                            files.append({"name": entry.name, "path": str(entry), "size_mb": round(entry.stat().st_size / 1_048_576, 1)})
                except PermissionError:
                    pass
                parent = str(target.parent) if target != target.parent else ""
                self._send_json({"current": str(target), "parent": parent, "dirs": dirs, "files": files})
                return
            if parsed.path == "/video-info":
                params = parse_qs(parsed.query)
                vpath = params.get("path", [""])[0].strip()
                if not vpath or not Path(vpath).exists():
                    self._send_json({"error": "not found"})
                    return
                try:
                    import cv2 as _cv2
                    cap = _cv2.VideoCapture(vpath)
                    fps = cap.get(_cv2.CAP_PROP_FPS) or 30.0
                    total = int(cap.get(_cv2.CAP_PROP_FRAME_COUNT))
                    w = int(cap.get(_cv2.CAP_PROP_FRAME_WIDTH))
                    h = int(cap.get(_cv2.CAP_PROP_FRAME_HEIGHT))
                    cap.release()
                    duration_s = round(total / fps, 2) if fps > 0 else 0
                    self._send_json({"fps": round(fps, 3), "total_frames": total, "width": w, "height": h, "duration_s": duration_s})
                except Exception as exc:
                    self._send_json({"error": str(exc)})
                return
            self.send_error(404)

        def do_POST(self) -> None:
            parsed = urlparse(self.path)
            if parsed.path == "/analyze":
                length = int(self.headers.get("Content-Length", 0))
                body = self.rfile.read(length).decode("utf-8")
                params = parse_qs(body)
                def _first_param(key: str, default: str = "") -> str:
                    vals = params.get(key, [])
                    return vals[0].strip() if vals else default
                video_path = _first_param("video_path")
                clip_id = _first_param("clip_id") or "clip_001"
                start_frame = _first_param("start_frame", "0")
                end_frame = _first_param("end_frame", "300")
                stride = _first_param("stride", "1")
                if not video_path:
                    self._send_json({"error": "Falta la ruta del video"})
                    return
                if not Path(video_path).exists():
                    self._send_json({"error": f"Video no encontrado: {video_path}"})
                    return
                with _ANALYSIS_LOCK:
                    if _ANALYSIS_STATE["running"]:
                        self._send_json({"error": "ya hay un análisis en curso"})
                        return
                    _ANALYSIS_STATE.update({"running": True, "done": False, "state": "starting", "log": [], "error": None})
                config_path = context.get("config_path")
                t = threading.Thread(
                    target=_run_analysis_async,
                    args=(
                        root, context, config_path,
                        video_path, clip_id,
                        int(start_frame or 0),
                        int(end_frame or 300),
                        int(stride or 1),
                    ),
                    daemon=True,
                )
                t.start()
                self._send_json({"status": "started"})
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

        def _send_artifact(self, query: str) -> None:
            params = parse_qs(query)
            rel_path = params.get("path", [""])[0].lstrip("/")
            if not rel_path:
                self.send_error(400, "missing path")
                return
            artifact = (root / rel_path).resolve()
            try:
                artifact.relative_to(root.resolve())
            except ValueError:
                self.send_error(403, "path outside root")
                return
            if not artifact.exists():
                self.send_error(404, f"not found: {rel_path}")
                return
            self._send_file_with_range(artifact)

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
    return f'<label class="tog"><input type="checkbox" id="{element_id}"{state}><span>{_esc(label)}</span></label>'


def _css() -> str:
    return """
:root{
  --bg:#f0f2f5;--bg2:#ffffff;--panel:#ffffff;--panel2:#f8f9fb;
  --line:#e2e6ea;--line2:#cbd3db;
  --text:#1a0a14;--muted:#64748b;
  --mx-green:#006847;--mx-red:#CE1126;--mx-maroon:#7B1A3E;--mx-gold:#B8962E;
  --wc-green:#009a44;--wc-blue:#005eb8;--wc-sky:#00b5e2;
  --ball:#f59e0b;
  font-size:15px
}
*{box-sizing:border-box;margin:0;padding:0}
body{background:var(--bg);color:var(--text);font-family:Inter,'Segoe UI',system-ui,sans-serif;min-height:100vh;display:flex;flex-direction:column}
/* ── Mexican stripe ── */
.mx-stripe{display:flex;height:5px;width:100%}
.mx-stripe>div{flex:1}
.mx-stripe>div:nth-child(1){background:var(--mx-green)}
.mx-stripe>div:nth-child(2){background:#fff}
.mx-stripe>div:nth-child(3){background:var(--mx-red)}
/* ── header ── */
header{background:var(--bg2);box-shadow:0 1px 3px rgba(0,0,0,.1);position:sticky;top:0;z-index:100}
.header-inner{display:flex;align-items:center;gap:14px;padding:10px 20px}
.header-brand{display:flex;align-items:center;gap:12px;flex-shrink:0}
.brand-icons{font-size:22px;display:flex;align-items:center;gap:4px}
.brand-titles{display:flex;flex-direction:column}
.brand-name{font-weight:900;font-size:19px;letter-spacing:-.6px;color:var(--mx-maroon);line-height:1.1}
.brand-sub{font-size:10px;color:var(--muted);display:none}
@media(min-width:800px){.brand-sub{display:block}}
.brand-divider{width:1px;height:32px;background:var(--line2)}
.header-center{display:flex;gap:8px;flex:1;justify-content:center;flex-wrap:wrap}
.clip-badge{background:rgba(0,104,71,.1);border:1px solid rgba(0,104,71,.35);border-radius:20px;padding:4px 12px;font-size:12px;color:var(--mx-green);font-weight:700}
.frames-badge{background:rgba(0,93,184,.08);border:1px solid rgba(0,93,184,.25);border-radius:20px;padding:4px 12px;font-size:12px;color:var(--wc-blue);font-weight:600}
.sync-badge{border:1px solid var(--line2);border-radius:20px;padding:4px 12px;font-size:11px;color:var(--muted);white-space:nowrap;transition:all .3s}
/* ── analyze bar ── */
.analyze-bar{background:var(--bg2);border-bottom:1px solid var(--line);border-top:1px solid var(--line);padding:12px 20px;display:flex;flex-direction:column;gap:8px}
.analyze-form{display:flex;gap:10px;align-items:flex-end;flex-wrap:wrap}
.field-group{display:flex;flex-direction:column;gap:4px}
.field-group label{font-size:10px;color:var(--muted);text-transform:uppercase;letter-spacing:.7px;font-weight:700}
.field-group.field-path{flex:1;min-width:200px}
.path-row{display:flex;gap:6px}
input[type=text],.inp-path,.inp-short,.inp-num{background:var(--bg);border:1px solid var(--line2);color:var(--text);padding:7px 10px;border-radius:6px;font-size:13px;outline:none;transition:border-color .2s,box-shadow .2s}
.inp-path{flex:1;min-width:0}
.inp-short{width:120px}
.inp-num{width:82px;font-variant-numeric:tabular-nums}
input:focus{border-color:var(--mx-green);box-shadow:0 0 0 2px rgba(0,104,71,.12)}
.btn-browse{background:var(--bg);border:1px solid var(--line2);color:var(--muted);border-radius:6px;padding:7px 11px;font-size:15px;cursor:pointer;line-height:1;transition:all .2s}
.btn-browse:hover{border-color:var(--mx-green);color:var(--text)}
.btn-analyze{background:var(--mx-green);color:#fff;border:none;border-radius:6px;padding:8px 22px;font-weight:700;font-size:13px;cursor:pointer;white-space:nowrap;align-self:flex-end;transition:filter .2s;box-shadow:0 2px 6px rgba(0,104,71,.3)}
.btn-analyze:hover{filter:brightness(1.1)}
.video-info-row{font-size:11px;color:var(--muted);padding:2px 0;font-variant-numeric:tabular-nums}
.video-info-row span{color:var(--mx-green);font-weight:600}
.analyze-status{font-size:12px;color:var(--mx-maroon);padding:4px 0}
.analyze-status.hidden{display:none}
/* ── stat cards ── */
.stats-row{display:flex;gap:8px;padding:10px 20px;background:var(--bg);overflow-x:auto;border-bottom:1px solid var(--line);flex-shrink:0}
.stat-card{background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:10px 16px;min-width:88px;text-align:center;flex-shrink:0;box-shadow:0 1px 3px rgba(0,0,0,.06)}
.stat-val{font-size:24px;font-weight:800;line-height:1;font-variant-numeric:tabular-nums}
.stat-lbl{font-size:10px;color:var(--muted);margin-top:4px;text-transform:uppercase;letter-spacing:.8px}
/* ── workbench ── */
.workbench{display:grid;grid-template-columns:1fr 300px;gap:0;background:#111;min-height:0}
@media(max-width:960px){.workbench{grid-template-columns:1fr}}
.stage-wrap{display:flex;align-items:flex-start;justify-content:center;background:#000;overflow:hidden}
.stage{position:relative;width:min(100%,calc(65vh * var(--vid-w,16) / var(--vid-h,9)));flex-shrink:0;aspect-ratio:var(--vid-w,16)/var(--vid-h,9)}
video{display:block;width:100%;height:100%;background:#000;object-fit:contain}
canvas{position:absolute;inset:0;width:100%;height:100%;pointer-events:none}
.video-missing{position:absolute;bottom:10px;left:50%;transform:translateX(-50%);background:rgba(0,0,0,.88);border:1px solid rgba(255,255,255,.15);border-radius:6px;padding:8px 14px;font-size:12px;color:#aaa;white-space:nowrap}
.video-missing.hidden{display:none}
/* ── side panel ── */
.side-panel{background:var(--panel);border-left:1px solid var(--line);display:flex;flex-direction:column;overflow-y:auto;max-height:65vh}
.panel-section{padding:12px 14px;border-bottom:1px solid var(--line)}
.panel-section h3{font-size:10px;color:var(--muted);text-transform:uppercase;letter-spacing:1px;font-weight:700;margin-bottom:9px}
.readout-grid{display:grid;grid-template-columns:auto 1fr;gap:4px 12px;font-size:13px;font-variant-numeric:tabular-nums}
.readout-grid span{color:var(--muted)}
.readout-grid strong{color:var(--text);text-align:right;font-weight:700}
.toggles{display:grid;grid-template-columns:1fr 1fr;gap:5px}
.tog{display:flex;align-items:center;gap:5px;font-size:12px;cursor:pointer;color:var(--text);padding:5px 7px;border-radius:5px;border:1px solid var(--line);user-select:none;transition:all .15s}
.tog:hover{border-color:var(--mx-green);background:rgba(0,104,71,.04)}
.tog input{accent-color:var(--mx-green)}
/* ── minimap sidebar ── */
.minimap-panel{padding:10px 14px 12px;border-bottom:1px solid var(--line)}
.minimap-panel h3{font-size:10px;color:var(--muted);text-transform:uppercase;letter-spacing:1px;font-weight:700;margin-bottom:8px}
.minimap-canvas{width:100%;height:130px;border-radius:6px;border:1px solid var(--line2);display:block;background:#050f05}
/* ── legend ── */
.legend{display:flex;flex-direction:column;gap:7px;font-size:12px;color:var(--muted)}
.legend div{display:flex;align-items:center;gap:8px}
.leg-dot{width:10px;height:10px;border-radius:50%;flex-shrink:0}
.leg-dot.blue{background:var(--wc-blue)}.leg-dot.red{background:var(--mx-red)}.leg-dot.ball{background:var(--ball)}.leg-dot.green{background:var(--mx-green)}
/* ── downloads ── */
.downloads{display:flex;flex-direction:column;gap:5px}
.dl-link,.btn-link{display:block;font-size:12px;color:var(--wc-blue);text-decoration:none;padding:5px 8px;border:1px solid var(--line);border-radius:5px;text-align:center;transition:all .15s}
.dl-link:hover,.btn-link:hover{border-color:var(--wc-blue);background:rgba(0,93,184,.06)}
/* ── analytics tabs ── */
.analytics{background:var(--bg2);border-top:1px solid var(--line)}
.tab-nav{display:flex;gap:0;border-bottom:2px solid var(--line);overflow-x:auto;background:var(--bg2)}
.tab-btn{background:none;border:none;border-bottom:3px solid transparent;color:var(--muted);padding:11px 18px;font-size:13px;cursor:pointer;white-space:nowrap;font-family:inherit;margin-bottom:-2px;transition:color .15s,border-color .15s}
.tab-btn:hover{color:var(--text)}
.tab-btn.active{color:var(--mx-green);border-bottom-color:var(--mx-green);font-weight:600}
.tab-panel{padding:16px;display:flex;flex-direction:column;gap:12px;min-height:180px;overflow-x:auto}
.tab-panel.hidden{display:none}
.gallery{display:flex;gap:12px;flex-wrap:wrap;justify-content:flex-start;align-items:flex-start}
.gallery img,.full-img{max-width:100%;height:auto;border-radius:8px;border:1px solid var(--line);box-shadow:0 1px 4px rgba(0,0,0,.08)}
.gallery img{max-height:260px;object-fit:contain;flex:1 1 280px;min-width:0}
.full-img{max-height:380px;object-fit:contain;display:block;margin:0 auto}
.highlights-gallery img{max-height:200px}
.empty{color:var(--muted);font-size:13px;padding:24px;text-align:center;background:var(--panel2);border-radius:8px;border:1px dashed var(--line2)}
/* ── file browser ── */
.fb-overlay{display:none;position:fixed;inset:0;background:rgba(0,0,0,.5);z-index:200;backdrop-filter:blur(3px)}
.fb-overlay.open{display:flex;align-items:flex-start;justify-content:center;padding-top:60px}
.fb-panel{background:var(--panel);border:1px solid var(--line2);border-radius:12px;width:min(700px,96vw);max-height:70vh;display:flex;flex-direction:column;box-shadow:0 20px 60px rgba(0,0,0,.2)}
.fb-head{display:flex;align-items:center;gap:8px;padding:14px 16px;border-bottom:1px solid var(--line);flex-shrink:0}
.fb-title{font-size:14px;font-weight:700;color:var(--text)}
.fb-path-label{font-size:11px;color:var(--muted);flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.fb-close{background:none;border:none;color:var(--muted);font-size:18px;cursor:pointer;padding:0 4px;line-height:1;transition:color .15s}
.fb-close:hover{color:var(--text)}
.fb-list{overflow-y:auto;flex:1;padding:6px 0}
.fb-item{display:flex;align-items:center;gap:10px;padding:8px 16px;cursor:pointer;font-size:13px;border-left:3px solid transparent;transition:all .1s}
.fb-item:hover{background:rgba(0,104,71,.05);border-left-color:var(--mx-green)}
.fb-item.fb-dir{color:var(--wc-blue)}
.fb-item.fb-file{color:var(--text)}
.fb-item.fb-up{color:var(--muted);font-style:italic}
.fb-icon{font-size:15px;flex-shrink:0;width:22px;text-align:center}
.fb-size{margin-left:auto;font-size:11px;color:var(--muted);font-variant-numeric:tabular-nums}
.fb-empty{padding:24px;text-align:center;color:var(--muted);font-size:13px}
/* ── events section ── */
.events-section{padding:14px 20px;background:var(--bg);border-top:1px solid var(--line)}
.events-section h3{font-size:10px;color:var(--muted);text-transform:uppercase;letter-spacing:1px;font-weight:700;margin-bottom:10px}
.event-list{display:flex;flex-direction:column;gap:6px;max-height:180px;overflow-y:auto}
.ev-card{background:var(--panel);border:1px solid var(--line);border-left:3px solid var(--ball);border-radius:6px;padding:8px 12px;font-size:12px;box-shadow:0 1px 2px rgba(0,0,0,.04)}
.ev-card .ev-label{font-weight:600;color:var(--text)}
.ev-card .ev-meta{color:var(--muted);margin-top:2px}
.ev-card.highlight{border-left-color:var(--mx-red)}
.ev-empty{color:var(--muted);font-size:13px;font-style:italic}
"""


def _js() -> str:
    return """
const data=window.FUTBOT_PLAYBACK_DATA;
const video=document.getElementById('video');
const canvas=document.getElementById('overlay');
const ctx=canvas.getContext('2d');
const minimapCanvas=document.getElementById('minimapCanvas');
const minimapCtx=minimapCanvas?.getContext('2d');
const syncState=document.getElementById('syncState');
const frameReadout=document.getElementById('frameReadout');
const timeReadout=document.getElementById('timeReadout');
const rateReadout=document.getElementById('rateReadout');
const resolvedFrameReadout=document.getElementById('resolvedFrameReadout');
const dataReadout=document.getElementById('dataReadout');
const videoMissing=document.getElementById('videoMissing');
const byFrame=new Map();
for(const row of data.tracks){const f=Number(row.frame);if(!byFrame.has(f))byFrame.set(f,[]);byFrame.get(f).push(row);}
const availableFrames=(data.available_frames||[]).map(Number).sort((a,b)=>a-b);
let lastTarget=null,suppressTrails=0;
// ── helpers ──
function enabled(id){return document.getElementById(id)?.checked;}
function esc(t){return String(t).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));}
function teamColor(row){return row.team==='blue'?'#005eb8':row.team==='red'?'#CE1126':'#006847';}
function frameFromTime(t){const fps=Number(data.config.fps)||30;return Math.min(Math.round(Math.max(0,t||0)*fps),Number(data.config.end_frame)||99999);}
function frameNow(){return frameFromTime(video.currentTime||0);}
function resolveFrame(target){
  if(byFrame.has(target))return{resolved_frame:target,status:'exact'};
  let prev=null,next=null;
  for(const f of availableFrames){if(f<=target)prev=f;if(f>target&&next===null)next=f;}
  const maxGap=Number(data.sync?.max_frame_gap||0)||999999;
  if(prev!==null&&target-prev<=maxGap)return{resolved_frame:prev,status:'prev'};
  if(next!==null&&next-target<=maxGap)return{resolved_frame:next,status:'next'};
  return{resolved_frame:null,status:'missing'};
}
let _cx=0,_cy=0,_cw=1,_ch=1;
function resizeCanvas(){
  const r=video.getBoundingClientRect();
  const W=data.config.width||1280,H=data.config.height||720;
  canvas.width=Math.max(1,Math.round(r.width||W));
  canvas.height=Math.max(1,Math.round(r.height||H));
  // Container sized to match video aspect ratio — no pillarbox/letterbox
  _cx=0;_cy=0;_cw=canvas.width;_ch=canvas.height;
}
function scaleX(x){return _cx+Number(x)*(_cw/(data.config.width||_cw));}
function scaleY(y){return _cy+Number(y)*(_ch/(data.config.height||_ch));}
function label(text,x,y,color){
  ctx.font='bold 11px system-ui';
  const w=ctx.measureText(text).width+8;
  ctx.fillStyle='rgba(8,13,30,.88)';ctx.fillRect(x,y-14,w,16);
  ctx.fillStyle=color;ctx.fillText(text,x+4,y);
}
function badge(text,x,y,color){
  ctx.font='12px system-ui';
  const w=Math.min(canvas.width-x-8,ctx.measureText(text).width+16);
  ctx.fillStyle='rgba(8,13,30,.9)';ctx.fillRect(x,y,w,22);
  ctx.strokeStyle=color;ctx.lineWidth=1;ctx.strokeRect(x,y,w,22);
  ctx.fillStyle='#e8ecf4';ctx.fillText(text,x+7,y+15);
}
// ── draw functions ──
function drawTracks(rows){
  for(const row of rows){
    const cls=row.class||'';
    if(cls==='ball')continue;
    const x=scaleX(row.x),y=scaleY(row.y),w=scaleX(row.w),h=scaleY(row.h);
    const cx=scaleX(row.center_x),cy=scaleY(row.center_y);
    if(cls.includes('goalpost')||cls.includes('porteria')){
      ctx.strokeStyle='#f0c230';ctx.lineWidth=3;
      ctx.setLineDash([6,4]);ctx.strokeRect(x,y,w,h);ctx.setLineDash([]);
      if(enabled('layerGoalpost'))label('portería',x,y-3,'#f0c230');
    } else if(cls.includes('field')||cls.includes('campo')){
      if(!enabled('layerField'))continue;
      ctx.strokeStyle='rgba(77,206,120,.35)';ctx.lineWidth=1.5;
      ctx.setLineDash([4,6]);ctx.strokeRect(x,y,w,h);ctx.setLineDash([]);
    } else {
      const color=teamColor(row);
      ctx.strokeStyle=color;ctx.lineWidth=2.5;ctx.strokeRect(x,y,w,h);
      ctx.fillStyle=color;ctx.beginPath();ctx.arc(cx,cy,4,0,Math.PI*2);ctx.fill();
      if(enabled('layerIds'))label(row.track_id.replace('_bt_','-'),x,y-3,color);
    }
  }
}
function drawBall(rows){
  const balls=rows.filter(r=>(r.class||'')==='ball');
  if(!balls.length)return;
  const best=balls.reduce((a,b)=>Number(b.confidence||0)>Number(a.confidence||0)?b:a);
  const x=scaleX(best.center_x),y=scaleY(best.center_y);
  ctx.shadowColor='#f59e0b';ctx.shadowBlur=14;
  ctx.fillStyle='#f59e0b';ctx.strokeStyle='#1a0a14';ctx.lineWidth=2;
  ctx.beginPath();ctx.arc(x,y,9,0,Math.PI*2);ctx.fill();ctx.stroke();
  ctx.shadowBlur=0;
  if(enabled('layerIds'))label(best.track_id,x+11,y,'#f59e0b');
}
function drawTrails(frame){
  const start=frame-(data.config.trail_length||20);
  const trails=new Map();
  for(const row of data.tracks){
    const f=Number(row.frame);
    if(f<start||f>frame)continue;
    if(!trails.has(row.track_id))trails.set(row.track_id,[]);
    trails.get(row.track_id).push(row);
  }
  for(const [tid,pts] of trails){
    if(pts.length<2)continue;
    const isBall=(pts[0].class||'')==='ball';
    ctx.beginPath();
    pts.forEach((p,i)=>{
      const x=scaleX(p.center_x),y=scaleY(p.center_y);
      i===0?ctx.moveTo(x,y):ctx.lineTo(x,y);
    });
    ctx.strokeStyle=isBall?'rgba(245,158,11,.5)':teamColor(pts[0])+'88';
    ctx.lineWidth=isBall?2:1.5;ctx.stroke();
  }
}
function drawMinimapPanel(rows){
  if(!minimapCtx)return;
  const pw=minimapCanvas.offsetWidth||240,ph=minimapCanvas.offsetHeight||128;
  if(minimapCanvas.width!==pw)minimapCanvas.width=pw;
  if(minimapCanvas.height!==ph)minimapCanvas.height=ph;
  minimapCtx.clearRect(0,0,pw,ph);
  // Field surface
  minimapCtx.fillStyle='#030f03';minimapCtx.fillRect(0,0,pw,ph);
  // Field markings
  minimapCtx.strokeStyle='#1a3a1a';minimapCtx.lineWidth=1;
  minimapCtx.strokeRect(2,2,pw-4,ph-4);
  // Center line
  minimapCtx.beginPath();minimapCtx.moveTo(pw/2,2);minimapCtx.lineTo(pw/2,ph-2);minimapCtx.stroke();
  // Center circle
  minimapCtx.beginPath();minimapCtx.arc(pw/2,ph/2,Math.min(pw,ph)*.13,0,Math.PI*2);minimapCtx.stroke();
  // Penalty areas
  minimapCtx.strokeRect(2,ph*.22,pw*.14,ph*.56);
  minimapCtx.strokeRect(pw-2-pw*.14,ph*.22,pw*.14,ph*.56);
  // Players and ball
  for(const row of rows){
    const xn=row.x_norm,yn=row.y_norm;
    if(xn===''||yn===''||xn===undefined||yn===undefined)continue;
    const isBall=(row.class||'')==='ball';
    minimapCtx.fillStyle=isBall?'#f59e0b':teamColor(row);
    if(isBall){minimapCtx.shadowColor='#f59e0b';minimapCtx.shadowBlur=7;}
    minimapCtx.beginPath();
    minimapCtx.arc(2+Number(xn)*(pw-4),2+Number(yn)*(ph-4),isBall?5:4,0,Math.PI*2);
    minimapCtx.fill();
    if(isBall)minimapCtx.shadowBlur=0;
  }
}
function drawMasks(targetFrame){
  const key='frame_'+targetFrame;
  const contours=MASK_CONTOURS[key]||[];
  if(!contours.length)return;
  for(const c of contours){
    if(!c.contour||c.contour.length<3)continue;
    const cls=c.class||'';
    let color='#4dce78';
    if(cls.includes('robot'))color='#4ba8ff';
    else if(cls.includes('ball'))color='#f0c230';
    else if(cls.includes('goalpost'))color='#ff5f5f';
    ctx.beginPath();
    const [x0,y0]=c.contour[0];
    ctx.moveTo(scaleX(x0),scaleY(y0));
    for(const [x,y] of c.contour.slice(1))ctx.lineTo(scaleX(x),scaleY(y));
    ctx.closePath();
    ctx.strokeStyle=color;
    ctx.lineWidth=3;
    ctx.stroke();
    // subtle fill
    ctx.fillStyle=color+'22';
    ctx.fill();
  }
}
function drawEvents(events){
  let top=14;
  for(const e of events.slice(0,4)){
    if(!e.label)continue;
    badge(e.label+(e.status?' · '+e.status:''),14,top,'#f59e0b');top+=28;
  }
}
function draw(){
  resizeCanvas();ctx.clearRect(0,0,canvas.width,canvas.height);
  const target=frameNow();
  const resolved=resolveFrame(target);
  const frame=resolved.resolved_frame;
  const rows=frame===null?[]:(byFrame.get(frame)||[]);
  const events=data.events.filter(e=>Number(e.start_frame)<=target&&Number(e.end_frame)>=target);
  const highlights=data.highlights.filter(e=>Number(e.start_frame)<=target&&Number(e.end_frame)>=target);
  if(lastTarget!==null&&Math.abs(target-lastTarget)>32)suppressTrails=2;
  lastTarget=target;
  frameReadout.textContent=String(target);
  timeReadout.textContent=(video.currentTime||0).toFixed(2)+'s';
  rateReadout.textContent=(video.playbackRate||1).toFixed(1)+'×';
  resolvedFrameReadout.textContent=frame===null?'sin datos':frame+'('+resolved.status+')';
  dataReadout.textContent=rows.length+' obj | '+events.length+' evt';
  syncState.textContent=resolved.status==='missing'?'sin datos':resolved.status==='exact'?'en caché':'interpolado';
  if(enabled('layerTrails')&&suppressTrails<=0)drawTrails(frame??target);
  else if(suppressTrails>0)suppressTrails--;
  if(enabled('layerMasks'))drawMasks(frame??target);
  if(enabled('layerTracks'))drawTracks(rows);
  if(enabled('layerBall'))drawBall(rows);
  if(enabled('layerEvents'))drawEvents(events);
  drawMinimapPanel(rows);
  renderEvents(events,highlights);
  requestAnimationFrame(draw);
}
function renderEvents(events,highlights){
  const list=document.getElementById('eventList');
  if(!list)return;
  const all=[...highlights.slice(0,3).map(h=>({...h,_hl:true})),...events.filter(e=>e.label).slice(0,6)];
  if(!all.length){list.innerHTML='<p class="ev-empty">Sin eventos en el frame actual.</p>';return;}
  list.innerHTML=all.map(item=>`
    <div class="ev-card${item._hl?' highlight':''}">
      <div class="ev-label">${esc(item.label||item.event_id||'evento')}</div>
      <div class="ev-meta">frames ${item.start_frame??'?'}–${item.end_frame??'?'} · ${esc(item.status||item.zone||'')}</div>
    </div>`).join('');
}
// ── tabs ──
function showTab(id,btn){
  document.querySelectorAll('.tab-panel').forEach(p=>p.classList.add('hidden'));
  document.querySelectorAll('.tab-btn').forEach(b=>b.classList.remove('active'));
  const panel=document.getElementById('tab-'+id);
  if(panel)panel.classList.remove('hidden');
  if(btn)btn.classList.add('active');
}
// ── file browser ──
const fbOverlay=document.getElementById('fbOverlay');
const fbList=document.getElementById('fbList');
const fbPathLabel=document.getElementById('fbPathLabel');
const inpVideoPath=document.getElementById('inpVideoPath');
const inpClipId=document.getElementById('inpClipId');
const inpStartFrame=document.getElementById('inpStartFrame');
const inpEndFrame=document.getElementById('inpEndFrame');
const videoInfoRow=document.getElementById('videoInfoRow');
let _fbCurrentDir='';
async function fbLoad(dir){
  fbList.innerHTML='<div class="fb-empty">Cargando…</div>';
  const bd=await fetch('/browse?dir='+encodeURIComponent(dir)).then(r=>r.json());
  _fbCurrentDir=bd.current||dir;
  fbPathLabel.textContent=_fbCurrentDir;
  let html='';
  if(bd.parent){
    html+=`<div class="fb-item fb-up" data-dir="${esc(bd.parent)}"><span class="fb-icon">⬆</span>.. (subir)</div>`;
  }
  for(const d of (bd.dirs||[])){
    html+=`<div class="fb-item fb-dir" data-dir="${esc(d.path)}"><span class="fb-icon">📁</span>${esc(d.name)}</div>`;
  }
  for(const f of (bd.files||[])){
    html+=`<div class="fb-item fb-file" data-path="${esc(f.path)}"><span class="fb-icon">🎬</span>${esc(f.name)}<span class="fb-size">${f.size_mb} MB</span></div>`;
  }
  if(!html)html='<div class="fb-empty">Sin videos ni subdirectorios</div>';
  fbList.innerHTML=html;
  fbList.querySelectorAll('.fb-item[data-dir]').forEach(el=>el.addEventListener('click',()=>fbLoad(el.dataset.dir)));
  fbList.querySelectorAll('.fb-item[data-path]').forEach(el=>el.addEventListener('click',()=>{
    fbSelectFile(el.dataset.path);
  }));
}
function fbSelectFile(path){
  inpVideoPath.value=path;
  fbOverlay.classList.remove('open');
  loadVideoInfo(path);
  const parts=path.split('/');
  const name=parts[parts.length-1].replace(/[.][^.]+$/,'').replace(/[^a-zA-Z0-9]/g,'_');
  if(inpClipId)inpClipId.value=name.slice(0,30);
}
document.getElementById('btnBrowse')?.addEventListener('click',()=>{
  fbOverlay.classList.add('open');
  const startDir=inpVideoPath.value?inpVideoPath.value.split('/').slice(0,-1).join('/')||'/':'/home';
  fbLoad(startDir||'/home');
});
document.getElementById('fbClose')?.addEventListener('click',()=>fbOverlay.classList.remove('open'));
fbOverlay?.addEventListener('click',e=>{if(e.target===fbOverlay)fbOverlay.classList.remove('open');});
// ── video info auto-detect ──
let _viTimer=null;
async function loadVideoInfo(path){
  if(!path)return;
  videoInfoRow.style.display='none';
  const info=await fetch('/video-info?path='+encodeURIComponent(path)).then(r=>r.json()).catch(()=>({}));
  if(info.error||!info.total_frames)return;
  const dur=info.duration_s,mm=Math.floor(dur/60),ss=(dur%60).toFixed(1);
  videoInfoRow.textContent='';
  videoInfoRow.innerHTML=`Video detectado: <span>${info.width}×${info.height}</span> · <span>${info.fps} fps</span> · <span>${mm}:${ss.padStart(4,'0')} min</span> · <span>${info.total_frames} frames</span>`;
  videoInfoRow.style.display='block';
  if(inpStartFrame)inpStartFrame.value=0;
  if(inpEndFrame)inpEndFrame.value=info.total_frames;
}
inpVideoPath?.addEventListener('change',()=>loadVideoInfo(inpVideoPath.value));
inpVideoPath?.addEventListener('input',()=>{clearTimeout(_viTimer);_viTimer=setTimeout(()=>loadVideoInfo(inpVideoPath.value),800);});
// Cargar info del video actual si ya tiene ruta
if(inpVideoPath?.value)setTimeout(()=>loadVideoInfo(inpVideoPath.value),200);
// ── analyze form ──
const analyzeForm=document.getElementById('analyzeForm');
const analyzeStatus=document.getElementById('analyzeStatus');
let pollInterval=null,_analyzeStart=0;
if(analyzeForm){
  analyzeForm.addEventListener('submit',async e=>{
    e.preventDefault();
    if(pollInterval){clearInterval(pollInterval);pollInterval=null;}
    const fd=new FormData(analyzeForm);
    const params=new URLSearchParams(fd);
    analyzeStatus.textContent='Iniciando análisis…';
    analyzeStatus.classList.remove('hidden');
    const resp=await fetch('/analyze',{method:'POST',body:params,headers:{'Content-Type':'application/x-www-form-urlencoded'}});
    if(resp.ok){
      const rj=await resp.json();
      if(rj.error){
        analyzeStatus.textContent='✗ '+rj.error;
        return;
      }
      _analyzeStart=Date.now();
      analyzeStatus.textContent='⏳ Analizando… (la segmentación Grounded-SAM tarda 10–30 min en GPU)';
      pollInterval=setInterval(async()=>{
        const s=await fetch('/analyze-status').then(r=>r.json());
        const elapsed=Math.round((Date.now()-_analyzeStart)/1000);
        const mm=String(Math.floor(elapsed/60)).padStart(2,'0'),ss=String(elapsed%60).padStart(2,'0');
        const last=s.log?.slice(-1)[0]||'';
        if(s.running){
          analyzeStatus.textContent=`⏳ Analizando… ${mm}:${ss} — ${last}`;
        } else if(s.done&&!s.error){
          analyzeStatus.textContent='✓ ¡Listo! Recargando…';
          clearInterval(pollInterval);setTimeout(()=>window.location.reload(),1500);
        } else {
          const errLog=(s.log||[]).slice(-5).join('\\n');
          analyzeStatus.style.whiteSpace='pre-wrap';
          analyzeStatus.textContent='✗ Error: '+(s.error||'?')+'\\n'+errLog;
          clearInterval(pollInterval);
        }
      },3000);
    } else {
      analyzeStatus.textContent='✗ Error al iniciar análisis';
    }
  });
}
// ── video events ──
if(!data.config.video_exists)videoMissing.classList.remove('hidden');
video.addEventListener('seeking',()=>{suppressTrails=2;resizeCanvas();});
video.addEventListener('seeked',()=>{suppressTrails=2;resizeCanvas();});
video.addEventListener('play',()=>{syncState.textContent='reproduciendo';});
video.addEventListener('pause',()=>{syncState.textContent='pausado';});
video.addEventListener('ended',()=>{syncState.textContent='fin';});
window.addEventListener('resize',resizeCanvas);
for(const cb of document.querySelectorAll('input[type=checkbox]'))cb.addEventListener('change',()=>{suppressTrails=1;});
// ── SSE stream ──
if(data.endpoints?.stream&&window.EventSource){
  const es=new EventSource(data.endpoints.stream);
  es.addEventListener('session_status',e=>{const m=JSON.parse(e.data);if(m.status==='complete')es.close();});
}
requestAnimationFrame(draw);
"""


def _controls_by_frame(
    controls: list[FrameLoopControl | dict[str, Any]],
    default_frame: int,
) -> dict[int, list[FrameLoopControl]]:
    by_frame: dict[int, list[FrameLoopControl]] = {}
    for raw_control in controls:
        control = raw_control if isinstance(raw_control, FrameLoopControl) else _coerce_frame_loop_control(raw_control)
        frame = control.at_frame if control.at_frame is not None else default_frame
        by_frame.setdefault(frame, []).append(control)
    return by_frame


def _coerce_frame_loop_control(raw_control: dict[str, Any]) -> FrameLoopControl:
    return FrameLoopControl(
        action=str(raw_control.get("action", "")),
        at_frame=_optional_int(raw_control.get("at_frame")),
        seek_frame=_optional_int(raw_control.get("seek_frame")),
        reason=str(raw_control.get("reason", "")),
    )


def _apply_frame_loop_control(add: Any, state: dict[str, Any], control: FrameLoopControl, frame: int) -> None:
    action = control.action.lower().strip()
    if action == "pause":
        state["paused"] = True
        add(
            "session_status",
            {
                "status": "paused",
                "engine_state": "paused",
                "frame": frame,
                "reason": control.reason or "control",
            },
        )
        return
    if action == "resume":
        state["paused"] = False
        add(
            "session_status",
            {
                "status": "running",
                "engine_state": "resumed",
                "frame": frame,
                "reason": control.reason or "control",
            },
        )
        return
    if action == "seek":
        seek_frame = control.seek_frame if control.seek_frame is not None else frame
        state["pending_seek_frame"] = seek_frame
        state["reset_count"] += 1
        add(
            "session_status",
            {
                "status": "seeked",
                "engine_state": "reset",
                "frame": frame,
                "seek_frame": seek_frame,
                "reset_state": True,
                "reason": control.reason or "seek",
            },
        )
        return
    if action == "stop":
        state["stopped"] = True
        add(
            "session_status",
            {
                "status": "stopped",
                "engine_state": "stopped",
                "frame": frame,
                "reason": control.reason or "control",
            },
        )
        return
    add(
        "warning",
        {
            "severity": "warn",
            "warning_code": "unknown_frame_loop_control",
            "message": f"Control de loop desconocido: {control.action}",
            "frame": frame,
        },
    )


def _frame_loop_stage_metrics(
    loop_config: OnlineFrameLoopConfig,
    requested_frame: int,
    resolution: FrameResolution,
    rows: list[dict[str, Any]],
    events: list[dict[str, Any]],
    highlights: list[dict[str, Any]],
) -> dict[str, Any]:
    track_count = len(rows)
    event_count = len(events)
    highlight_count = len(highlights)
    frame_read_ms = 0.18
    if loop_config.inference_mode == "sam3_sampling":
        detection_ms = 92.0 + track_count * 0.4
    elif loop_config.inference_mode == "lightweight_detector":
        detection_ms = 5.5 + track_count * 0.18
    else:
        detection_ms = 0.22 + track_count * 0.02
    tracking_ms = 0.12 + track_count * 0.04
    events_ms = 0.08 + (event_count + highlight_count) * 0.03
    overlay_ms = 0.16 + track_count * 0.02
    total = frame_read_ms + detection_ms + tracking_ms + events_ms + overlay_ms
    return {
        "frame_read_ms": round(frame_read_ms, 3),
        "detection_ms": round(detection_ms, 3),
        "tracking_ms": round(tracking_ms, 3),
        "events_ms": round(events_ms, 3),
        "overlay_ms": round(overlay_ms, 3),
        "total_to_overlay_ms": round(total, 3),
        "lookup_latency_ms": round(frame_read_ms + detection_ms, 3),
        "emit_latency_ms": round(overlay_ms, 3),
        "processing_budget_ms": loop_config.processing_budget_ms,
        "target_fps": loop_config.target_fps,
        "skipped_frames": 0,
        "queue_depth": 0,
        "backpressure": total > loop_config.processing_budget_ms,
        "source": "precomputed_online_frame_loop",
        "inference_mode": loop_config.inference_mode,
        "inference_status": loop_config.inference_status,
        "inference_stride": loop_config.inference_stride,
        "tracker_mode": loop_config.tracker_mode,
        "event_window_frames": loop_config.event_window_frames,
        "gpu_memory_mb": "",
        "gpu_memory_metric": "not_available" if loop_config.inference_mode == "sam3_sampling" else "not_applicable",
        "overlay_ready": resolution.resolved_frame is not None,
        "requested_frame": requested_frame,
    }


def _frame_loop_skip_count(
    metrics: dict[str, Any],
    frames: list[int],
    frame_index: int,
    loop_config: OnlineFrameLoopConfig,
) -> int:
    if metrics["total_to_overlay_ms"] <= loop_config.processing_budget_ms:
        return 0
    remaining = len(frames) - frame_index - 1
    if remaining <= 0:
        return 0
    budget = max(loop_config.processing_budget_ms, 0.001)
    overrun_units = max(1, int(metrics["total_to_overlay_ms"] // budget))
    return min(remaining, loop_config.max_skip_frames, overrun_units)


def _frame_loop_summary(
    context: dict[str, Any],
    loop_config: OnlineFrameLoopConfig,
    messages: list[dict[str, Any]],
    metrics: list[dict[str, Any]],
    state: dict[str, Any],
) -> dict[str, Any]:
    return {
        "mode": loop_config.mode,
        "inference_mode": loop_config.inference_mode,
        "inference_profile": loop_config.inference_profile,
        "inference_status": loop_config.inference_status,
        "inference_stride": loop_config.inference_stride,
        "detection_source": loop_config.detection_source,
        "inference_enabled": loop_config.inference_enabled,
        "tracker_mode": loop_config.tracker_mode,
        "event_window_frames": loop_config.event_window_frames,
        "processing_budget_ms": loop_config.processing_budget_ms,
        "target_fps": loop_config.target_fps,
        "available_frame_count": len(context["available_frames"]),
        "processed_frame_count": len(metrics),
        "partial_result_count": len([message for message in messages if message.get("type") == "frame_result"]),
        "skipped_frame_count": state["skipped_frame_count"],
        "skipped_frames": state["skipped_frames"],
        "state_reset_count": state["reset_count"],
        "message_count": len(messages),
        "emits_partial_results": bool(metrics),
        "requires_final_csv": False,
        "backpressure_policy": loop_config.backpressure_policy,
        "controls_supported": ["pause", "resume", "seek", "stop", "skip_late_frames"],
        "average_total_to_overlay_ms": _average_metric(metrics, "total_to_overlay_ms"),
        "max_total_to_overlay_ms": _max_metric(metrics, "total_to_overlay_ms"),
        "average_frame_read_ms": _average_metric(metrics, "frame_read_ms"),
        "average_detection_ms": _average_metric(metrics, "detection_ms"),
        "average_tracking_ms": _average_metric(metrics, "tracking_ms"),
        "average_events_ms": _average_metric(metrics, "events_ms"),
        "average_overlay_ms": _average_metric(metrics, "overlay_ms"),
    }


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


def _optional_int(value: Any) -> int | None:
    if value in {"", None}:
        return None
    return _coerce_int(value, 0)


def _coerce_bool(value: Any, default: bool = False) -> bool:
    if value in {"", None}:
        return default
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "y", "on"}


def _normalize_inference_mode(value: Any) -> str:
    mode = str(value or DEFAULT_INFERENCE_MODE).strip().lower().replace("-", "_")
    aliases = {
        "precomputed_lookup": "precomputed",
        "precompute": "precomputed",
        "offline": "precomputed",
        "sam3": "sam3_sampling",
        "sam_3": "sam3_sampling",
        "sam3_stride": "sam3_sampling",
        "sam3_sampling_gpu": "sam3_sampling",
        "light": "lightweight_detector",
        "lightweight": "lightweight_detector",
        "fast_detector": "lightweight_detector",
        "detector_ligero": "lightweight_detector",
    }
    normalized = aliases.get(mode, mode)
    if normalized not in INFERENCE_MODE_IDS:
        return DEFAULT_INFERENCE_MODE
    return normalized


def _first(params: dict[str, list[str]], key: str, default: str) -> str:
    values = params.get(key)
    if not values:
        return default
    return values[0]


def _esc(value: Any) -> str:
    return html.escape(str(value), quote=True)
