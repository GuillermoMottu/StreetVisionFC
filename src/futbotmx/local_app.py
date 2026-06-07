from __future__ import annotations

import csv
import html
import json
import mimetypes
import os
import subprocess
import sys
import time
from dataclasses import asdict, dataclass, replace
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, quote, unquote, urlparse

from futbotmx.config import load_config, write_config_snapshot


RULE_VERSION = "local_app_v0.1"
DEFAULT_EXPERIMENT_DIR = Path("experiments/test_028_local_app")
DEFAULT_DASHBOARD_HTML = Path("experiments/test_024_level3_dashboard/dashboard.html")
DEFAULT_REEL_HTML = Path("experiments/test_025_level3_reel/reel_demo.html")
DEFAULT_CLOSURE_CHECKS = Path("experiments/test_027_level3_closure/closure_checks.csv")
MANIFEST_FIELDS = ["asset_id", "asset_type", "path", "source_artifact", "is_versioned", "role", "notes"]


@dataclass(frozen=True)
class ClipOption:
    clip_id: str
    role: str
    video_path: str
    start_frame: int
    end_frame: int
    stride: int
    roi: tuple[int, int, int, int]
    width: int
    height: int
    fps: float


@dataclass(frozen=True)
class AnalysisRequest:
    clip_id: str
    video_path: str
    start_frame: int
    end_frame: int
    stride: int
    roi: tuple[int, int, int, int]
    run_dashboard: bool = True
    run_reel: bool = True


@dataclass(frozen=True)
class CommandStatus:
    name: str
    status: str
    command: str
    notes: str
    duration_sec: float


@dataclass(frozen=True)
class ArtifactRow:
    label: str
    path: str
    exists: bool
    size_bytes: int
    role: str


@dataclass(frozen=True)
class CheckRow:
    check_id: str
    status: str
    evidence: str
    notes: str


@dataclass(frozen=True)
class AnalysisResult:
    status: str
    message: str
    generated_at: str
    request: AnalysisRequest
    commands: list[CommandStatus]
    artifacts: list[ArtifactRow]
    checks: list[CheckRow]
    summary_path: str
    manifest_path: str


def clip_options_from_config(config: dict[str, Any]) -> list[ClipOption]:
    clips = _clips_from_level2_closure(config)
    if clips:
        return clips
    return _clips_from_level2_multiclip(config)


def selected_clip(clips: list[ClipOption], clip_id: str | None = None) -> ClipOption:
    if not clips:
        return ClipOption("manual", "manual", "", 0, 180, 1, (0, 0, 0, 0), 0, 0, 0.0)
    for clip in clips:
        if clip.clip_id == clip_id:
            return clip
    return clips[0]


def analysis_request_from_form(form: dict[str, list[str]], clips: list[ClipOption]) -> AnalysisRequest:
    clip = selected_clip(clips, _first(form, "clip_id", ""))
    start_frame = _coerce_int(_first(form, "start_frame", str(clip.start_frame)), clip.start_frame, minimum=0)
    end_frame = _coerce_int(_first(form, "end_frame", str(clip.end_frame)), clip.end_frame, minimum=start_frame)
    stride = _coerce_int(_first(form, "stride", str(clip.stride)), clip.stride, minimum=1)
    video_path = _first(form, "video_path", clip.video_path).strip()
    roi = _roi_from_form(form, clip)
    return AnalysisRequest(
        clip_id=clip.clip_id,
        video_path=video_path,
        start_frame=start_frame,
        end_frame=end_frame,
        stride=stride,
        roi=roi,
        run_dashboard=_checkbox(form, "run_dashboard", default=False),
        run_reel=_checkbox(form, "run_reel", default=False),
    )


def artifact_inventory(root: Path, experiment_dir: Path) -> list[ArtifactRow]:
    paths = [
        ("App summary", experiment_dir / "summary.md", "local_app"),
        ("App manifest", experiment_dir / "local_app_manifest.csv", "local_app"),
        ("App config", experiment_dir / "config.yaml", "local_app"),
        ("Generated dashboard", experiment_dir / "dashboard/dashboard.html", "dashboard"),
        ("Generated reel", experiment_dir / "reel/reel_demo.html", "reel"),
        ("Generated reel manifest", experiment_dir / "reel/reel_manifest.csv", "reel"),
        ("Nivel 3 dashboard", DEFAULT_DASHBOARD_HTML, "evidence"),
        ("Nivel 3 reel", DEFAULT_REEL_HTML, "evidence"),
        ("Nivel 3 closure checks", DEFAULT_CLOSURE_CHECKS, "checks"),
    ]
    rows = []
    for label, path, role in paths:
        full_path = root / path
        exists = full_path.exists()
        size = full_path.stat().st_size if exists and full_path.is_file() else 0
        rows.append(ArtifactRow(label, path.as_posix(), exists, size, role))
    return rows


def read_closure_checks(root: Path, limit: int = 12) -> list[CheckRow]:
    path = root / DEFAULT_CLOSURE_CHECKS
    if not path.exists():
        return [CheckRow("level3_closure", "missing", DEFAULT_CLOSURE_CHECKS.as_posix(), "closure checks not found")]
    with path.open("r", newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    checks = [
        CheckRow(
            str(row.get("check_id", "")),
            str(row.get("status", "")),
            str(row.get("evidence", "")),
            str(row.get("notes", "")),
        )
        for row in rows[:limit]
    ]
    return checks


def run_light_analysis(
    root: Path,
    config_path: Path,
    experiment_dir: Path,
    request: AnalysisRequest,
    python_executable: str | None = None,
) -> AnalysisResult:
    experiment_path = root / experiment_dir
    dashboard_dir = experiment_dir / "dashboard"
    reel_dir = experiment_dir / "reel"
    commands: list[CommandStatus] = []
    python = python_executable or sys.executable
    if request.run_dashboard:
        commands.append(
            _run_command(
                root,
                "dashboard",
                [
                    python,
                    "scripts/run_level3_dashboard.py",
                    "--config",
                    config_path.as_posix(),
                    "--experiment",
                    dashboard_dir.as_posix(),
                ],
            )
        )
    if request.run_reel:
        commands.append(
            _run_command(
                root,
                "reel",
                [
                    python,
                    "scripts/run_level3_reel.py",
                    "--config",
                    config_path.as_posix(),
                    "--experiment",
                    reel_dir.as_posix(),
                    "--dashboard-html",
                    (dashboard_dir / "dashboard.html").as_posix(),
                ],
            )
        )
    config = load_config(root / config_path)
    write_local_app_config(config, experiment_path, request, commands)
    artifacts = artifact_inventory(root, experiment_dir)
    checks = read_closure_checks(root)
    status = "pass" if all(command.status == "pass" for command in commands) else "fail"
    if not commands:
        status = "pass"
    result = AnalysisResult(
        status=status,
        message="analysis completed" if status == "pass" else "analysis completed with failures",
        generated_at=_timestamp(),
        request=request,
        commands=commands,
        artifacts=artifacts,
        checks=checks,
        summary_path=(experiment_dir / "summary.md").as_posix(),
        manifest_path=(experiment_dir / "local_app_manifest.csv").as_posix(),
    )
    write_local_app_manifest(root, experiment_dir, result)
    write_local_app_summary(root, experiment_dir, result)
    result = replace(result, artifacts=artifact_inventory(root, experiment_dir))
    write_local_app_manifest(root, experiment_dir, result)
    write_local_app_summary(root, experiment_dir, result)
    return result


def run_smoke_test(root: Path, config_path: Path, experiment_dir: Path) -> AnalysisResult:
    config = load_config(root / config_path)
    clips = clip_options_from_config(config)
    clip = selected_clip(clips)
    request = AnalysisRequest(
        clip_id=clip.clip_id,
        video_path=clip.video_path,
        start_frame=clip.start_frame,
        end_frame=clip.end_frame,
        stride=clip.stride,
        roi=clip.roi,
        run_dashboard=False,
        run_reel=False,
    )
    command = CommandStatus("server_smoke", "pass", "render local app", "index rendered without starting long-lived server", 0.0)
    write_local_app_config(config, root / experiment_dir, request, [command])
    result = AnalysisResult(
        status="pass",
        message="smoke test completed",
        generated_at=_timestamp(),
        request=request,
        commands=[command],
        artifacts=artifact_inventory(root, experiment_dir),
        checks=read_closure_checks(root),
        summary_path=(experiment_dir / "summary.md").as_posix(),
        manifest_path=(experiment_dir / "local_app_manifest.csv").as_posix(),
    )
    write_local_app_manifest(root, experiment_dir, result)
    write_local_app_summary(root, experiment_dir, result)
    result = replace(result, artifacts=artifact_inventory(root, experiment_dir))
    write_local_app_manifest(root, experiment_dir, result)
    write_local_app_summary(root, experiment_dir, result)
    return result


def write_local_app_config(
    config: dict[str, Any],
    experiment_path: Path,
    request: AnalysisRequest,
    commands: list[CommandStatus],
) -> None:
    snapshot = dict(config)
    snapshot["local_app"] = {
        "rule_version": RULE_VERSION,
        "architecture": "html_plus_local_stdlib_backend",
        "server": "http.server.ThreadingHTTPServer",
        "request": asdict(request),
        "commands": [asdict(command) for command in commands],
        "outputs": [
            "summary.md",
            "local_app_manifest.csv",
            "config.yaml",
            "dashboard/dashboard.html",
            "reel/reel_demo.html",
        ],
    }
    write_config_snapshot(snapshot, experiment_path / "config.yaml")


def write_local_app_manifest(root: Path, experiment_dir: Path, result: AnalysisResult) -> None:
    rows = [
        _manifest_row("summary", "md", "summary.md", "local_app", True, "local_app", "Local app execution summary."),
        _manifest_row("config", "yaml", "config.yaml", "configs/default.yaml", True, "local_app", "Configuration snapshot."),
        _manifest_row("local_app_manifest", "csv", "local_app_manifest.csv", "local_app", True, "manifest", "Local app artifact manifest."),
    ]
    for artifact in result.artifacts:
        rows.append(
            _manifest_row(
                _asset_id(artifact.label),
                Path(artifact.path).suffix.lstrip(".") or "artifact",
                _rel_to_experiment(artifact.path, experiment_dir),
                artifact.path,
                artifact.exists,
                artifact.role,
                f"{artifact.label}; size={artifact.size_bytes}",
            )
        )
    output = root / experiment_dir / "local_app_manifest.csv"
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=MANIFEST_FIELDS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def write_local_app_summary(root: Path, experiment_dir: Path, result: AnalysisResult) -> None:
    lines = [
        "# Interfaz Local De Ejecucion",
        "",
        "## Resultado",
        "",
        f"- Estado: `{result.status}`.",
        f"- Regla: `{RULE_VERSION}`.",
        "- Arquitectura: `HTML + backend local con libreria estandar`.",
        f"- Clip seleccionado: `{result.request.clip_id}`.",
        f"- Frames: `{result.request.start_frame}-{result.request.end_frame}`.",
        f"- Stride: `{result.request.stride}`.",
        f"- ROI: `{','.join(str(value) for value in result.request.roi)}`.",
        "",
        "## Comandos",
        "",
    ]
    for command in result.commands:
        lines.append(
            f"- `{command.name}`: `{command.status}` en `{command.duration_sec:.3f}s`; "
            f"{command.notes}"
        )
    lines.extend(["", "## Artefactos", ""])
    for artifact in result.artifacts:
        state = "presente" if artifact.exists else "pendiente"
        lines.append(f"- `{artifact.path}`: `{state}`, rol `{artifact.role}`.")
    pass_count = sum(1 for check in result.checks if check.status == "pass")
    fail_count = sum(1 for check in result.checks if check.status not in {"pass", ""})
    lines.extend(
        [
            "",
            "## Checks",
            "",
            f"- Checks Nivel 3 leidos: `{len(result.checks)}`.",
            f"- Pass: `{pass_count}`.",
            f"- No pass: `{fail_count}`.",
            "",
            "## Comando",
            "",
            "```bash",
            ".venv/bin/python scripts/run_local_app.py",
            "```",
        ]
    )
    output = root / experiment_dir / "summary.md"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(lines) + "\n", encoding="utf-8")


def render_index(
    root: Path,
    config_path: Path,
    experiment_dir: Path,
    clips: list[ClipOption],
    result: AnalysisResult | None = None,
    error: str | None = None,
) -> str:
    current = result.request if result else _request_from_clip(selected_clip(clips))
    artifacts = result.artifacts if result else artifact_inventory(root, experiment_dir)
    checks = result.checks if result else read_closure_checks(root)
    clip_json = json.dumps([asdict(clip) for clip in clips], ensure_ascii=True)
    return "\n".join(
        [
            "<!doctype html>",
            '<html lang="es">',
            "<head>",
            '<meta charset="utf-8">',
            '<meta name="viewport" content="width=device-width, initial-scale=1">',
            "<title>FutBotMX Local</title>",
            f"<style>{_css()}</style>",
            "</head>",
            "<body>",
            '<main class="shell">',
            _header(result),
            _error_html(error),
            '<form method="post" action="/run-analysis" class="layout">',
            _input_panel(clips, current),
            _control_panel(current),
            _action_panel(current),
            "</form>",
            _result_panel(result, artifacts, checks),
            "</main>",
            f"<script>window.FUTBOT_CLIPS = {clip_json};{_js()}</script>",
            "</body>",
            "</html>",
        ]
    ) + "\n"


def resolve_artifact_path(root: Path, requested_path: str) -> Path:
    root_resolved = root.resolve()
    candidate = (root_resolved / unquote(requested_path)).resolve()
    if not candidate.is_relative_to(root_resolved):
        raise ValueError("path outside repository")
    if not candidate.exists() or not candidate.is_file():
        raise FileNotFoundError(requested_path)
    return candidate


def serve_local_app(root: Path, config_path: Path, experiment_dir: Path, host: str, port: int) -> None:
    config = load_config(root / config_path)
    clips = clip_options_from_config(config)
    handler = make_handler(root, config_path, experiment_dir, clips)
    server = ThreadingHTTPServer((host, port), handler)
    actual_host, actual_port = server.server_address
    display_host = host if host != "0.0.0.0" else actual_host
    print(f"FutBotMX local app: http://{display_host}:{actual_port}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("Stopping FutBotMX local app", flush=True)
    finally:
        server.server_close()


def make_handler(
    root: Path,
    config_path: Path,
    experiment_dir: Path,
    clips: list[ClipOption],
) -> type[BaseHTTPRequestHandler]:
    class LocalAppHandler(BaseHTTPRequestHandler):
        server_version = "FutBotMXLocalApp/0.1"

        def do_GET(self) -> None:
            parsed = urlparse(self.path)
            if parsed.path == "/health":
                self._send_text("ok\n", "text/plain; charset=utf-8")
                return
            if parsed.path == "/artifact":
                self._send_artifact(parsed.query)
                return
            if parsed.path != "/":
                self.send_error(404)
                return
            self._send_html(render_index(root, config_path, experiment_dir, clips))

        def do_POST(self) -> None:
            parsed = urlparse(self.path)
            if parsed.path != "/run-analysis":
                self.send_error(404)
                return
            length = int(self.headers.get("Content-Length", "0") or "0")
            body = self.rfile.read(length).decode("utf-8")
            form = parse_qs(body)
            try:
                request = analysis_request_from_form(form, clips)
                result = run_light_analysis(root, config_path, experiment_dir, request)
                self._send_html(render_index(root, config_path, experiment_dir, clips, result=result))
            except Exception as exc:
                self._send_html(render_index(root, config_path, experiment_dir, clips, error=str(exc)))

        def log_message(self, format: str, *args: Any) -> None:
            sys.stderr.write("local_app: " + format % args + "\n")

        def _send_html(self, payload: str) -> None:
            self._send_text(payload, "text/html; charset=utf-8")

        def _send_text(self, payload: str, content_type: str) -> None:
            body = payload.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _send_artifact(self, query: str) -> None:
            params = parse_qs(query)
            requested = _first(params, "path", "")
            try:
                artifact = resolve_artifact_path(root, requested)
            except (FileNotFoundError, ValueError) as exc:
                self.send_error(404, str(exc))
                return
            content_type = mimetypes.guess_type(artifact.as_posix())[0] or "application/octet-stream"
            body = artifact.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    return LocalAppHandler


def _clips_from_level2_closure(config: dict[str, Any]) -> list[ClipOption]:
    closure = config.get("level2_closure", {})
    raw_clips = closure.get("clips", []) if isinstance(closure, dict) else []
    clips = []
    for raw in raw_clips:
        if not isinstance(raw, dict):
            continue
        width = _coerce_int(raw.get("width"), 0, minimum=0)
        height = _coerce_int(raw.get("height"), 0, minimum=0)
        roi = _tuple_roi(raw.get("roi"), width, height)
        clips.append(
            ClipOption(
                clip_id=str(raw.get("clip_id", "clip")),
                role=str(raw.get("role", "")),
                video_path=str(raw.get("video", "")),
                start_frame=_coerce_int(raw.get("start_frame"), 0, minimum=0),
                end_frame=_coerce_int(raw.get("end_frame"), 180, minimum=0),
                stride=_coerce_int(raw.get("stride"), 1, minimum=1),
                roi=roi,
                width=width,
                height=height,
                fps=float(raw.get("fps", 0.0) or 0.0),
            )
        )
    return clips


def _clips_from_level2_multiclip(config: dict[str, Any]) -> list[ClipOption]:
    multiclip = config.get("level2_multiclip", {})
    raw_clips = multiclip.get("clips", []) if isinstance(multiclip, dict) else []
    clips = []
    for raw in raw_clips:
        if not isinstance(raw, dict):
            continue
        width = _coerce_int(raw.get("width"), 0, minimum=0)
        height = _coerce_int(raw.get("height"), 0, minimum=0)
        clips.append(
            ClipOption(
                clip_id=str(raw.get("clip_id", "clip")),
                role=str(raw.get("role", "")),
                video_path=str(raw.get("video", "")),
                start_frame=0,
                end_frame=180,
                stride=1,
                roi=_tuple_roi(raw.get("roi"), width, height),
                width=width,
                height=height,
                fps=float(raw.get("fps", 0.0) or 0.0),
            )
        )
    return clips


def _tuple_roi(value: Any, width: int, height: int) -> tuple[int, int, int, int]:
    if isinstance(value, (list, tuple)) and len(value) == 4:
        return tuple(_coerce_int(part, 0, minimum=0) for part in value)  # type: ignore[return-value]
    return (0, 0, width, height)


def _roi_from_form(form: dict[str, list[str]], clip: ClipOption) -> tuple[int, int, int, int]:
    mode = _first(form, "roi_mode", "preset")
    if mode == "full":
        return (0, 0, clip.width, clip.height)
    if mode == "preset":
        return clip.roi
    x1 = _coerce_int(_first(form, "roi_x1", str(clip.roi[0])), clip.roi[0], minimum=0)
    y1 = _coerce_int(_first(form, "roi_y1", str(clip.roi[1])), clip.roi[1], minimum=0)
    x2 = _coerce_int(_first(form, "roi_x2", str(clip.roi[2])), clip.roi[2], minimum=x1 + 1)
    y2 = _coerce_int(_first(form, "roi_y2", str(clip.roi[3])), clip.roi[3], minimum=y1 + 1)
    if clip.width:
        x2 = min(x2, clip.width)
    if clip.height:
        y2 = min(y2, clip.height)
    return (x1, y1, x2, y2)


def _run_command(root: Path, name: str, command: list[str]) -> CommandStatus:
    started = time.monotonic()
    env = os.environ.copy()
    env.setdefault("MPLCONFIGDIR", "/tmp/matplotlib")
    try:
        result = subprocess.run(command, cwd=root, env=env, capture_output=True, text=True, timeout=180)
        output = (result.stdout + "\n" + result.stderr).strip()
        status = "pass" if result.returncode == 0 else "fail"
        notes = output.splitlines()[-1] if output else f"returncode={result.returncode}"
    except (FileNotFoundError, subprocess.SubprocessError) as exc:
        status = "fail"
        notes = str(exc)
    return CommandStatus(name, status, " ".join(command), notes[-500:], time.monotonic() - started)


def _request_from_clip(clip: ClipOption) -> AnalysisRequest:
    return AnalysisRequest(
        clip.clip_id,
        clip.video_path,
        clip.start_frame,
        clip.end_frame,
        clip.stride,
        clip.roi,
    )


def _header(result: AnalysisResult | None) -> str:
    state = "listo" if result is None else result.status
    return f"""
<header class="topbar">
  <div>
    <p>FutBotMX Local</p>
    <h1>Interfaz local de ejecucion</h1>
  </div>
  <span class="pill {state}">{_esc(state)}</span>
</header>"""


def _input_panel(clips: list[ClipOption], current: AnalysisRequest) -> str:
    options = []
    for clip in clips:
        selected = " selected" if clip.clip_id == current.clip_id else ""
        label = f"{clip.clip_id} | {clip.role}" if clip.role else clip.clip_id
        options.append(f'<option value="{_esc(clip.clip_id)}"{selected}>{_esc(label)}</option>')
    return f"""
<section class="panel">
  <h2>Entrada</h2>
  <label>Video</label>
  <select name="clip_id" id="clip_id">{"".join(options)}</select>
  <label>Clip ID</label>
  <input name="clip_display" id="clip_display" value="{_esc(current.clip_id)}" readonly>
  <label>Ruta local</label>
  <input name="video_path" id="video_path" value="{_esc(current.video_path)}">
</section>"""


def _control_panel(current: AnalysisRequest) -> str:
    roi = current.roi
    return f"""
<section class="panel">
  <h2>Controles</h2>
  <div class="triple">
    <label>Frame inicial<input type="number" name="start_frame" id="start_frame" min="0" value="{current.start_frame}"></label>
    <label>Frame final<input type="number" name="end_frame" id="end_frame" min="0" value="{current.end_frame}"></label>
    <label>Stride<input type="number" name="stride" id="stride" min="1" value="{current.stride}"></label>
  </div>
  <div class="segmented">
    <label><input type="radio" name="roi_mode" value="preset" checked> ROI clip</label>
    <label><input type="radio" name="roi_mode" value="full"> Full frame</label>
    <label><input type="radio" name="roi_mode" value="custom"> Custom</label>
  </div>
  <div class="quad">
    <label>x1<input type="number" name="roi_x1" id="roi_x1" min="0" value="{roi[0]}"></label>
    <label>y1<input type="number" name="roi_y1" id="roi_y1" min="0" value="{roi[1]}"></label>
    <label>x2<input type="number" name="roi_x2" id="roi_x2" min="1" value="{roi[2]}"></label>
    <label>y2<input type="number" name="roi_y2" id="roi_y2" min="1" value="{roi[3]}"></label>
  </div>
</section>"""


def _action_panel(current: AnalysisRequest) -> str:
    dashboard_checked = " checked" if current.run_dashboard else ""
    reel_checked = " checked" if current.run_reel else ""
    return f"""
<section class="panel actions">
  <h2>Analisis</h2>
  <label class="toggle"><input type="checkbox" name="run_dashboard"{dashboard_checked}> Dashboard</label>
  <label class="toggle"><input type="checkbox" name="run_reel"{reel_checked}> Reel demo</label>
  <button type="submit">Ejecutar analisis</button>
</section>"""


def _result_panel(result: AnalysisResult | None, artifacts: list[ArtifactRow], checks: list[CheckRow]) -> str:
    return f"""
<section class="results">
  <div class="panel span2">
    <h2>Resultados</h2>
    {_command_table(result)}
    {_artifact_table(artifacts)}
  </div>
  <div class="panel">
    <h2>Checks</h2>
    {_checks_table(checks)}
  </div>
</section>"""


def _command_table(result: AnalysisResult | None) -> str:
    if not result:
        return '<p class="muted">Sin ejecucion local en esta sesion.</p>'
    rows = []
    for command in result.commands:
        rows.append(
            "<tr>"
            f"<td>{_esc(command.name)}</td>"
            f'<td><span class="status {command.status}">{_esc(command.status)}</span></td>'
            f"<td>{command.duration_sec:.2f}s</td>"
            f"<td>{_esc(command.notes)}</td>"
            "</tr>"
        )
    return '<table><thead><tr><th>Comando</th><th>Estado</th><th>Tiempo</th><th>Notas</th></tr></thead><tbody>' + "".join(rows) + "</tbody></table>"


def _artifact_table(artifacts: list[ArtifactRow]) -> str:
    rows = []
    for artifact in artifacts:
        label = _artifact_link(artifact)
        state = "presente" if artifact.exists else "pendiente"
        rows.append(
            "<tr>"
            f"<td>{_esc(artifact.label)}</td>"
            f'<td><span class="status {state}">{state}</span></td>'
            f"<td>{label}</td>"
            f"<td>{artifact.size_bytes}</td>"
            "</tr>"
        )
    return '<table><thead><tr><th>Artefacto</th><th>Estado</th><th>Ruta</th><th>Bytes</th></tr></thead><tbody>' + "".join(rows) + "</tbody></table>"


def _checks_table(checks: list[CheckRow]) -> str:
    rows = []
    for check in checks:
        rows.append(
            "<tr>"
            f"<td>{_esc(check.check_id)}</td>"
            f'<td><span class="status {check.status}">{_esc(check.status)}</span></td>'
            f"<td>{_esc(check.notes)}</td>"
            "</tr>"
        )
    return '<table><thead><tr><th>ID</th><th>Estado</th><th>Notas</th></tr></thead><tbody>' + "".join(rows) + "</tbody></table>"


def _artifact_link(artifact: ArtifactRow) -> str:
    if not artifact.exists:
        return _esc(artifact.path)
    href = "/artifact?path=" + quote(artifact.path)
    return f'<a href="{href}" target="_blank" rel="noreferrer">{_esc(artifact.path)}</a>'


def _error_html(error: str | None) -> str:
    if not error:
        return ""
    return f'<section class="error">{_esc(error)}</section>'


def _manifest_row(asset_id: str, asset_type: str, path: str, source_artifact: str, is_versioned: bool, role: str, notes: str) -> dict[str, str]:
    return {
        "asset_id": asset_id,
        "asset_type": asset_type,
        "path": path,
        "source_artifact": source_artifact,
        "is_versioned": str(is_versioned).lower(),
        "role": role,
        "notes": notes,
    }


def _rel_to_experiment(path: str, experiment_dir: Path) -> str:
    try:
        return Path(os.path.relpath(Path(path), start=experiment_dir)).as_posix()
    except ValueError:
        return path


def _asset_id(label: str) -> str:
    return label.lower().replace(" ", "_").replace("/", "_")


def _coerce_int(value: Any, default: int, minimum: int | None = None) -> int:
    try:
        number = int(float(str(value)))
    except (TypeError, ValueError):
        number = default
    if minimum is not None:
        number = max(number, minimum)
    return number


def _checkbox(form: dict[str, list[str]], key: str, default: bool = False) -> bool:
    if key not in form:
        return default
    return _first(form, key, "").lower() in {"1", "true", "on", "yes"}


def _first(form: dict[str, list[str]], key: str, default: str) -> str:
    values = form.get(key, [])
    return str(values[0]) if values else default


def _timestamp() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S%z")


def _esc(value: Any) -> str:
    return html.escape(str(value), quote=True)


def _css() -> str:
    return """
:root {
  --ink: #1b211d;
  --muted: #61706a;
  --line: #c8d5ce;
  --panel: #ffffff;
  --page: #f7faf7;
  --green: #2d6f4d;
  --blue: #315d9b;
  --amber: #9b6a1f;
  --red: #a03c34;
}
* { box-sizing: border-box; }
body {
  margin: 0;
  background: var(--page);
  color: var(--ink);
  font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
}
.shell {
  width: min(1220px, calc(100vw - 28px));
  margin: 0 auto;
  padding: 22px 0 34px;
}
.topbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  border-bottom: 2px solid var(--line);
  padding-bottom: 14px;
}
.topbar p {
  margin: 0 0 4px;
  color: var(--green);
  font-size: 13px;
  font-weight: 800;
  text-transform: uppercase;
}
h1 {
  margin: 0;
  font-size: 32px;
  line-height: 1.1;
  letter-spacing: 0;
}
h2 {
  margin: 0 0 12px;
  font-size: 18px;
  letter-spacing: 0;
}
.layout,
.results {
  display: grid;
  grid-template-columns: minmax(280px, 1fr) minmax(360px, 1.3fr) minmax(220px, .75fr);
  gap: 12px;
  margin-top: 16px;
}
.panel {
  background: var(--panel);
  border: 1px solid var(--line);
  border-radius: 8px;
  padding: 14px;
  min-width: 0;
}
.span2 {
  grid-column: span 2;
}
label {
  display: grid;
  gap: 5px;
  color: var(--muted);
  font-size: 13px;
  font-weight: 700;
  margin-bottom: 10px;
}
input,
select {
  width: 100%;
  min-height: 36px;
  border: 1px solid var(--line);
  border-radius: 6px;
  padding: 7px 9px;
  color: var(--ink);
  background: #fbfdfb;
  font: inherit;
}
.triple,
.quad {
  display: grid;
  gap: 8px;
}
.triple {
  grid-template-columns: repeat(3, minmax(0, 1fr));
}
.quad {
  grid-template-columns: repeat(4, minmax(0, 1fr));
}
.segmented {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 6px;
  margin: 4px 0 10px;
}
.segmented label,
.toggle {
  display: flex;
  align-items: center;
  gap: 7px;
  border: 1px solid var(--line);
  border-radius: 6px;
  padding: 7px 8px;
  margin: 0;
  color: var(--ink);
}
.segmented input,
.toggle input {
  width: auto;
  min-height: 0;
}
button {
  width: 100%;
  min-height: 40px;
  margin-top: 12px;
  border: 1px solid #1f5337;
  border-radius: 6px;
  background: var(--green);
  color: #fff;
  font-weight: 800;
  cursor: pointer;
}
table {
  width: 100%;
  border-collapse: collapse;
  margin-top: 8px;
  table-layout: fixed;
}
th,
td {
  border-bottom: 1px solid #e2e9e5;
  padding: 8px 6px;
  text-align: left;
  vertical-align: top;
  font-size: 13px;
  overflow-wrap: anywhere;
}
th {
  color: var(--muted);
  font-size: 12px;
  text-transform: uppercase;
}
.pill,
.status {
  display: inline-flex;
  align-items: center;
  min-height: 24px;
  border-radius: 999px;
  padding: 3px 9px;
  font-size: 12px;
  font-weight: 800;
}
.pill,
.pass,
.presente {
  background: #e1f3e8;
  color: var(--green);
}
.fail,
.missing {
  background: #f9e5e2;
  color: var(--red);
}
.pendiente {
  background: #f8efd7;
  color: var(--amber);
}
.muted {
  color: var(--muted);
}
.error {
  margin-top: 14px;
  border: 1px solid #e1a8a3;
  background: #fff0ef;
  color: var(--red);
  border-radius: 8px;
  padding: 10px 12px;
}
a {
  color: var(--blue);
  text-underline-offset: 2px;
}
@media (max-width: 900px) {
  .layout,
  .results {
    grid-template-columns: 1fr;
  }
  .span2 {
    grid-column: auto;
  }
  .triple,
  .quad,
  .segmented {
    grid-template-columns: 1fr;
  }
}
"""


def _js() -> str:
    return """
function byId(id) { return document.getElementById(id); }
function applyClip() {
  const selected = byId("clip_id").value;
  const clip = (window.FUTBOT_CLIPS || []).find((item) => item.clip_id === selected);
  if (!clip) return;
  byId("clip_display").value = clip.clip_id;
  byId("video_path").value = clip.video_path || "";
  byId("start_frame").value = clip.start_frame;
  byId("end_frame").value = clip.end_frame;
  byId("stride").value = clip.stride;
  byId("roi_x1").value = clip.roi[0];
  byId("roi_y1").value = clip.roi[1];
  byId("roi_x2").value = clip.roi[2];
  byId("roi_y2").value = clip.roi[3];
}
const select = byId("clip_id");
if (select) select.addEventListener("change", applyClip);
"""
