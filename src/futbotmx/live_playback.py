from __future__ import annotations

import csv
import html
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
    video = resolve_configured_video(playback_config)
    return {
        "rule_version": RULE_VERSION,
        "config": playback_config,
        "tracks": normalized_tracks,
        "events": normalized_events,
        "highlights": normalized_highlights,
        "minimap_sample": minimap_sample,
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
            "video_exists": bool(video and video.exists()),
            "tracks_csv": playback_config.tracks_csv,
            "events_json": playback_config.events_json,
            "highlights_csv": playback_config.highlights_csv,
            "validation_errors": sum(len(row["errors"]) for row in validation),
        },
    }


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
            '<span>Frame <strong id="frameReadout">0</strong></span>',
            '<span>Tiempo <strong id="timeReadout">0.000s</strong></span>',
            '<span>Datos <strong id="dataReadout">sin datos</strong></span>',
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
        "outputs": [
            "playback.html",
            "live_tracks.csv",
            "live_events.json",
            "live_highlights.csv",
            "minimap_frame_sample.json",
            "live_playback_manifest.csv",
            "summary.md",
        ],
    }
    write_config_snapshot(config, root / playback_config.output_dir / "config.yaml")


def write_live_playback_manifest(root: Path, playback_config: LivePlaybackConfig, context: dict[str, Any]) -> None:
    rows = [
        _manifest_row("playback_html", "html", "playback.html", "render_playback_html", True, "ui", "Video element plus synchronized canvas overlay."),
        _manifest_row("config", "yaml", "config.yaml", "configs/default.yaml", True, "config", "Live playback configuration snapshot."),
        _manifest_row("summary", "md", "summary.md", "live_playback", True, "summary", "Activity 23 summary."),
        _manifest_row("manifest", "csv", "live_playback_manifest.csv", "live_playback", True, "manifest", "Activity 23 manifest."),
        _manifest_row("live_tracks", "csv", "live_tracks.csv", playback_config.tracks_csv, True, "data", f"{len(context['tracks'])} normalized track rows."),
        _manifest_row("live_events", "json", "live_events.json", playback_config.events_json, True, "data", f"{len(context['events'])} normalized events."),
        _manifest_row("live_highlights", "csv", "live_highlights.csv", playback_config.highlights_csv, True, "data", f"{len(context['highlights'])} normalized highlights."),
        _manifest_row("minimap_sample", "json", "minimap_frame_sample.json", "live_tracks.csv", True, "data", "Sample minimap payload for first frame with rectified points."),
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
        f"- Video local existe: `{str(summary['video_exists']).lower()}`.",
        f"- Tracks normalizados: `{summary['track_rows']}`.",
        f"- Eventos normalizados: `{summary['event_count']}`.",
        f"- Highlights normalizados: `{summary['highlight_count']}`.",
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
        "- `config.yaml`.",
        "- `live_playback_manifest.csv`.",
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


def run_smoke_test(root: Path, config_path: Path, output_dir: Path, clip_id: str | None = None) -> dict[str, Any]:
    project_config = load_config(root / config_path)
    playback_config = live_playback_config_from_project(root, project_config, output_dir, clip_id=clip_id)
    return build_live_playback_package(root, config_path, playback_config)


def serve_live_playback_app(root: Path, config_path: Path, output_dir: Path, host: str, port: int, clip_id: str | None = None) -> None:
    context = run_smoke_test(root, config_path, output_dir, clip_id=clip_id)
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

        def _send_json(self, payload: dict[str, Any]) -> None:
            self._send_text(json.dumps(payload, ensure_ascii=True), "application/json; charset=utf-8")

        def _send_video(self, query: str) -> None:
            params = parse_qs(query)
            clip_id = _first(params, "clip_id", "")
            config: LivePlaybackConfig = context["config"]
            if clip_id and clip_id != config.clip_id:
                self.send_error(404, "clip not configured")
                return
            video = resolve_configured_video(config)
            if not video or not video.exists() or not video.is_file():
                self.send_error(404, "configured video not found")
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
.timeline{display:flex;flex-direction:column;gap:8px;max-height:260px;overflow:auto}.event{border-left:3px solid var(--accent);background:#111611;padding:8px;font-size:12px;color:var(--muted)}.event strong{color:var(--text)}
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
const timeReadout=document.getElementById('timeReadout');
const dataReadout=document.getElementById('dataReadout');
const syncState=document.getElementById('syncState');
const byFrame=new Map();
for(const row of data.tracks){const f=Number(row.frame);if(!byFrame.has(f))byFrame.set(f,[]);byFrame.get(f).push(row);}
function enabled(id){return document.getElementById(id)?.checked;}
function frameNow(){const fps=Number(data.config.fps)||30;return Math.round((video.currentTime||0)*fps);}
function resizeCanvas(){const rect=video.getBoundingClientRect();const fallbackW=data.config.width||960;const fallbackH=data.config.height||540;canvas.width=Math.max(1,Math.round(rect.width||fallbackW));canvas.height=Math.max(1,Math.round(rect.height||fallbackH));}
function scaleX(x){return Number(x)*(canvas.width/(data.config.width||canvas.width));}
function scaleY(y){return Number(y)*(canvas.height/(data.config.height||canvas.height));}
function activeEvents(frame){return data.events.filter(e=>Number(e.start_frame)<=frame&&Number(e.end_frame)>=frame);}
function activeHighlights(frame){return data.highlights.filter(e=>Number(e.start_frame)<=frame&&Number(e.end_frame)>=frame);}
function draw(){resizeCanvas();ctx.clearRect(0,0,canvas.width,canvas.height);const frame=frameNow();const rows=byFrame.get(frame)||nearestRows(frame);const events=activeEvents(frame);const highlights=activeHighlights(frame);frameReadout.textContent=String(frame);timeReadout.textContent=(video.currentTime||0).toFixed(3)+'s';dataReadout.textContent=rows.length+' tracks | '+events.length+' eventos';syncState.textContent=rows.length?'replaying_cache':'delayed';if(enabled('layerTrails'))drawTrails(frame);if(enabled('layerTracks'))drawTracks(rows);if(enabled('layerBall'))drawBall(rows);if(enabled('layerEvents'))drawEvents(events);if(enabled('layerPossession'))drawPossession(events);if(enabled('layerHighlights'))drawHighlights(highlights);if(enabled('layerMinimap'))drawMinimap(rows);if(enabled('layerDebug'))drawDebug(frame,rows);renderEventList(events,highlights);requestAnimationFrame(draw);}
function nearestRows(frame){for(let gap=1;gap<=3;gap++){if(byFrame.has(frame-gap))return byFrame.get(frame-gap);if(byFrame.has(frame+gap))return byFrame.get(frame+gap);}return [];}
function drawTracks(rows){for(const row of rows){if(row.class==='ball')continue;const x=scaleX(row.x),y=scaleY(row.y),w=scaleX(row.w),h=scaleY(row.h);ctx.strokeStyle=row.team==='blue'?'#48a6ff':(row.team==='red'?'#ff6b6b':'#64d47c');ctx.lineWidth=2;ctx.strokeRect(x,y,w,h);ctx.fillStyle=ctx.strokeStyle;ctx.beginPath();ctx.arc(scaleX(row.center_x),scaleY(row.center_y),3,0,Math.PI*2);ctx.fill();if(enabled('layerIds'))label(row.track_id,x,y-6,ctx.strokeStyle);}}
function drawBall(rows){for(const row of rows.filter(r=>r.class==='ball')){const x=scaleX(row.center_x),y=scaleY(row.center_y);ctx.fillStyle='#f4c430';ctx.strokeStyle='#10130f';ctx.lineWidth=3;ctx.beginPath();ctx.arc(x,y,8,0,Math.PI*2);ctx.fill();ctx.stroke();if(enabled('layerIds'))label(row.track_id,x+10,y,'#f4c430');}}
function drawTrails(frame){const start=frame-(data.config.trail_length||16);const trails=new Map();for(const row of data.tracks){const f=Number(row.frame);if(f<start||f>frame)continue;if(!trails.has(row.track_id))trails.set(row.track_id,[]);trails.get(row.track_id).push(row);}for(const points of trails.values()){if(points.length<2)continue;ctx.beginPath();points.forEach((p,i)=>{const x=scaleX(p.center_x),y=scaleY(p.center_y);if(i===0)ctx.moveTo(x,y);else ctx.lineTo(x,y);});ctx.strokeStyle='rgba(244,196,48,.42)';ctx.lineWidth=2;ctx.stroke();}}
function drawEvents(events){let top=14;for(const event of events){const text=event.label+' '+event.status;badge(text,14,top,'#f4c430');top+=30;}}
function drawPossession(events){const possession=events.find(e=>(e.label||'').includes('possession')||(e.reason||'').includes('posesion'));if(!possession)return;badge('posesion candidata: '+(possession.team||'unknown'),14,canvas.height-42,'#64d47c');}
function drawHighlights(highlights){for(const hl of highlights){badge('highlight #'+hl.rank+' '+Number(hl.score).toFixed(1),canvas.width-190,14,'#ff6b6b');}}
function drawMinimap(rows){const w=150,h=96,x=canvas.width-w-14,y=canvas.height-h-14;ctx.fillStyle='rgba(13,16,13,.86)';ctx.fillRect(x,y,w,h);ctx.strokeStyle='#aab6a4';ctx.strokeRect(x,y,w,h);ctx.strokeStyle='rgba(170,182,164,.3)';ctx.beginPath();ctx.moveTo(x+w/2,y);ctx.lineTo(x+w/2,y+h);ctx.stroke();for(const row of rows){if(row.x_norm===''||row.y_norm==='')continue;ctx.fillStyle=row.class==='ball'?'#f4c430':(row.team==='blue'?'#48a6ff':'#64d47c');ctx.beginPath();ctx.arc(x+Number(row.x_norm)*w,y+Number(row.y_norm)*h,row.class==='ball'?4:3,0,Math.PI*2);ctx.fill();}}
function drawDebug(frame,rows){label('fps='+data.config.fps+' rows='+rows.length+' frame='+frame,12,canvas.height-12,'#edf2e9');}
function label(text,x,y,color){ctx.font='12px system-ui';ctx.fillStyle='rgba(5,6,5,.78)';const width=ctx.measureText(text).width+8;ctx.fillRect(x,y-13,width,17);ctx.fillStyle=color;ctx.fillText(text,x+4,y);}
function badge(text,x,y,color){ctx.font='13px system-ui';const width=Math.min(canvas.width-24,ctx.measureText(text).width+18);ctx.fillStyle='rgba(5,6,5,.82)';ctx.fillRect(x,y,width,24);ctx.strokeStyle=color;ctx.strokeRect(x,y,width,24);ctx.fillStyle='#edf2e9';ctx.fillText(text,x+8,y+16);}
function renderEventList(events,highlights){const list=document.getElementById('eventList');list.innerHTML='';for(const item of [...events,...highlights].slice(0,6)){const div=document.createElement('div');div.className='event';div.innerHTML='<strong>'+escapeHtml(item.label||item.highlight_id)+'</strong><br>frames '+(item.start_frame||item.start_frame)+'-'+(item.end_frame||item.end_frame)+' | '+(item.status||'provisional');list.appendChild(div);}}
function escapeHtml(text){return String(text).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',\"'\":'&#39;'}[c]));}
if(!data.config.video_exists){missing.hidden=false;}
video.addEventListener('loadedmetadata',resizeCanvas);
window.addEventListener('resize',resizeCanvas);
for(const input of document.querySelectorAll('input[type=checkbox]'))input.addEventListener('change',draw);
requestAnimationFrame(draw);
"""


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
