from __future__ import annotations

import csv
import html
import json
import mimetypes
import os
import re
import sys
from dataclasses import asdict, dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, quote, unquote, urlparse

from futbotmx.config import load_config, write_config_snapshot
from futbotmx.level3.spatial import (
    FIELD_POINTS,
    ClipCalibration,
    ClipSpatialSpec,
    FieldModel,
    build_calibration_from_tracks,
    estimate_manual_calibration_confidence,
    solve_homography,
)
from futbotmx.tracking import read_tracks_csv
from futbotmx.ui import shared_css, ui_body_attrs


RULE_VERSION = "manual_field_calibration_v0.1"
DEFAULT_OUTPUT_DIR = Path("experiments/test_029_manual_calibration")
DEFAULT_SOURCE_DIR = Path("experiments/test_017_level2_closure")
DEFAULT_CLIPS = ("video_595", "video_667")
MANIFEST_FIELDS = ["asset_id", "asset_type", "path", "source_artifact", "is_versioned", "role", "notes"]


@dataclass(frozen=True)
class CalibrationEditorClip:
    clip_id: str
    role: str
    width: int
    height: int
    fps: float
    overlay_path: str
    overlay_static_path: str
    overlay_server_path: str
    overlay_frame: int
    image_points: tuple[tuple[float, float], ...]
    confidence: float
    notes: str


@dataclass(frozen=True)
class CalibrationEditorContext:
    rule_version: str
    output_dir: str
    source_dir: str
    field_model: dict[str, Any]
    clips: list[CalibrationEditorClip]
    calibration_json: str
    editor_html: str
    manifest_csv: str


def clip_specs_from_config(config: dict[str, Any], selected_clips: tuple[str, ...]) -> dict[str, ClipSpatialSpec]:
    specs: dict[str, ClipSpatialSpec] = {}
    closure_clips = config.get("level2_closure", {}).get("clips", [])
    for raw in closure_clips:
        clip_id = str(raw.get("clip_id", ""))
        if clip_id not in selected_clips:
            continue
        specs[clip_id] = ClipSpatialSpec(
            clip_id=clip_id,
            width=int(raw["width"]),
            height=int(raw["height"]),
            fps=float(raw["fps"]),
            role=str(raw.get("role", "dense_candidate")),
        )
    missing = [clip_id for clip_id in selected_clips if clip_id not in specs]
    if missing:
        raise ValueError(f"Missing clip metadata for: {', '.join(missing)}")
    return specs


def build_calibration_editor(
    config_path: str | Path,
    source_dir: Path,
    output_dir: Path,
    clips: tuple[str, ...],
) -> CalibrationEditorContext:
    config = load_config(config_path)
    specs = clip_specs_from_config(config, clips)
    output_dir.mkdir(parents=True, exist_ok=True)
    field_model = FieldModel(zone_axis=str(config.get("level2_events", {}).get("zone_axis", "y")))
    seed_calibrations: dict[str, ClipCalibration] = {}
    editor_clips: list[CalibrationEditorClip] = []

    for clip_id in clips:
        spec = specs[clip_id]
        tracks_path = source_dir / clip_id / "tracks_level2.csv"
        if not tracks_path.exists():
            raise FileNotFoundError(f"Missing tracks for {clip_id}: {tracks_path}")
        rows = read_tracks_csv(tracks_path)
        automatic = build_calibration_from_tracks(clip_id, rows, spec)
        seed = manual_seed_from_calibration(automatic, spec)
        seed_calibrations[clip_id] = seed
        overlay_path, overlay_frame = find_reference_overlay(source_dir, clip_id)
        editor_clips.append(
            CalibrationEditorClip(
                clip_id=clip_id,
                role=spec.role,
                width=spec.width,
                height=spec.height,
                fps=spec.fps,
                overlay_path=overlay_path.as_posix(),
                overlay_static_path=Path(os.path.relpath(overlay_path, start=output_dir)).as_posix(),
                overlay_server_path="/artifact?path=" + quote(overlay_path.as_posix()),
                overlay_frame=overlay_frame,
                image_points=seed.image_points,
                confidence=seed.confidence,
                notes=seed.notes,
            )
        )

    context = CalibrationEditorContext(
        rule_version=RULE_VERSION,
        output_dir=output_dir.as_posix(),
        source_dir=source_dir.as_posix(),
        field_model=field_model.to_dict(),
        clips=editor_clips,
        calibration_json="field_calibration.json",
        editor_html="calibration_editor.html",
        manifest_csv="calibration_editor_manifest.csv",
    )
    write_editor_config(config, output_dir, source_dir, clips)
    write_seed_calibration_json(output_dir / context.calibration_json, field_model, seed_calibrations)
    (output_dir / context.editor_html).write_text(render_calibration_editor_html(context), encoding="utf-8")
    manifest = write_editor_manifest(output_dir / context.manifest_csv, context)
    write_editor_summary(output_dir / "summary.md", context, manifest)
    return context


def manual_seed_from_calibration(calibration: ClipCalibration, spec: ClipSpatialSpec) -> ClipCalibration:
    image_points = calibration.image_points
    confidence = estimate_manual_calibration_confidence(image_points, spec)
    homography = solve_homography(image_points, FIELD_POINTS) if len(image_points) >= 4 else None
    return ClipCalibration(
        clip_id=calibration.clip_id,
        calibration_id=f"{calibration.clip_id}_manual_four_corner_seed_v0.1",
        method="manual_four_corner_homography_seed",
        status="usable" if homography else "fallback",
        confidence=confidence,
        image_width=spec.width,
        image_height=spec.height,
        image_points=image_points,
        field_points=FIELD_POINTS,
        homography=homography,
        notes=(
            "Seeded from automatic field bbox for the manual editor. "
            "Replace the four corners in the browser editor for human-reviewed calibration."
        ),
    )


def find_reference_overlay(source_dir: Path, clip_id: str) -> tuple[Path, int]:
    clip_dir = source_dir / clip_id
    candidates: list[tuple[int, Path]] = []
    for path in sorted(clip_dir.glob("overlay_*_frame_*.png")):
        match = re.search(r"_frame_(\d+)\.png$", path.name)
        if match:
            candidates.append((int(match.group(1)), path))
    if not candidates:
        raise FileNotFoundError(f"No lightweight overlay PNG found for {clip_id} in {clip_dir}")
    return min(candidates, key=lambda item: (abs(item[0] - 120), item[0]))[1], min(candidates, key=lambda item: (abs(item[0] - 120), item[0]))[0]


def write_seed_calibration_json(path: Path, field_model: FieldModel, calibrations: dict[str, ClipCalibration]) -> None:
    payload = {
        "rule_version": RULE_VERSION,
        "review_status": "draft_seed",
        "field_model": field_model.to_dict(),
        "editor_notes": [
            "This file is valid input for scripts/run_level3_spatial_model.py --calibration-json.",
            "Initial points are automatic seeds; save from the editor after human review to replace them.",
        ],
        "clips": {clip_id: calibration.to_dict() for clip_id, calibration in calibrations.items()},
    }
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")


def save_manual_calibration_payload(payload: dict[str, Any], path: Path, field_model: FieldModel | None = None) -> None:
    clips = payload.get("clips", {})
    if not isinstance(clips, dict) or not clips:
        raise ValueError("Calibration payload must include clips")
    output_clips: dict[str, Any] = {}
    model = field_model or FieldModel()
    for clip_id, raw in clips.items():
        if not isinstance(raw, dict):
            continue
        points = _points_from_payload(raw.get("image_points", []))
        if len(points) < 4:
            raise ValueError(f"{clip_id} requires four image points")
        field_points = _points_from_payload(raw.get("field_points", []), norm=True) or list(FIELD_POINTS)
        homography = solve_homography(points[:4], field_points[:4])
        output_clips[str(clip_id)] = {
            "clip_id": str(clip_id),
            "calibration_id": str(raw.get("calibration_id", f"{clip_id}_manual_four_corner_v0.1")),
            "method": "manual_four_corner_homography",
            "status": "usable",
            "confidence": raw.get("confidence", ""),
            "image_size": raw.get("image_size", {}),
            "image_points": [
                {"label": label, "x": round(point[0], 6), "y": round(point[1], 6)}
                for label, point in zip(("top_left", "top_right", "bottom_right", "bottom_left"), points[:4])
            ],
            "field_points": [
                {"label": label, "x_norm": point[0], "y_norm": point[1]}
                for label, point in zip(("top_left", "top_right", "bottom_right", "bottom_left"), field_points[:4])
            ],
            "homography": homography,
            "notes": "Saved from FutBotMX local manual calibration editor.",
        }
    output = {
        "rule_version": RULE_VERSION,
        "review_status": "human_saved",
        "field_model": model.to_dict(),
        "clips": output_clips,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(output, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")


def render_calibration_editor_html(context: CalibrationEditorContext) -> str:
    clips_json = json.dumps([_clip_to_dict(clip) for clip in context.clips], ensure_ascii=True)
    return "\n".join(
        [
            "<!doctype html>",
            '<html lang="es">',
            "<head>",
            '<meta charset="utf-8">',
            '<meta name="viewport" content="width=device-width, initial-scale=1">',
            "<title>FutBotMX Calibracion Manual</title>",
            f"<style>{_css()}</style>",
            "</head>",
            f'<body {ui_body_attrs("review", "calibration-page")}>',
            '<main class="shell fb-shell">',
            '<header class="fb-topbar">',
            "<div>",
            "<p>FutBotMX Nivel 3</p>",
            "<h1>Calibracion manual de cancha</h1>",
            "</div>",
            f"<span>{_esc(context.rule_version)}</span>",
            "</header>",
            '<section class="workspace">',
            '<aside class="panel">',
            "<h2>Clip</h2>",
            '<select id="clipSelect"></select>',
            '<div id="clipMeta" class="meta"></div>',
            '<div class="buttons">',
            '<div class="button-row">',
            '<button type="button" id="downloadBtn" class="btn-secondary">Descargar JSON</button>',
            '<button type="button" id="saveBtn" class="btn-primary">Guardar</button>',
            "</div>",
            '<button type="button" id="resetBtn" class="btn-danger">Reset puntos</button>',
            "</div>",
            '<ol id="pointList"></ol>',
            '<p id="saveStatus" class="muted"></p>',
            "</aside>",
            '<section class="panel canvasPanel">',
            '<canvas id="fieldCanvas"></canvas>',
            "</section>",
            "</section>",
            "</main>",
            f"<script>window.CALIBRATION_CLIPS = {clips_json};{_js()}</script>",
            "</body>",
            "</html>",
        ]
    ) + "\n"


def write_editor_config(config: dict[str, Any], output_dir: Path, source_dir: Path, clips: tuple[str, ...]) -> None:
    snapshot = dict(config)
    snapshot["manual_field_calibration"] = {
        "rule_version": RULE_VERSION,
        "source_dir": source_dir.as_posix(),
        "output_dir": output_dir.as_posix(),
        "clips": list(clips),
        "editor": "calibration_editor.html",
        "calibration_json": "field_calibration.json",
        "outputs": [
            "calibration_editor.html",
            "field_calibration.json",
            "calibration_editor_manifest.csv",
            "config.yaml",
            "summary.md",
        ],
    }
    write_config_snapshot(snapshot, output_dir / "config.yaml")


def write_editor_manifest(path: Path, context: CalibrationEditorContext) -> list[dict[str, Any]]:
    rows = [
        _manifest_row("config", "yaml", "config.yaml", "configs/default.yaml", True, "configuration", "Configuration snapshot."),
        _manifest_row("calibration_editor", "html", context.editor_html, context.calibration_json, True, "editor", "Browser point editor."),
        _manifest_row("field_calibration", "json", context.calibration_json, "automatic seed/manual editor", True, "manual_input", "Manual calibration JSON input."),
        _manifest_row("summary", "md", "summary.md", context.editor_html, True, "summary", "Editor summary."),
        _manifest_row("manifest", "csv", context.manifest_csv, context.editor_html, True, "manifest", "Editor artifact manifest."),
    ]
    for clip in context.clips:
        rows.append(
            _manifest_row(
                f"{clip.clip_id}_overlay",
                "png",
                clip.overlay_static_path,
                clip.overlay_path,
                True,
                "reference_overlay",
                f"Frame {clip.overlay_frame} lightweight overlay for point selection.",
            )
        )
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=MANIFEST_FIELDS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    return rows


def write_editor_summary(path: Path, context: CalibrationEditorContext, manifest: list[dict[str, Any]]) -> None:
    lines = [
        "# Calibracion Manual De Cancha",
        "",
        "## Resultado",
        "",
        "- Estado: `editor_generado`.",
        f"- Regla: `{RULE_VERSION}`.",
        f"- Clips: `{', '.join(clip.clip_id for clip in context.clips)}`.",
        "- Entrada editable: `field_calibration.json`.",
        "- Editor: `calibration_editor.html`.",
        "",
        "## Uso",
        "",
        "```bash",
        ".venv/bin/python scripts/run_field_calibration_editor.py",
        "```",
        "",
        "Abrir el editor local, seleccionar cuatro esquinas en orden `top_left`, `top_right`, `bottom_right`, `bottom_left` y guardar el JSON.",
        "",
        "## Integracion",
        "",
        "```bash",
        ".venv/bin/python scripts/run_level3_spatial_model.py --calibration-json experiments/test_029_manual_calibration/field_calibration.json --experiment experiments/test_030_manual_spatial_model",
        "```",
        "",
        "## Clips",
        "",
    ]
    for clip in context.clips:
        lines.append(
            f"- `{clip.clip_id}` frame `{clip.overlay_frame}` overlay `{clip.overlay_static_path}` confianza seed `{clip.confidence}`."
        )
    lines.extend(
        [
            "",
            "## Manifest",
            "",
            f"- Filas en `calibration_editor_manifest.csv`: `{len(manifest)}`.",
            "",
            "## Limitaciones",
            "",
            "- Los puntos iniciales son una semilla automatica; deben revisarse visualmente antes de tratarlos como calibracion humana.",
            "- El editor trabaja sobre overlays ligeros versionados, no sobre video completo.",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def serve_calibration_editor(root: Path, output_dir: Path, host: str, port: int) -> None:
    handler = make_editor_handler(root, output_dir)
    server = ThreadingHTTPServer((host, port), handler)
    actual_host, actual_port = server.server_address
    display_host = host if host != "0.0.0.0" else actual_host
    print(f"FutBotMX calibration editor: http://{display_host}:{actual_port}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("Stopping FutBotMX calibration editor", flush=True)
    finally:
        server.server_close()


def make_editor_handler(root: Path, output_dir: Path) -> type[BaseHTTPRequestHandler]:
    class CalibrationEditorHandler(BaseHTTPRequestHandler):
        server_version = "FutBotMXCalibrationEditor/0.1"

        def do_GET(self) -> None:
            parsed = urlparse(self.path)
            if parsed.path in {"/", "/calibration_editor.html"}:
                self._send_file(output_dir / "calibration_editor.html", "text/html; charset=utf-8")
                return
            if parsed.path == "/artifact":
                self._send_artifact(parsed.query)
                return
            if parsed.path == "/health":
                self._send_text("ok\n", "text/plain; charset=utf-8")
                return
            self.send_error(404)

        def do_POST(self) -> None:
            parsed = urlparse(self.path)
            if parsed.path != "/save-calibration":
                self.send_error(404)
                return
            length = int(self.headers.get("Content-Length", "0") or "0")
            payload = json.loads(self.rfile.read(length).decode("utf-8"))
            try:
                save_manual_calibration_payload(payload, output_dir / "field_calibration.json")
            except Exception as exc:
                self.send_error(400, str(exc))
                return
            self._send_text('{"status":"ok"}\n', "application/json; charset=utf-8")

        def log_message(self, format: str, *args: Any) -> None:
            sys.stderr.write("calibration_editor: " + format % args + "\n")

        def _send_artifact(self, query: str) -> None:
            params = parse_qs(query)
            requested = unquote(params.get("path", [""])[0])
            try:
                path = resolve_repo_path(root, requested)
            except (FileNotFoundError, ValueError) as exc:
                self.send_error(404, str(exc))
                return
            self._send_file(path, mimetypes.guess_type(path.as_posix())[0] or "application/octet-stream")

        def _send_file(self, path: Path, content_type: str) -> None:
            if not path.exists() or not path.is_file():
                self.send_error(404)
                return
            body = path.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _send_text(self, payload: str, content_type: str) -> None:
            body = payload.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    return CalibrationEditorHandler


def resolve_repo_path(root: Path, requested_path: str) -> Path:
    root_resolved = root.resolve()
    candidate = (root_resolved / requested_path).resolve()
    if not candidate.is_relative_to(root_resolved):
        raise ValueError("path outside repository")
    if not candidate.exists() or not candidate.is_file():
        raise FileNotFoundError(requested_path)
    return candidate


def _points_from_payload(raw_points: Any, norm: bool = False) -> list[tuple[float, float]]:
    if not isinstance(raw_points, list):
        return []
    points: list[tuple[float, float]] = []
    for point in raw_points:
        if not isinstance(point, dict):
            continue
        if "x" in point and "y" in point:
            points.append((float(point["x"]), float(point["y"])))
        elif norm and "x_norm" in point and "y_norm" in point:
            points.append((float(point["x_norm"]), float(point["y_norm"])))
    return points


def _clip_to_dict(clip: CalibrationEditorClip) -> dict[str, Any]:
    data = asdict(clip)
    data["image_points"] = [
        {"label": label, "x": point[0], "y": point[1]}
        for label, point in zip(("top_left", "top_right", "bottom_right", "bottom_left"), clip.image_points)
    ]
    data["field_points"] = [
        {"label": label, "x_norm": point[0], "y_norm": point[1]}
        for label, point in zip(("top_left", "top_right", "bottom_right", "bottom_left"), FIELD_POINTS)
    ]
    return data


def _manifest_row(asset_id: str, asset_type: str, path: str, source_artifact: str, is_versioned: bool, role: str, notes: str) -> dict[str, Any]:
    return {
        "asset_id": asset_id,
        "asset_type": asset_type,
        "path": path,
        "source_artifact": source_artifact,
        "is_versioned": str(is_versioned).lower(),
        "role": role,
        "notes": notes,
    }


def _esc(value: Any) -> str:
    return html.escape(str(value), quote=True)


def _css() -> str:
    return shared_css() + """
:root {
  --ink: #05261d;
  --muted: #52665d;
  --line: #c7e2d1;
  --field: #e9ffd8;
  --panel: #ffffff;
  --page: #f5f9ef;
  --green: #00d25b;
  --blue: #00c853;
}
* { box-sizing: border-box; }
body {
  margin: 0;
  background:
    linear-gradient(90deg, rgba(0,200,83,.08) 1px, transparent 1px),
    linear-gradient(180deg, rgba(0,75,58,.07) 1px, transparent 1px),
    linear-gradient(90deg, rgba(183,243,0,.18) 0 24%, transparent 24%),
    radial-gradient(circle at 84% 0%, rgba(0,75,58,.14), transparent 30%),
    var(--page);
  background-size: 52px 52px, 52px 52px, auto, auto, auto;
  color: var(--ink);
  font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
}
.shell {
  width: min(1280px, calc(100vw - 28px));
  margin: 0 auto;
  padding: 22px 0 34px;
}
header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 14px;
  border: 1px solid var(--line);
  border-bottom: 4px solid #b7f300;
  border-radius: 8px;
  padding: 16px;
  background: linear-gradient(135deg, #004b3a, #00c853);
  color: #ffffff;
}
header p {
  margin: 0 0 4px;
  color: #eaffd6;
  font-size: 13px;
  font-weight: 800;
  text-transform: uppercase;
}
h1 {
  margin: 0;
  font-size: 32px;
  line-height: 1.1;
  letter-spacing: 0;
  color: inherit;
}
h2 {
  margin: 0 0 10px;
  font-size: 18px;
  letter-spacing: 0;
}
.workspace {
  display: grid;
  grid-template-columns: minmax(260px, 320px) minmax(0, 1fr);
  gap: 12px;
  margin-top: 16px;
}
.panel {
  border: 1px solid var(--line);
  border-radius: 8px;
  background: var(--panel);
  padding: 14px;
}
select,
button {
  width: 100%;
  min-height: 38px;
  border-radius: 6px;
  border: 1px solid var(--line);
  font: inherit;
}
select {
  padding: 7px 9px;
}
button {
  cursor: pointer;
  font-weight: 800;
  background: #fff;
  color: var(--green);
  border-color: var(--line);
}
.buttons {
  display: grid;
  gap: 8px;
  margin-top: 12px;
}
.button-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
}
.btn-primary {
  background: var(--green);
  color: #fff;
  border-color: #008f43;
}
.btn-secondary {
  color: var(--blue);
  border-color: #93c4ef;
}
.btn-danger {
  color: #b7f300;
  border-color: #f3a9bd;
  background: #fff2f5;
}
.meta,
.muted,
ol {
  color: var(--muted);
  font-size: 13px;
}
ol {
  padding-left: 22px;
}
li {
  margin-bottom: 7px;
}
.canvasPanel {
  overflow: auto;
  min-height: 520px;
}
canvas {
  width: 100%;
  height: auto;
  display: block;
  background: var(--field);
  border: 1px solid var(--line);
}
a {
  color: var(--blue);
}
@media (max-width: 900px) {
  .workspace {
    grid-template-columns: 1fr;
  }
  .canvasPanel {
    min-height: 0;
  }
}
@media (max-width: 540px) {
  .button-row {
    grid-template-columns: 1fr;
  }
}
"""


def _js() -> str:
    return """
const labels = ["top_left", "top_right", "bottom_right", "bottom_left"];
let clips = window.CALIBRATION_CLIPS || [];
let active = 0;
let pointsByClip = {};
const canvas = document.getElementById("fieldCanvas");
const ctx = canvas.getContext("2d");
const select = document.getElementById("clipSelect");
const pointList = document.getElementById("pointList");
const meta = document.getElementById("clipMeta");
const statusNode = document.getElementById("saveStatus");
const image = new Image();

function init() {
  clips.forEach((clip, index) => {
    const option = document.createElement("option");
    option.value = String(index);
    option.textContent = `${clip.clip_id} | frame ${clip.overlay_frame}`;
    select.appendChild(option);
    pointsByClip[clip.clip_id] = (clip.image_points || []).map((point) => ({...point}));
  });
  select.addEventListener("change", () => {
    active = Number(select.value);
    loadClip();
  });
  canvas.addEventListener("click", recordPoint);
  document.getElementById("resetBtn").addEventListener("click", resetPoints);
  document.getElementById("downloadBtn").addEventListener("click", downloadJson);
  document.getElementById("saveBtn").addEventListener("click", saveJson);
  loadClip();
}

function currentClip() {
  return clips[active];
}

function clipImageSource(clip) {
  if (window.location.protocol === "http:" || window.location.protocol === "https:") {
    return clip.overlay_server_path;
  }
  return clip.overlay_static_path;
}

function loadClip() {
  const clip = currentClip();
  meta.innerHTML = `Resolucion ${clip.width}x${clip.height}<br>Overlay: <a href="${clipImageSource(clip)}">${clip.overlay_frame}</a><br>Confianza seed: ${clip.confidence}`;
  image.onload = () => {
    canvas.width = image.naturalWidth;
    canvas.height = image.naturalHeight;
    draw();
  };
  image.src = clipImageSource(clip);
  renderPoints();
}

function draw() {
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  ctx.drawImage(image, 0, 0);
  const points = pointsByClip[currentClip().clip_id] || [];
  ctx.lineWidth = 4;
  ctx.strokeStyle = "#f5c542";
  ctx.fillStyle = "#111111";
  if (points.length > 1) {
    ctx.beginPath();
    ctx.moveTo(points[0].x, points[0].y);
    points.slice(1).forEach((point) => ctx.lineTo(point.x, point.y));
    if (points.length === 4) ctx.closePath();
    ctx.stroke();
  }
  points.forEach((point, index) => {
    ctx.beginPath();
    ctx.arc(point.x, point.y, 11, 0, Math.PI * 2);
    ctx.fillStyle = "#f5c542";
    ctx.fill();
    ctx.lineWidth = 3;
    ctx.strokeStyle = "#111111";
    ctx.stroke();
    ctx.fillStyle = "#111111";
    ctx.font = "18px sans-serif";
    ctx.fillText(String(index + 1), point.x + 14, point.y - 14);
  });
}

function recordPoint(event) {
  const clip = currentClip();
  const rect = canvas.getBoundingClientRect();
  const x = (event.clientX - rect.left) * (canvas.width / rect.width);
  const y = (event.clientY - rect.top) * (canvas.height / rect.height);
  const points = pointsByClip[clip.clip_id] || [];
  const next = points.length >= 4 ? [] : points;
  next.push({label: labels[next.length], x: Math.round(x * 1000) / 1000, y: Math.round(y * 1000) / 1000});
  pointsByClip[clip.clip_id] = next;
  renderPoints();
  draw();
}

function resetPoints() {
  const clip = currentClip();
  pointsByClip[clip.clip_id] = (clip.image_points || []).map((point) => ({...point}));
  renderPoints();
  draw();
}

function renderPoints() {
  const points = pointsByClip[currentClip().clip_id] || [];
  pointList.innerHTML = "";
  labels.forEach((label, index) => {
    const point = points[index];
    const item = document.createElement("li");
    item.textContent = point ? `${label}: ${point.x}, ${point.y}` : `${label}: sin punto`;
    pointList.appendChild(item);
  });
}

function buildPayload() {
  const payload = {rule_version: "manual_field_calibration_v0.1", review_status: "human_saved", clips: {}};
  clips.forEach((clip) => {
    const points = (pointsByClip[clip.clip_id] || []).slice(0, 4);
    payload.clips[clip.clip_id] = {
      clip_id: clip.clip_id,
      calibration_id: `${clip.clip_id}_manual_four_corner_v0.1`,
      image_size: {width: clip.width, height: clip.height},
      image_points: points,
      field_points: clip.field_points,
      notes: "Saved from FutBotMX local manual calibration editor."
    };
  });
  return payload;
}

function downloadJson() {
  const blob = new Blob([JSON.stringify(buildPayload(), null, 2) + "\\n"], {type: "application/json"});
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = "field_calibration.json";
  link.click();
  URL.revokeObjectURL(url);
}

async function saveJson() {
  if (!(window.location.protocol === "http:" || window.location.protocol === "https:")) {
    downloadJson();
    statusNode.textContent = "Archivo descargado; abre el editor con el servidor local para guardar directo.";
    return;
  }
  const response = await fetch("/save-calibration", {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify(buildPayload())
  });
  statusNode.textContent = response.ok ? "field_calibration.json guardado." : "No se pudo guardar.";
}

init();
"""
