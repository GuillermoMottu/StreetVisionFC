from __future__ import annotations

import html
import json
import mimetypes
import re
import subprocess
import sys
import threading
import time
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, quote, unquote, urlparse

from futbotmx.artifact_names import (
    ADVANCED_EVENTS_DIR,
    ADVANCED_EVENTS_JSON,
    HIGHLIGHTS_CSV,
    LEGACY_ADVANCED_EVENTS_DIR,
    LEGACY_ADVANCED_EVENTS_JSON,
    LEGACY_HIGHLIGHTS_CSV,
    LEGACY_SPATIAL_DIR,
    LEGACY_SPATIAL_TRACKS_CSV,
    LEGACY_VISUALIZATIONS_DIR,
    SPATIAL_DIR,
    SPATIAL_TRACKS_CSV,
    VISUALIZATIONS_DIR,
    first_existing,
)
from futbotmx.app_state import AppState
from futbotmx.config import load_config
from futbotmx.live_playback import (
    DEFAULT_EXPERIMENT_DIR as DEFAULT_LIVE_PLAYBACK_EXPERIMENT_DIR,
    build_live_playback_context,
    live_playback_config_from_project,
    make_handler as make_live_playback_handler,
)
from futbotmx.live_playback_contract import read_csv_rows, read_json_events
from futbotmx.ui import shared_css, ui_body_attrs


DEFAULT_EXPERIMENT_DIR = Path("experiments/test_028_local_app")


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------

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
class PipelineRequest:
    video_path: str
    clip_id: str
    start_frame: int
    end_frame: int
    stride: int
    skip_segmentation: bool = False


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

def clip_options_from_config(config: dict[str, Any]) -> list[ClipOption]:
    clips = _clips_from_legacy_closure(config)
    if clips:
        return clips
    return _clips_from_legacy_multiclip(config)


def selected_clip(clips: list[ClipOption], clip_id: str | None = None) -> ClipOption:
    if not clips:
        return ClipOption("manual", "manual", "", 0, 180, 1, (0, 0, 0, 0), 0, 0, 0.0)
    for clip in clips:
        if clip.clip_id == clip_id:
            return clip
    return clips[0]


def pipeline_request_from_form(form: dict[str, list[str]], clips: list[ClipOption]) -> PipelineRequest:
    requested_clip_id = _first(form, "clip_id", "").strip()
    clip = selected_clip(clips, requested_clip_id)
    video_path = _first(form, "video_path", clip.video_path).strip()
    start_frame = _coerce_int(_first(form, "start_frame", str(clip.start_frame)), clip.start_frame, minimum=0)
    end_frame = _coerce_int(_first(form, "end_frame", str(clip.end_frame)), clip.end_frame, minimum=start_frame)
    stride = _coerce_int(_first(form, "stride", str(clip.stride)), clip.stride, minimum=1)
    skip = _checkbox(form, "skip_segmentation", default=False)
    known_clip_ids = {item.clip_id for item in clips}
    clip_id = requested_clip_id if requested_clip_id in known_clip_ids else _clip_id_from_video_path(video_path, requested_clip_id)
    return PipelineRequest(
        video_path=video_path,
        clip_id=clip_id,
        start_frame=start_frame,
        end_frame=end_frame,
        stride=stride,
        skip_segmentation=skip,
    )


def _clip_id_from_video_path(video_path: str, fallback: str = "manual") -> str:
    source = Path(video_path).stem if video_path else fallback
    if source in ("", "nuevo"):
        source = "manual"
    clip_id = re.sub(r"[^a-zA-Z0-9_-]+", "_", source).strip("_")[:48]
    return clip_id or "manual"


# ---------------------------------------------------------------------------
# Pipeline execution
# ---------------------------------------------------------------------------

def _generate_experiment_dir(video_path: str) -> str:
    stem = re.sub(r"[^a-zA-Z0-9_-]", "_", Path(video_path).stem)[:24]
    ts = time.strftime("%Y%m%d_%H%M%S")
    return f"experiments/run_{stem}_{ts}"


def _build_pipeline_cmd(
    root: Path,
    request: PipelineRequest,
    experiment_dir: str,
    state: AppState,
    previous_experiment_dir: str | None = None,
) -> list[str]:
    python = sys.executable
    script = str(root / "scripts" / "run_unified_analysis.py")
    cmd = [
        python, script,
        "--video", request.video_path,
        "--clip-id", request.clip_id,
        "--start-frame", str(request.start_frame),
        "--end-frame", str(request.end_frame),
        "--stride", str(request.stride),
        "--experiment", experiment_dir,
        "--no-browser",
        "--no-serve",
    ]
    reuse_experiment_dir = previous_experiment_dir or state.experiment_dir
    if request.skip_segmentation and reuse_experiment_dir:
        detections = root / reuse_experiment_dir / "detections.json"
        if detections.exists():
            cmd += ["--detections", str(detections)]
    return cmd


def _launch_pipeline(root: Path, request: PipelineRequest, state: AppState) -> None:
    experiment_dir = _generate_experiment_dir(request.video_path)
    previous_experiment_dir = state.experiment_dir
    state.start(request.video_path, experiment_dir)
    cmd = _build_pipeline_cmd(root, request, experiment_dir, state, previous_experiment_dir)
    try:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            cwd=str(root),
        )
    except (FileNotFoundError, OSError) as exc:
        state.fail(str(exc))
        return
    t = threading.Thread(target=_pipeline_reader, args=(proc, state), daemon=True)
    t.start()


def _pipeline_reader(proc: subprocess.Popen, state: AppState) -> None:
    assert proc.stdout is not None
    for raw in proc.stdout:
        state.append_log(raw.rstrip())
    proc.wait()
    if proc.returncode == 0:
        state.complete()
    else:
        state.fail(f"pipeline terminó con código {proc.returncode}")


# ---------------------------------------------------------------------------
# Results data
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ExperimentMetrics:
    highlight_count: int
    top_score: float
    frame_count: int
    event_count: int
    has_voronoi: bool
    has_graph: bool
    voronoi_path: str
    graph_path: str
    highlights_csv: str
    tracks_csv: str
    events_json: str
    playback_html: str


def _read_experiment_metrics(root: Path, experiment_dir: str) -> ExperimentMetrics:
    base = root / experiment_dir
    highlights_path = first_existing(base / ADVANCED_EVENTS_DIR / HIGHLIGHTS_CSV, base / LEGACY_ADVANCED_EVENTS_DIR / LEGACY_HIGHLIGHTS_CSV)
    tracks_path = first_existing(base / SPATIAL_DIR / SPATIAL_TRACKS_CSV, base / LEGACY_SPATIAL_DIR / LEGACY_SPATIAL_TRACKS_CSV)
    events_path = first_existing(base / ADVANCED_EVENTS_DIR / ADVANCED_EVENTS_JSON, base / LEGACY_ADVANCED_EVENTS_DIR / LEGACY_ADVANCED_EVENTS_JSON)
    highlights_csv = highlights_path.as_posix()
    tracks_csv = tracks_path.as_posix()
    events_json = events_path.as_posix()
    playback_html = (base / "live_playback" / "playback.html").as_posix()
    viz_dir = first_existing(base / VISUALIZATIONS_DIR, base / LEGACY_VISUALIZATIONS_DIR)
    voronoi = viz_dir / "voronoi.png"
    graph = viz_dir / "interaction_graph.png"

    highlight_count = 0
    top_score = 0.0
    try:
        rows = read_csv_rows(root / highlights_csv)
        highlight_count = len(rows)
        scores = [float(r.get("score", 0) or 0) for r in rows if r.get("score")]
        top_score = max(scores) if scores else 0.0
    except Exception:
        pass

    event_count = 0
    frame_count = 0
    try:
        events = read_json_events(root / events_json)
        event_count = len(events)
    except Exception:
        pass
    try:
        tracks = read_csv_rows(root / tracks_csv)
        frames = {r.get("frame") for r in tracks if r.get("frame")}
        frame_count = len(frames)
    except Exception:
        pass

    return ExperimentMetrics(
        highlight_count=highlight_count,
        top_score=top_score,
        frame_count=frame_count,
        event_count=event_count,
        has_voronoi=voronoi.exists(),
        has_graph=graph.exists(),
        voronoi_path=voronoi.relative_to(root).as_posix() if voronoi.exists() else "",
        graph_path=graph.relative_to(root).as_posix() if graph.exists() else "",
        highlights_csv=Path(highlights_csv).relative_to(root).as_posix() if (root / highlights_csv).exists() else "",
        tracks_csv=Path(tracks_csv).relative_to(root).as_posix() if (root / tracks_csv).exists() else "",
        events_json=Path(events_json).relative_to(root).as_posix() if (root / events_json).exists() else "",
        playback_html=Path(playback_html).relative_to(root).as_posix() if (root / playback_html).exists() else "",
    )


def _read_highlights(root: Path, experiment_dir: str, limit: int = 10) -> list[dict]:
    base = root / experiment_dir
    csv_path = first_existing(base / ADVANCED_EVENTS_DIR / HIGHLIGHTS_CSV, base / LEGACY_ADVANCED_EVENTS_DIR / LEGACY_HIGHLIGHTS_CSV)
    if not csv_path.exists():
        return []
    try:
        return list(read_csv_rows(csv_path))[:limit]
    except Exception:
        return []


# ---------------------------------------------------------------------------
# Screen renderers
# ---------------------------------------------------------------------------

def render_home(root: Path, state: AppState) -> str:
    snap = state.snapshot()
    metrics: ExperimentMetrics | None = None
    if snap["status"] == "complete" and snap["experiment_dir"]:
        try:
            metrics = _read_experiment_metrics(root, snap["experiment_dir"])
        except Exception:
            pass
    return "\n".join([
        "<!doctype html>",
        '<html lang="es">',
        "<head>",
        '<meta charset="utf-8">',
        '<meta name="viewport" content="width=device-width, initial-scale=1">',
        "<title>FutBotMX</title>",
        f"<style>{_css()}</style>",
        "</head>",
        f'<body {ui_body_attrs("launcher", "home-page")}>',
        '<main class="fb-shell">',
        _topbar_html("FutBotMX Analysis Center", "Centro de analisis deportivo", snap["status"]),
        _home_metrics_html(snap, metrics),
        _home_nav_html(snap),
        _tech_stack_html(),
        "</main>",
        "</body>",
        "</html>",
    ]) + "\n"


def render_analyze(root: Path, clips: list[ClipOption], state: AppState) -> str:
    snap = state.snapshot()
    clip = selected_clip(clips)
    has_detections = state.has_detections(str(root))
    clip_json = json.dumps([
        {
            "clip_id": c.clip_id,
            "video_path": c.video_path,
            "start_frame": c.start_frame,
            "end_frame": c.end_frame,
            "stride": c.stride,
        }
        for c in clips
    ], ensure_ascii=True)
    return "\n".join([
        "<!doctype html>",
        '<html lang="es">',
        "<head>",
        '<meta charset="utf-8">',
        '<meta name="viewport" content="width=device-width, initial-scale=1">',
        "<title>FutBotMX — Análisis</title>",
        f"<style>{_css()}</style>",
        "</head>",
        f'<body {ui_body_attrs("launcher", "analyze-page")}>',
        '<main class="fb-shell">',
        _topbar_html("Nuevo analisis tactico", "Pipeline deportivo end-to-end", snap["status"]),
        _analyze_form_html(clip, clips, has_detections, snap),
        _analyze_progress_html(snap),
        _fb_overlay_html(),
        "</main>",
        f"<script>window.FB_CLIPS={clip_json};{_analyze_js()}</script>",
        "</body>",
        "</html>",
    ]) + "\n"


def render_results(root: Path, state: AppState) -> str:
    snap = state.snapshot()
    if not snap["experiment_dir"] or snap["status"] not in ("complete", "error"):
        return _results_empty_html(snap)
    metrics = None
    highlights: list[dict] = []
    try:
        metrics = _read_experiment_metrics(root, snap["experiment_dir"])
        highlights = _read_highlights(root, snap["experiment_dir"])
    except Exception:
        pass
    return "\n".join([
        "<!doctype html>",
        '<html lang="es">',
        "<head>",
        '<meta charset="utf-8">',
        '<meta name="viewport" content="width=device-width, initial-scale=1">',
        "<title>FutBotMX — Resultados</title>",
        f"<style>{_css()}</style>",
        "</head>",
        f'<body {ui_body_attrs("report", "results-page")}>',
        '<main class="fb-shell">',
        _topbar_html("Resultados tacticos", _esc(Path(snap["video_path"]).name), "complete"),
        _results_metrics_html(metrics),
        _results_playback_html(),
        _results_visualizations_html(metrics),
        _results_highlights_html(highlights),
        _results_downloads_html(metrics),
        "</main>",
        "</body>",
        "</html>",
    ]) + "\n"


# ---------------------------------------------------------------------------
# Internal HTML builders
# ---------------------------------------------------------------------------

def _topbar_html(title: str, subtitle: str, status: str) -> str:
    nav = """
  <nav class="topbar-nav">
    <a href="/">Inicio</a>
    <a href="/analyze">Analizar</a>
    <a href="/results">Resultados</a>
  </nav>"""
    return f"""
<header class="topbar fb-topbar">
  <div>
    <p class="eyebrow">{_esc(subtitle)}</p>
    <h1>{_esc(title)}</h1>
  </div>{nav}
  <span class="pill status-{_esc(status)}">{_esc(status)}</span>
</header>"""


def _home_metrics_html(snap: dict, metrics: ExperimentMetrics | None) -> str:
    if metrics is None:
        hl = "—"
        score = "—"
        frames = "—"
        events = "—"
        note = "Sin análisis previo"
    else:
        hl = str(metrics.highlight_count)
        score = f"{metrics.top_score:.2f}" if metrics.top_score else "—"
        frames = str(metrics.frame_count)
        events = str(metrics.event_count)
        note = _esc(snap.get("video_path", ""))
    return f"""
<section class="home-metrics">
  <ul class="summary-grid">
    <li><span>Highlights</span><strong>{hl}</strong><em>detectados</em></li>
    <li><span>Score máx.</span><strong>{score}</strong><em>highlight top</em></li>
    <li><span>Frames</span><strong>{frames}</strong><em>analizados</em></li>
    <li><span>Eventos</span><strong>{events}</strong><em>registrados</em></li>
  </ul>
  <p class="home-note">{note}</p>
</section>"""


def _home_nav_html(snap: dict) -> str:
    results_disabled = "" if snap["status"] == "complete" else " disabled"
    results_href = "/results" if snap["status"] == "complete" else "#"
    running_note = '<p class="running-note">Pipeline en curso — <a href="/analyze">ver progreso</a></p>' if snap["status"] == "running" else ""
    return f"""
<section class="home-nav">
  <div class="home-nav-grid">
    <a href="/analyze" class="nav-card primary">
      <span class="nav-icon">▶</span>
      <strong>Analizar video</strong>
      <span>Selecciona un video y corre el pipeline completo end-to-end</span>
    </a>
    <a href="{results_href}" class="nav-card secondary{results_disabled}">
      <span class="nav-icon">◉</span>
      <strong>Ver resultados</strong>
      <span>Métricas, highlights, mapas y descargas del último análisis</span>
    </a>
  </div>
  {running_note}
</section>"""


def _tech_stack_html() -> str:
    return """
<section class="tech-stack">
  <p class="stack-label">Stack</p>
  <div class="stack-pills">
    <span class="pill">Grounded-SAM 3</span>
    <span class="pill">OWLv2</span>
    <span class="pill">ByteTrack</span>
    <span class="pill">Táctica avanzada</span>
    <span class="pill">Voronoi</span>
  </div>
</section>"""


def _analyze_form_html(clip: ClipOption, clips: list[ClipOption], has_detections: bool, snap: dict) -> str:
    is_running = snap["status"] == "running"
    disabled = " disabled" if is_running else ""
    skip_html = ""
    if has_detections:
        skip_html = f"""
  <label class="toggle skip-option">
    <input type="checkbox" name="skip_segmentation">
    Reutilizar detecciones previas
    <span class="skip-note">(omite Grounded-SAM)</span>
  </label>"""
    clips_html = "".join(
        f'<option value="{_esc(item.clip_id)}"{" selected" if item.clip_id == clip.clip_id else ""}>'
        f'{_esc(item.clip_id)} · {_esc(Path(item.video_path).name or item.video_path)}</option>'
        for item in clips
    )
    if not clips_html:
        clips_html = '<option value="manual" selected>manual</option>'
    selected_video_name = _esc(Path(clip.video_path).name or clip.video_path or "Sin video seleccionado")
    return f"""
<section class="analyze-section panel fb-panel">
  <h2>Configuración del análisis</h2>
  <form method="post" action="/start-analysis" id="analyze-form">
    <div class="field-group">
      <label>Video
        <div class="video-picker">
          <div class="video-field">
            <input type="text" name="video_path" id="video_path"
                   value="{_esc(clip.video_path)}" placeholder="/ruta/al/video.mp4"
                   aria-describedby="video_selected_name video_meta"{disabled}>
            <button type="button" class="btn-browse" onclick="fbOpen()" title="📁 Explorar" aria-label="Explorar videos"{disabled}>
              <span>📁</span><span>Explorar</span>
            </button>
          </div>
          <div class="video-selected" id="video_selected">
            <span>Seleccionado</span>
            <strong id="video_selected_name">{selected_video_name}</strong>
          </div>
        </div>
      </label>
      <div class="video-meta" id="video_meta"></div>
    </div>
    <div class="field-group">
      <label>Clip ID
        <select name="clip_id" id="clip_id"{disabled}>
          {clips_html}
          <option value="nuevo">nuevo · seleccionar desde explorar</option>
        </select>
      </label>
    </div>
    <div class="field-group triple">
      <label>Frame inicial
        <input type="number" name="start_frame" id="start_frame"
               min="0" value="{clip.start_frame}"{disabled}>
      </label>
      <label>Frame final
        <input type="number" name="end_frame" id="end_frame"
               min="0" value="{clip.end_frame}"{disabled}>
      </label>
      <label>Stride
        <input type="number" name="stride" id="stride"
               min="1" value="{clip.stride}"{disabled}>
      </label>
    </div>
    {skip_html}
    <div class="action-stack">
      <button type="submit" class="btn-primary"{disabled}>
        {'⏳ Pipeline en curso…' if is_running else '▶ Ejecutar análisis completo'}
      </button>
    </div>
  </form>
</section>"""


def _analyze_progress_html(snap: dict) -> str:
    show = snap["status"] in ("running", "complete", "error")
    hidden = "" if show else " hidden"
    status = snap["status"]
    seg_cls = _stage_class(status, "segmentation", snap)
    ana_cls = _stage_class(status, "analysis", snap)
    done_cls = _stage_class(status, "complete", snap)
    return f"""
<section class="progress-section panel fb-panel" id="progress-panel"{hidden}>
  <h2>Progreso del pipeline</h2>
  <div class="stage-bar">
    <div class="stage-step {seg_cls}" id="stage-segmentation">
      <span class="stage-num">1</span>
      <span class="stage-label">Segmentación<br><small>Grounded-SAM</small></span>
    </div>
    <div class="stage-connector"></div>
    <div class="stage-step {ana_cls}" id="stage-analysis">
      <span class="stage-num">2</span>
      <span class="stage-label">Análisis<br><small>Táctico</small></span>
    </div>
    <div class="stage-connector"></div>
    <div class="stage-step {done_cls}" id="stage-complete">
      <span class="stage-num">3</span>
      <span class="stage-label">Listo</span>
    </div>
  </div>
  <div class="log-output" id="log-output" aria-live="polite"></div>
  <div class="results-cta" id="results-cta" hidden>
    <a href="/results" class="btn-primary">Ver resultados →</a>
  </div>
</section>"""


def _stage_class(status: str, stage: str, snap: dict) -> str:
    if status == "idle":
        return "pending"
    if stage == "complete":
        return "done" if status == "complete" else ("error" if status == "error" else "pending")
    return "done" if status == "complete" else "active" if status == "running" else "pending"


def _results_empty_html(snap: dict) -> str:
    msg = "Ejecuta un análisis primero para ver los resultados."
    if snap["status"] == "running":
        msg = 'Pipeline en curso. <a href="/analyze">Ver progreso →</a>'
    elif snap["status"] == "error":
        msg = f'El último pipeline terminó con error: {_esc(snap.get("error", ""))}'
    return f"""<!doctype html>
<html lang="es"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>FutBotMX — Resultados</title>
<style>{_css()}</style></head>
<body {ui_body_attrs("report", "results-page")}>
<main class="fb-shell">
{_topbar_html("Resultados tacticos", "Sin datos disponibles", snap["status"])}
<section class="panel fb-panel empty-state">
  <p>{msg}</p>
  <a href="/analyze" class="btn-primary">Analizar video →</a>
</section>
</main></body></html>"""


def _results_metrics_html(metrics: ExperimentMetrics | None) -> str:
    if metrics is None:
        return '<section class="results-metrics"><ul class="summary-grid"></ul></section>'
    score = f"{metrics.top_score:.2f}" if metrics.top_score else "—"
    return f"""
<section class="results-metrics">
  <ul class="summary-grid">
    <li><span>Highlights</span><strong>{metrics.highlight_count}</strong><em>detectados</em></li>
    <li><span>Score máx.</span><strong>{score}</strong><em>highlight top</em></li>
    <li><span>Frames</span><strong>{metrics.frame_count}</strong><em>con tracks</em></li>
    <li><span>Eventos</span><strong>{metrics.event_count}</strong><em>registrados</em></li>
  </ul>
</section>"""


def _results_playback_html() -> str:
    return """
<section class="results-playback panel fb-panel">
  <div class="section-heading">
    <h2>Live Playback</h2>
    <p>Video con overlays, tracks, eventos y minimapa en tiempo real.</p>
  </div>
  <iframe src="/playback/" title="Live Playback" class="playback-frame"
          loading="lazy" allowfullscreen></iframe>
</section>"""


def _results_visualizations_html(metrics: ExperimentMetrics | None) -> str:
    def _img(path: str, label: str, exists: bool) -> str:
        if exists and path:
            href = _file_href(path)
            return f"""
<figure>
  <img src="{href}" alt="{_esc(label)}" loading="lazy">
  <figcaption>{_esc(label)}</figcaption>
</figure>"""
        return f'<figure class="missing viz-placeholder"><figcaption>{_esc(label)} — no disponible</figcaption></figure>'

    voronoi = _img(metrics.voronoi_path if metrics else "", "Control espacial (Voronoi)", bool(metrics and metrics.has_voronoi))
    graph = _img(metrics.graph_path if metrics else "", "Grafo de interacciones", bool(metrics and metrics.has_graph))
    return f"""
<section class="results-viz panel fb-panel">
  <div class="section-heading">
    <h2>Visualizaciones</h2>
    <p>Análisis espacial y red de interacciones entre robots.</p>
  </div>
  <div class="visual-grid">
    {voronoi}
    {graph}
  </div>
</section>"""


def _results_highlights_html(highlights: list[dict]) -> str:
    if not highlights:
        return """
<section class="results-highlights panel fb-panel">
  <h2>Highlights</h2>
  <p class="muted">No se encontraron highlights para este experimento.</p>
</section>"""
    rows = []
    for i, row in enumerate(highlights, 1):
        score = row.get("score", "")
        conf = row.get("confidence", row.get("conf", ""))
        track = row.get("track_id", row.get("robot_id", ""))
        label = row.get("event_label", row.get("label", ""))
        frame_start = row.get("frame_start", row.get("start_frame", ""))
        try:
            score_val = float(score)
            score_disp = f"{score_val:.3f}"
        except (TypeError, ValueError):
            score_disp = _esc(str(score))
        rows.append(
            "<tr>"
            f"<td>{i}</td>"
            f"<td>{_esc(str(track))}</td>"
            f"<td><strong>{score_disp}</strong></td>"
            f"<td>{_esc(str(conf))}</td>"
            f"<td>{_esc(str(frame_start))}</td>"
            f"<td>{_esc(str(label))}</td>"
            "</tr>"
        )
    return f"""
<section class="results-highlights panel fb-panel">
  <div class="section-heading">
    <h2>Highlights</h2>
    <p>Top {len(highlights)} por score de relevancia.</p>
  </div>
  <div class="table-scroll">
    <table>
      <thead><tr><th>#</th><th>Robot</th><th>Score</th><th>Conf.</th><th>Frame</th><th>Evento</th></tr></thead>
      <tbody>{"".join(rows)}</tbody>
    </table>
  </div>
</section>"""


def _results_downloads_html(metrics: ExperimentMetrics | None) -> str:
    if metrics is None:
        return ""
    items = [
        ("Highlights CSV", metrics.highlights_csv),
        ("Tracks CSV", metrics.tracks_csv),
        ("Events JSON", metrics.events_json),
        ("Playback HTML", metrics.playback_html),
    ]
    links = []
    for label, path in items:
        if path:
            links.append(f'<a class="dl-link btn-link" href="{_file_href(path)}" target="_blank" rel="noreferrer">{_esc(label)}</a>')
    if not links:
        return ""
    return f"""
<section class="results-downloads panel fb-panel">
  <h2>Descargas</h2>
  <div class="quick-links">{"".join(links)}</div>
</section>"""


def _fb_overlay_html() -> str:
    return """
<div class="fb-overlay" id="fb-overlay" role="dialog" aria-modal="true" aria-label="Explorar videos" hidden>
  <div class="fb-panel">
    <div class="fb-header">
      <span id="fb-path" class="fb-path"></span>
      <button type="button" class="fb-close" onclick="fbClose()" aria-label="Cerrar">✕</button>
    </div>
    <div class="fb-list" id="fb-list" role="listbox"></div>
  </div>
</div>"""


# ---------------------------------------------------------------------------
# CSS
# ---------------------------------------------------------------------------

def _css() -> str:
    return shared_css() + """
/* ── Product app styles ───────────────────────────────────────────────── */
.topbar-nav {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
  position: relative;
  z-index: 1;
}
.topbar-nav a {
  color: #f2ffe7;
  font-size: 13px;
  font-weight: 800;
  text-decoration: none;
  border: 1px solid rgba(255,255,255,.22);
  border-radius: 6px;
  padding: 5px 10px;
}
.topbar-nav a:hover { background: rgba(183,243,0,.18); }

.status-idle    { background:#ecffd8; color:var(--fb-navy); }
.status-running { background:#fff6cf; color:#725000; }
.status-complete{ background:#ecffd8; color:var(--fb-navy); }
.status-error   { background:#fff2ee; color:var(--fb-alert); }

.panel,
.fb-panel {
  background: rgba(255,255,255,.96);
  border: 1px solid var(--fb-line);
  border-radius: var(--fb-radius);
  padding: 16px;
  box-shadow: 0 10px 24px rgba(0,75,58,.08);
}

/* Home */
.home-metrics { padding: 18px 0 4px; }
.home-note { margin: 8px 0 0; color: var(--fb-muted); font-size: 12px; overflow-wrap: anywhere; }

.home-nav { padding: 10px 0 18px; }
.home-nav-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}
.nav-card {
  position: relative;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  gap: 10px;
  min-height: 148px;
  background:
    linear-gradient(135deg, rgba(0,75,58,.98), rgba(0,200,83,.86)),
    var(--fb-navy);
  border: 1px solid var(--fb-line);
  border-top: 4px solid var(--fb-lime);
  border-radius: var(--fb-radius);
  padding: 18px;
  text-decoration: none;
  color: #ffffff;
  box-shadow: 0 14px 32px rgba(0,75,58,.16);
  transition: transform .15s, box-shadow .15s;
}
.nav-card::after {
  content: "";
  position: absolute;
  inset: auto -12% -34% 48%;
  height: 90%;
  background: rgba(183,243,0,.28);
  transform: skewX(-9deg);
}
.nav-card:hover { transform: translateY(-2px); box-shadow: 0 18px 40px rgba(0,75,58,.2); }
.nav-card.secondary {
  background: #ffffff;
  color: var(--fb-ink);
  border-top-color: var(--fb-green);
}
.nav-card.secondary.disabled { opacity: .5; pointer-events: none; }
.nav-icon {
  display: grid;
  place-items: center;
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background: rgba(183,243,0,.24);
  font-size: 18px;
  position: relative;
  z-index: 1;
}
.nav-card strong { font-size: 22px; color: inherit; position: relative; z-index: 1; }
.nav-card span:last-child { color: inherit; opacity: .82; font-size: 13px; line-height: 1.45; position: relative; z-index: 1; }
.running-note { margin: 10px 0 0; color: var(--fb-amber); font-weight: 800; font-size: 13px; }

.tech-stack { padding: 0 0 24px; }
.stack-label { margin: 0 0 8px; color: var(--fb-muted); font-size: 12px; font-weight: 800; text-transform: uppercase; }
.stack-pills { display: flex; flex-wrap: wrap; gap: 6px; }
.stack-pills .pill { background: #ecffd8; color: var(--fb-navy); border: 1px solid var(--fb-line); }

/* Analyze */
.analyze-section { margin-top: 14px; }
.field-group { margin-bottom: 14px; }
.video-picker {
  display: grid;
  gap: 7px;
}
.video-field {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 8px;
  align-items: stretch;
  width: 100%;
}
.video-field input {
  width: 100%;
  min-width: 0;
  height: 42px;
}
.btn-browse {
  flex-shrink: 0;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  width: auto;
  min-width: 132px;
  min-height: 42px;
  border: 1px solid var(--fb-line);
  border-radius: 6px;
  background: #fff;
  color: var(--fb-navy);
  font-weight: 800;
  padding: 0 16px;
  cursor: pointer;
  white-space: nowrap;
}
.btn-browse:hover { border-color: var(--fb-green); background: #f2ffe7; }
.video-selected {
  display: flex;
  align-items: center;
  gap: 8px;
  min-height: 28px;
  border: 1px solid var(--fb-line-soft);
  border-radius: 6px;
  background: #f6fff2;
  padding: 5px 8px;
  overflow: hidden;
}
.video-selected span {
  flex: 0 0 auto;
  color: var(--fb-muted);
  font-size: 11px;
  font-weight: 800;
  text-transform: uppercase;
}
.video-selected strong {
  min-width: 0;
  color: var(--fb-ink);
  font-size: 13px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.video-meta { color: var(--fb-muted); font-size: 12px; margin-top: 5px; min-height: 18px; }

.skip-option { margin: 8px 0; }
.skip-note { color: var(--fb-muted); font-size: 12px; }

.action-stack { margin-top: 16px; }

/* Progress */
.progress-section { margin-top: 14px; }
.stage-bar {
  display: flex;
  align-items: center;
  gap: 0;
  margin: 16px 0;
}
.stage-step {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  min-width: 90px;
}
.stage-num {
  display: grid;
  place-items: center;
  width: 32px;
  height: 32px;
  border-radius: 50%;
  font-weight: 900;
  font-size: 14px;
  background: #e2f2e6;
  color: var(--fb-muted);
}
.stage-step.active .stage-num  { background: var(--fb-lime); color: var(--fb-navy); }
.stage-step.done .stage-num    { background: var(--fb-green); color: #fff; }
.stage-step.error .stage-num   { background: var(--fb-alert); color: #fff; }
.stage-label { font-size: 12px; font-weight: 700; text-align: center; color: var(--fb-muted); }
.stage-step.active .stage-label,
.stage-step.done .stage-label  { color: var(--fb-ink); }
.stage-connector {
  flex: 1;
  height: 2px;
  background: var(--fb-line);
  margin-bottom: 24px;
}

.log-output {
  background: #031b14;
  color: #b7f300;
  font-family: "JetBrains Mono", "Fira Code", ui-monospace, monospace;
  font-size: 12px;
  line-height: 1.5;
  padding: 12px;
  border-radius: 6px;
  min-height: 120px;
  max-height: 320px;
  overflow-y: auto;
  white-space: pre-wrap;
  word-break: break-all;
}
.results-cta { margin-top: 14px; }
.results-cta a.btn-primary {
  display: inline-flex;
  align-items: center;
  min-height: 40px;
  padding: 0 20px;
  background: var(--fb-navy);
  color: #fff;
  border-radius: 6px;
  font-weight: 800;
  text-decoration: none;
}

/* File browser overlay */
.fb-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0,75,58,.55);
  z-index: 900;
  display: flex;
  align-items: flex-start;
  justify-content: center;
  padding-top: 60px;
}
.fb-overlay[hidden] { display: none; }
.fb-panel {
  background: #fff;
  border-radius: var(--fb-radius);
  box-shadow: var(--fb-shadow);
  width: min(620px, calc(100vw - 32px));
  max-height: 70vh;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
.fb-header {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 14px;
  border-bottom: 1px solid var(--fb-line);
  background: #ecffd8;
}
.fb-path {
  flex: 1;
  font-size: 12px;
  font-family: monospace;
  color: var(--fb-muted);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.fb-close {
  border: none;
  background: none;
  color: var(--fb-muted);
  font-size: 16px;
  cursor: pointer;
  padding: 2px 6px;
  border-radius: 4px;
}
.fb-close:hover { background: var(--fb-line); }
.fb-list { flex: 1; overflow-y: auto; padding: 6px 0; }
.fb-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 14px;
  cursor: pointer;
  font-size: 13px;
  color: var(--fb-ink);
  border: none;
  background: none;
  width: 100%;
  text-align: left;
}
.fb-item:hover { background: #f2ffe7; }
.fb-item.dir { color: var(--fb-navy); font-weight: 700; }
.fb-item.file { color: var(--fb-ink); }
.fb-item.up { color: var(--fb-muted); }
.fb-empty { padding: 20px 14px; color: var(--fb-muted); font-size: 13px; }

/* Results */
.results-playback { margin-top: 14px; }
.playback-frame {
  width: 100%;
  min-height: 580px;
  border: 1px solid var(--fb-line);
  border-radius: 6px;
  background: #031b14;
  margin-top: 10px;
  display: block;
}
.results-viz,
.results-highlights,
.results-downloads { margin-top: 14px; }
.viz-placeholder { min-height: 200px; }
.table-scroll { overflow-x: auto; }

.empty-state {
  margin-top: 14px;
  padding: 40px 24px;
  text-align: center;
  color: var(--fb-muted);
}
.empty-state a.btn-primary {
  display: inline-flex;
  align-items: center;
  min-height: 40px;
  padding: 0 20px;
  background: var(--fb-navy);
  color: #fff;
  border-radius: 6px;
  font-weight: 800;
  text-decoration: none;
  margin-top: 16px;
}

/* Shared form */
label {
  display: grid;
  gap: 5px;
  color: var(--fb-muted);
  font-size: 13px;
  font-weight: 700;
  margin-bottom: 10px;
}
input, select {
  width: 100%;
  min-height: 36px;
  border: 1px solid var(--fb-line);
  border-radius: 6px;
  padding: 7px 9px;
  color: var(--fb-ink);
  background: #fff;
  font: inherit;
}
input:focus, select:focus {
  outline: 0;
  border-color: var(--fb-sky);
  box-shadow: 0 0 0 3px rgba(0,210,91,.18);
}
button.btn-primary, a.btn-primary, input[type=submit].btn-primary {
  background: var(--fb-navy);
  color: #fff;
  border-color: var(--fb-blue);
}
button {
  width: 100%;
  min-height: 40px;
  border: 1px solid var(--fb-green);
  border-radius: 6px;
  background: #fff;
  color: var(--fb-navy);
  font-weight: 800;
  cursor: pointer;
  font: inherit;
}
button:disabled { opacity: .5; cursor: not-allowed; }
.toggle {
  display: flex;
  align-items: center;
  gap: 7px;
  border: 1px solid var(--fb-line);
  border-radius: 6px;
  padding: 7px 8px;
  margin: 0;
  color: var(--fb-ink);
  background: #fff;
}
.toggle input { width: auto; min-height: 0; accent-color: var(--fb-green); }
.triple { display: grid; grid-template-columns: repeat(3, minmax(0,1fr)); gap: 8px; }
.muted { color: var(--fb-muted); }
a { color: var(--fb-navy); text-underline-offset: 2px; }

/* Responsive */
@media (max-width: 900px) {
  .home-nav-grid { grid-template-columns: 1fr; }
  .triple { grid-template-columns: 1fr; }
  .playback-frame { min-height: 420px; }
}
@media (max-width: 640px) {
  .topbar-nav { display: none; }
  .video-field { grid-template-columns: 1fr; }
  .video-field .btn-browse { width: 100%; }
  .video-selected { align-items: flex-start; flex-direction: column; gap: 2px; }
  table { display: block; overflow-x: auto; white-space: nowrap; }
}
"""


# ---------------------------------------------------------------------------
# JavaScript (analyze page)
# ---------------------------------------------------------------------------

def _analyze_js() -> str:
    return r"""
/* Clip selector */
function applyClip() {
  var sel = document.getElementById('clip_id');
  var clip = (window.FB_CLIPS || []).find(function(c){ return c.clip_id === sel.value; });
  var pathInput = document.getElementById('video_path');
  if (!clip) {
    updateSelectedVideoName(pathInput ? pathInput.value : '');
    return;
  }
  pathInput.value = clip.video_path || '';
  document.getElementById('start_frame').value = clip.start_frame;
  document.getElementById('end_frame').value = clip.end_frame;
  document.getElementById('stride').value = clip.stride;
  updateSelectedVideoName(clip.video_path || '');
  if (clip.video_path) fetchVideoMeta(clip.video_path);
}
var clipSel = document.getElementById('clip_id');
if (clipSel) clipSel.addEventListener('change', applyClip);

/* Video metadata */
var vpInput = document.getElementById('video_path');
if (vpInput) {
  var _metaTimer = null;
  vpInput.addEventListener('input', function() {
    clearTimeout(_metaTimer);
    updateSelectedVideoName(vpInput.value.trim());
    syncClipSelectWithPath(vpInput.value.trim());
    _metaTimer = setTimeout(function() { fetchVideoMeta(vpInput.value.trim()); }, 600);
  });
  updateSelectedVideoName(vpInput.value.trim());
  if (vpInput.value) fetchVideoMeta(vpInput.value.trim());
}
function basename(path) {
  if (!path) return 'Sin video seleccionado';
  return String(path).split(/[\/\\]/).filter(Boolean).pop() || path;
}
function updateSelectedVideoName(path) {
  var el = document.getElementById('video_selected_name');
  if (el) el.textContent = basename(path);
}
function syncClipSelectWithPath(path) {
  var sel = document.getElementById('clip_id');
  if (!sel) return;
  var match = (window.FB_CLIPS || []).find(function(c){ return c.video_path === path; });
  sel.value = match ? match.clip_id : 'nuevo';
}
function fetchVideoMeta(path) {
  if (!path) return;
  fetch('/playback/video-info?path=' + encodeURIComponent(path))
    .then(function(r){ return r.json(); })
    .then(function(d) {
      var meta = document.getElementById('video_meta');
      if (!meta) return;
      if (d.error) { meta.textContent = ''; return; }
      meta.textContent = d.fps.toFixed(2) + ' fps  ·  ' + d.width + '×' + d.height + '  ·  ' + d.total_frames + ' frames  (' + d.duration_s.toFixed(1) + 's)';
      document.getElementById('end_frame').value = Math.max(0, d.total_frames - 1);
    }).catch(function(){});
}

/* File browser */
window.fbOpen = function() {
  var ov = document.getElementById('fb-overlay');
  if (ov) { ov.hidden = false; fbLoad(''); }
};
window.fbClose = function() {
  var ov = document.getElementById('fb-overlay');
  if (ov) ov.hidden = true;
};
document.addEventListener('keydown', function(e){ if (e.key === 'Escape') fbClose(); });
function fbLoad(dir) {
  fetch('/playback/browse?dir=' + encodeURIComponent(dir || ''))
    .then(function(r){ return r.json(); })
    .then(function(d) {
      document.getElementById('fb-path').textContent = d.current || '';
      var list = document.getElementById('fb-list');
      list.innerHTML = '';
      if (d.parent !== undefined && d.parent !== null && d.parent !== '') {
        var up = document.createElement('button');
        up.className = 'fb-item up'; up.type = 'button';
        up.textContent = '↑ ..';
        up.onclick = function(){ fbLoad(d.parent); };
        list.appendChild(up);
      }
      (d.dirs || []).forEach(function(item) {
        var btn = document.createElement('button');
        btn.className = 'fb-item dir'; btn.type = 'button';
        btn.textContent = '📁 ' + item.name;
        btn.onclick = function(){ fbLoad(item.path); };
        list.appendChild(btn);
      });
      (d.files || []).forEach(function(item) {
        var btn = document.createElement('button');
        btn.className = 'fb-item file'; btn.type = 'button';
        btn.textContent = '🎬 ' + item.name + ' — ' + item.size_mb.toFixed(1) + ' MB';
        btn.onclick = function(){ fbSelectFile(item.path); };
        list.appendChild(btn);
      });
      if (!d.dirs.length && !d.files.length) {
        var em = document.createElement('p');
        em.className = 'fb-empty'; em.textContent = 'Sin videos en esta carpeta.';
        list.appendChild(em);
      }
    }).catch(function(){ });
}
function fbSelectFile(path) {
  var inp = document.getElementById('video_path');
  if (inp) {
    inp.value = path;
    updateSelectedVideoName(path);
    syncClipSelectWithPath(path);
    fetchVideoMeta(path);
  }
  fbClose();
}

/* SSE progress */
(function() {
  var panel = document.getElementById('progress-panel');
  var logEl  = document.getElementById('log-output');
  var cta    = document.getElementById('results-cta');
  if (!panel) return;
  var statusAttr = document.body.getAttribute('data-product-flow');
  /* Only start SSE if panel is visible (running state) */
  if (panel.hidden) return;
  var es = new EventSource('/analyze-progress');
  es.onmessage = function(e) {
    var msg = JSON.parse(e.data);
    if (msg.line) {
      var line = document.createTextNode(msg.line + '\n');
      logEl.appendChild(line);
      logEl.scrollTop = logEl.scrollHeight;
    }
    if (msg.stage) updateStage(msg.stage);
    if (msg.stage === 'complete' || msg.stage === 'error') {
      es.close();
      if (cta) cta.removeAttribute('hidden');
    }
  };
  es.onerror = function() { es.close(); };
  function updateStage(s) {
    var steps = ['segmentation', 'analysis', 'complete'];
    steps.forEach(function(step) {
      var el = document.getElementById('stage-' + step);
      if (!el) return;
      var num = el.querySelector('.stage-num');
      if (s === 'complete') {
        el.querySelector('.stage-num') && setClass(el, 'done');
      } else if (step === s) {
        setClass(el, 'active');
      }
    });
  }
  function setClass(el, cls) {
    el.classList.remove('pending', 'active', 'done', 'error');
    el.classList.add(cls);
  }
})();
"""


# ---------------------------------------------------------------------------
# Server
# ---------------------------------------------------------------------------

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
    state = AppState()
    handler = make_handler(root, config_path, experiment_dir, clips, state)
    server = ThreadingHTTPServer((host, port), handler)
    actual_host, actual_port = server.server_address
    display_host = host if host != "0.0.0.0" else actual_host
    print(f"FutBotMX: http://{display_host}:{actual_port}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("Stopping FutBotMX", flush=True)
    finally:
        server.server_close()


def make_handler(
    root: Path,
    config_path: Path,
    experiment_dir: Path,
    clips: list[ClipOption],
    state: AppState,
) -> type[BaseHTTPRequestHandler]:
    config = load_config(root / config_path)
    playback_config = live_playback_config_from_project(root, config, DEFAULT_LIVE_PLAYBACK_EXPERIMENT_DIR)
    playback_context = build_live_playback_context(root, playback_config)
    playback_context["config_path"] = config_path
    LivePlaybackHandler = make_live_playback_handler(root, playback_context, route_prefix="/playback")

    class AppHandler(LivePlaybackHandler):
        server_version = "FutBotMXApp/1.0"

        def do_GET(self) -> None:
            parsed = urlparse(self.path)
            path = parsed.path

            if path == "/playback" or path.startswith("/playback/"):
                super().do_GET()
                return
            if path == "/health":
                self._send_text("ok\n", "text/plain; charset=utf-8")
                return
            if path == "/artifact":
                self._send_artifact(parsed.query)
                return
            if path.startswith("/files/"):
                self._send_file_path(unquote(path[len("/files/"):]))
                return
            if path == "/analyze-progress":
                self._stream_progress()
                return
            if path == "/analyze":
                self._send_html(render_analyze(root, clips, state))
                return
            if path == "/results":
                self._send_html(render_results(root, state))
                return
            if path in ("/", "/index.html"):
                self._send_html(render_home(root, state))
                return
            self.send_error(404)

        def do_POST(self) -> None:
            parsed = urlparse(self.path)
            if parsed.path == "/playback" or parsed.path.startswith("/playback/"):
                super().do_POST()
                return
            length = int(self.headers.get("Content-Length", "0") or "0")
            body = self.rfile.read(length).decode("utf-8")
            form = parse_qs(body)
            if parsed.path == "/start-analysis":
                self._start_analysis(form)
            else:
                self.send_error(404)

        def log_message(self, format: str, *args: Any) -> None:
            sys.stderr.write("app: " + format % args + "\n")

        def _start_analysis(self, form: dict[str, list[str]]) -> None:
            if state.snapshot()["status"] == "running":
                self.send_response(409)
                self.send_header("Content-Type", "text/plain; charset=utf-8")
                self.end_headers()
                self.wfile.write(b"pipeline already running\n")
                return
            request = pipeline_request_from_form(form, clips)
            if not request.video_path:
                self._send_html(render_analyze(root, clips, state))
                return
            _launch_pipeline(root, request, state)
            self.send_response(303)
            self.send_header("Location", "/analyze")
            self.end_headers()

        def _stream_progress(self) -> None:
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Cache-Control", "no-cache")
            self.send_header("Connection", "keep-alive")
            self.end_headers()
            sent = 0
            try:
                while True:
                    snap = state.snapshot()
                    log = state.log_snapshot()
                    for line in log[sent:]:
                        stage = _classify_stage(line)
                        msg = json.dumps({"line": line, "stage": stage}, ensure_ascii=True)
                        self.wfile.write(f"data: {msg}\n\n".encode())
                        sent += 1
                    self.wfile.flush()
                    if snap["status"] in ("complete", "error") and sent >= len(log):
                        final = {"stage": snap["status"], "experiment_dir": snap["experiment_dir"]}
                        self.wfile.write(f"data: {json.dumps(final)}\n\n".encode())
                        self.wfile.flush()
                        break
                    time.sleep(0.25)
            except (BrokenPipeError, ConnectionResetError, OSError):
                pass

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
            self._send_file_path(requested)

        def _send_file_path(self, requested: str) -> None:
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

    return AppHandler


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _classify_stage(line: str) -> str:
    lower = line.lower()
    if any(k in lower for k in ("grounded", "owlv2", "sam", "segment", "mask", "detection")):
        return "segmentation"
    if any(k in lower for k in ("tracking", "level3", "voronoi", "interaction", "highlight", "event", "dashboard", "reel", "tactical")):
        return "analysis"
    return ""


def _clips_from_legacy_closure(config: dict[str, Any]) -> list[ClipOption]:
    closure = config.get("level2_closure", {})
    raw_clips = closure.get("clips", []) if isinstance(closure, dict) else []
    clips = []
    for raw in raw_clips:
        if not isinstance(raw, dict):
            continue
        width = _coerce_int(raw.get("width"), 0, minimum=0)
        height = _coerce_int(raw.get("height"), 0, minimum=0)
        roi = _tuple_roi(raw.get("roi"), width, height)
        clips.append(ClipOption(
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
        ))
    return clips


def _clips_from_legacy_multiclip(config: dict[str, Any]) -> list[ClipOption]:
    multiclip = config.get("level2_multiclip", {})
    raw_clips = multiclip.get("clips", []) if isinstance(multiclip, dict) else []
    clips = []
    for raw in raw_clips:
        if not isinstance(raw, dict):
            continue
        width = _coerce_int(raw.get("width"), 0, minimum=0)
        height = _coerce_int(raw.get("height"), 0, minimum=0)
        clips.append(ClipOption(
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
        ))
    return clips


def _tuple_roi(value: Any, width: int, height: int) -> tuple[int, int, int, int]:
    if isinstance(value, (list, tuple)) and len(value) == 4:
        return tuple(_coerce_int(part, 0, minimum=0) for part in value)  # type: ignore[return-value]
    return (0, 0, width, height)


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


def _esc(value: Any) -> str:
    return html.escape(str(value), quote=True)


def _file_href(path: str) -> str:
    return "/files/" + quote(path, safe="/")


def _timestamp() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S%z")
