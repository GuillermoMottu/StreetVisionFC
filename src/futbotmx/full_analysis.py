from __future__ import annotations

import csv
import json
import os
import re
import shutil
import subprocess
import sys
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from futbotmx.config import load_config, write_config_snapshot
from futbotmx.video_io import inspect_video


RULE_VERSION = "full_analysis_v0.1"
DEFAULT_LEVEL2_ROOT = Path("experiments/test_017_level2_closure")
DEFAULT_EXPERIMENT_SLUG = "full_analysis"
MANIFEST_FIELDS = ["asset_id", "asset_type", "path", "source_artifact", "is_versioned", "role", "notes"]
STAGE_FIELDS = [
    "stage_id",
    "stage_name",
    "kind",
    "execution_policy",
    "status",
    "output_dir",
    "command",
    "duration_sec",
    "outputs",
    "notes",
]


@dataclass(frozen=True)
class FullAnalysisRequest:
    video: str
    clip_id: str
    start_frame: int
    end_frame: int
    config_path: str = "configs/default.yaml"
    experiment_dir: str = ""
    detections: str = ""
    tracks: str = ""
    level2_root: str = DEFAULT_LEVEL2_ROOT.as_posix()
    calibration_json: str = ""
    top_highlights: int = 4
    segment_count: int = 4


@dataclass(frozen=True)
class StageResult:
    stage_id: str
    stage_name: str
    kind: str
    execution_policy: str
    status: str
    output_dir: str
    command: str = ""
    duration_sec: float = 0.0
    outputs: list[str] = field(default_factory=list)
    notes: str = ""


@dataclass(frozen=True)
class FullAnalysisResult:
    status: str
    request: FullAnalysisRequest
    stages: list[StageResult]
    experiment_dir: str
    summary_path: str
    manifest_path: str


def next_experiment_dir(root: Path, clip_id: str, start_frame: int, end_frame: int) -> Path:
    experiments = root / "experiments"
    highest = 0
    if experiments.exists():
        for path in experiments.iterdir():
            match = re.match(r"test_(\d+)_", path.name)
            if match:
                highest = max(highest, int(match.group(1)))
    slug = _slug(f"{DEFAULT_EXPERIMENT_SLUG}_{clip_id}_{start_frame}_{end_frame}")
    return Path("experiments") / f"test_{highest + 1:03d}_{slug}"


def stage_plan_template(request: FullAnalysisRequest, root: Path | None = None) -> list[StageResult]:
    repo_root = root or Path.cwd()
    detections = _optional_repo_path(repo_root, request.detections)
    tracks = _optional_repo_path(repo_root, request.tracks)
    level2_tracks = _repo_path(repo_root, Path(request.level2_root) / request.clip_id / "tracks_level2.csv")
    detections_available = bool(detections and detections.exists())
    tracks_available = bool(tracks and tracks.exists())
    level2_available = level2_tracks.exists()
    sam_status = "pass" if detections_available else "requires_gpu"
    tracking_status = "pass" if (detections_available or tracks_available or level2_available) else "blocked"
    return [
        _planned("setup", "Preparar experimento", "lightweight", "local_stdlib", "pending"),
        _planned("ingestion", "Ingesta de video", "lightweight", "opencv_metadata", "pending"),
        _planned("sam3_detections", "SAM 3 / detecciones", "requires_gpu", "laptop_or_precomputed_detections", sam_status),
        _planned("tracking", "Tracking", "lightweight_or_reused", "from_detections_or_level2_tracks", tracking_status),
        _planned("level1_events", "Eventos Nivel 1", "lightweight", "rules_from_tracks", "pending"),
        _planned("level2_events", "Eventos Nivel 2", "lightweight", "rules_from_tracks", "pending"),
        _planned("level3_spatial", "Nivel 3 espacial", "lightweight", "homography_or_precomputed_tracks", "pending"),
        _planned("team_assignment", "Asignacion de equipos", "lightweight", "heuristic_or_manual_csv", "pending"),
        _planned("level3_metrics", "Metricas Nivel 3", "lightweight", "rules_from_rectified_tracks", "pending"),
        _planned("level3_events", "Eventos avanzados Nivel 3", "lightweight", "rules_and_highlight_ranking", "pending"),
        _planned("level3_visualizations", "Visualizaciones Nivel 3", "lightweight", "static_png_assets", "pending"),
        _planned("dashboard", "Dashboard final", "lightweight", "static_html", "pending"),
        _planned("reel", "Reel local", "lightweight", "static_demo_and_render_plan", "pending"),
    ]


def run_full_analysis(
    root: Path,
    request: FullAnalysisRequest,
    python_executable: str | None = None,
) -> FullAnalysisResult:
    repo_root = root.resolve()
    python = python_executable or sys.executable
    experiment_dir = Path(request.experiment_dir) if request.experiment_dir else next_experiment_dir(repo_root, request.clip_id, request.start_frame, request.end_frame)
    experiment_path = _repo_path(repo_root, experiment_dir)
    experiment_path.mkdir(parents=True, exist_ok=True)
    config = load_config(_repo_path(repo_root, request.config_path))
    clip_info = clip_info_from_config(config, request.clip_id)
    stages: list[StageResult] = []
    context: dict[str, Path] = {}

    stages.append(_setup_stage(repo_root, request, experiment_path))
    stages.append(_ingestion_stage(repo_root, request, experiment_path, config, clip_info))
    stages.append(_detections_stage(repo_root, request, experiment_path, config))
    tracking = _tracking_stage(repo_root, request, experiment_path, config, python)
    stages.append(tracking)
    if tracking.status == "pass":
        context["tracks"] = experiment_path / "tracking" / "tracks.csv"

    metadata = effective_clip_metadata(repo_root, request, clip_info, experiment_path)
    level1 = _level1_stage(repo_root, request, experiment_path, config, python, context.get("tracks"), metadata)
    stages.append(level1)
    level2 = _level2_stage(repo_root, request, experiment_path, python, context.get("tracks"), metadata)
    stages.append(level2)
    spatial = _spatial_stage(repo_root, request, experiment_path, config, python, context.get("tracks"))
    stages.append(spatial)
    spatial_tracks = experiment_path / "level3_spatial" / "level3_tracks.csv"
    if spatial_tracks.exists():
        context["level3_tracks"] = spatial_tracks

    team = _team_assignment_stage(repo_root, request, experiment_path, python, context.get("level3_tracks"))
    stages.append(team)
    team_tracks = experiment_path / "team_assignment" / "level3_tracks_with_teams.csv"
    if team_tracks.exists():
        context["level3_tracks"] = team_tracks
    tactical = _level3_metrics_stage(repo_root, request, experiment_path, python, context.get("level3_tracks"))
    stages.append(tactical)
    advanced = _level3_events_stage(repo_root, request, experiment_path, python, context.get("level3_tracks"))
    stages.append(advanced)
    visualizations = _level3_visualizations_stage(repo_root, request, experiment_path, python, context.get("level3_tracks"))
    stages.append(visualizations)
    dashboard = _dashboard_stage(repo_root, request, experiment_path, python)
    stages.append(dashboard)
    reel = _reel_stage(repo_root, request, experiment_path, python)
    stages.append(reel)

    _write_root_outputs(repo_root, request, config, experiment_path, stages)
    status = "pass" if all(stage.status in {"pass", "requires_gpu", "skipped"} for stage in stages) else "fail"
    return FullAnalysisResult(
        status=status,
        request=request,
        stages=stages,
        experiment_dir=_rel(repo_root, experiment_path),
        summary_path=_rel(repo_root, experiment_path / "summary.md"),
        manifest_path=_rel(repo_root, experiment_path / "full_analysis_manifest.csv"),
    )


def clip_info_from_config(config: dict[str, Any], clip_id: str) -> dict[str, Any]:
    for section in ("level2_closure", "level2_multiclip"):
        raw_section = config.get(section, {})
        clips = raw_section.get("clips", []) if isinstance(raw_section, dict) else []
        for clip in clips:
            if isinstance(clip, dict) and str(clip.get("clip_id", "")) == clip_id:
                return dict(clip)
    return {}


def effective_clip_metadata(
    root: Path,
    request: FullAnalysisRequest,
    clip_info: dict[str, Any],
    experiment_path: Path,
) -> dict[str, float | int]:
    metadata_path = experiment_path / "ingestion" / "video_metadata.json"
    metadata: dict[str, Any] = {}
    if metadata_path.exists():
        with metadata_path.open("r", encoding="utf-8") as handle:
            metadata = json.load(handle)
    fps = float(clip_info.get("fps") or metadata.get("fps") or 30.0)
    width = int(clip_info.get("width") or metadata.get("width") or 1360)
    height = int(clip_info.get("height") or metadata.get("height") or 1808)
    return {"fps": fps, "width": width, "height": height}


def manifest_rows_for_paths(root: Path, experiment_path: Path, paths: list[Path]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for path in sorted(paths):
        if not path.exists() or not path.is_file():
            continue
        rel_to_exp = path.relative_to(experiment_path).as_posix()
        rows.append(
            _manifest_row(
                _asset_id(rel_to_exp),
                path.suffix.lstrip(".") or "file",
                rel_to_exp,
                "full_analysis",
                True,
                _role_from_path(rel_to_exp),
                f"size_bytes={path.stat().st_size}",
            )
        )
    return rows


def _setup_stage(root: Path, request: FullAnalysisRequest, experiment_path: Path) -> StageResult:
    started = time.monotonic()
    request_path = experiment_path / "request.json"
    request_path.write_text(json.dumps(asdict(request), indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    result = StageResult(
        "setup",
        "Preparar experimento",
        "lightweight",
        "local_stdlib",
        "pass",
        _rel(root, experiment_path),
        outputs=[_rel(root, request_path)],
        notes="Experiment folder and request snapshot created.",
        duration_sec=time.monotonic() - started,
    )
    _ensure_stage_files(root, experiment_path, result, {"request": asdict(request)})
    return result


def _ingestion_stage(
    root: Path,
    request: FullAnalysisRequest,
    experiment_path: Path,
    config: dict[str, Any],
    clip_info: dict[str, Any],
) -> StageResult:
    stage_dir = experiment_path / "ingestion"
    stage_dir.mkdir(parents=True, exist_ok=True)
    started = time.monotonic()
    video_path = _repo_path(root, request.video)
    metadata_path = stage_dir / "video_metadata.json"
    status = "pass"
    notes = "Video metadata inspected with OpenCV."
    try:
        metadata = inspect_video(video_path).to_dict()
        metadata["exists"] = True
    except (FileNotFoundError, ValueError) as exc:
        status = "fail"
        notes = str(exc)
        metadata = {
            "path": request.video,
            "exists": False,
            "fps": float(clip_info.get("fps", 0.0) or 0.0),
            "width": int(clip_info.get("width", 0) or 0),
            "height": int(clip_info.get("height", 0) or 0),
            "frame_count": 0,
            "duration_sec": 0.0,
        }
    metadata["clip_id"] = request.clip_id
    metadata["frame_window"] = {"start_frame": request.start_frame, "end_frame": request.end_frame}
    metadata_path.write_text(json.dumps(metadata, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    result = StageResult(
        "ingestion",
        "Ingesta de video",
        "lightweight",
        "opencv_metadata",
        status,
        _rel(root, stage_dir),
        command=f"inspect_video {request.video}",
        duration_sec=time.monotonic() - started,
        outputs=[_rel(root, metadata_path)],
        notes=notes,
    )
    _ensure_stage_files(root, stage_dir, result, {"clip_info": clip_info, "video_metadata": metadata}, config)
    return result


def _detections_stage(root: Path, request: FullAnalysisRequest, experiment_path: Path, config: dict[str, Any]) -> StageResult:
    stage_dir = experiment_path / "detections"
    stage_dir.mkdir(parents=True, exist_ok=True)
    started = time.monotonic()
    outputs: list[str] = []
    if request.detections:
        source = _repo_path(root, request.detections)
        target = stage_dir / "detections.json"
        if source.exists():
            _copy_file(source, target)
            status = "pass"
            notes = "Precomputed detections copied into the experiment."
            outputs.append(_rel(root, target))
        else:
            status = "fail"
            notes = f"Detections file not found: {request.detections}"
    else:
        status = "requires_gpu"
        notes = "SAM 3 inference is intentionally documented as a laptop/GPU stage; provide --detections to execute tracking from fresh detections."
        requirements = stage_dir / "requirements.md"
        requirements.write_text(
            "\n".join(
                [
                    "# SAM 3 / Detecciones",
                    "",
                    "- Estado: `requiere_gpu`.",
                    "- Equipo recomendado: laptop MSI con GPU.",
                    "- Entrada esperada: detecciones normalizadas en JSON via `--detections`.",
                    "- En escritorio se reutilizan tracks ligeros existentes cuando estan disponibles.",
                    "",
                ]
            ),
            encoding="utf-8",
        )
        outputs.append(_rel(root, requirements))
    result = StageResult(
        "sam3_detections",
        "SAM 3 / detecciones",
        "requires_gpu",
        "laptop_or_precomputed_detections",
        status,
        _rel(root, stage_dir),
        command="SAM3 external GPU run" if not request.detections else f"copy {request.detections}",
        duration_sec=time.monotonic() - started,
        outputs=outputs,
        notes=notes,
    )
    _ensure_stage_files(root, stage_dir, result, {"detections": request.detections}, config)
    return result


def _tracking_stage(
    root: Path,
    request: FullAnalysisRequest,
    experiment_path: Path,
    config: dict[str, Any],
    python: str,
) -> StageResult:
    stage_dir = experiment_path / "tracking"
    stage_dir.mkdir(parents=True, exist_ok=True)
    target = stage_dir / "tracks.csv"
    started = time.monotonic()
    if request.tracks:
        source = _repo_path(root, request.tracks)
        if source.exists():
            _copy_file(source, target)
            result = StageResult(
                "tracking",
                "Tracking",
                "lightweight_or_reused",
                "provided_tracks",
                "pass",
                _rel(root, stage_dir),
                command=f"copy {request.tracks}",
                duration_sec=time.monotonic() - started,
                outputs=[_rel(root, target)],
                notes="Provided tracks copied into the full analysis experiment.",
            )
            _ensure_stage_files(root, stage_dir, result, {"source_tracks": request.tracks}, config)
            return result
        return _failed_stage(root, stage_dir, "tracking", "Tracking", "Provided tracks not found.", time.monotonic() - started)

    detections = experiment_path / "detections" / "detections.json"
    if detections.exists():
        command = [
            python,
            "scripts/run_tracking.py",
            "--detections",
            _rel(root, detections),
            "--output",
            _rel(root, target),
        ]
        result = _command_stage(root, "tracking", "Tracking", "lightweight_or_reused", "from_detections", stage_dir, command, timeout=180)
        _ensure_stage_files(root, stage_dir, result, {"source_detections": _rel(root, detections)}, config)
        return result

    source = _repo_path(root, Path(request.level2_root) / request.clip_id / "tracks_level2.csv")
    if source.exists():
        _copy_file(source, target)
        result = StageResult(
            "tracking",
            "Tracking",
            "lightweight_or_reused",
            "reused_level2_closure_tracks",
            "pass",
            _rel(root, stage_dir),
            command=f"copy {_rel(root, source)}",
            duration_sec=time.monotonic() - started,
            outputs=[_rel(root, target)],
            notes="No fresh detections were provided; reused lightweight Level 2 closure tracks for this clip.",
        )
        _ensure_stage_files(root, stage_dir, result, {"source_tracks": _rel(root, source)}, config)
        return result

    return _failed_stage(root, stage_dir, "tracking", "Tracking", "No detections, provided tracks or Level 2 closure tracks were available.", time.monotonic() - started)


def _level1_stage(
    root: Path,
    request: FullAnalysisRequest,
    experiment_path: Path,
    config: dict[str, Any],
    python: str,
    tracks: Path | None,
    metadata: dict[str, float | int],
) -> StageResult:
    stage_dir = experiment_path / "level1_events"
    stage_dir.mkdir(parents=True, exist_ok=True)
    if not tracks or not tracks.exists():
        return _skipped_stage(root, stage_dir, "level1_events", "Eventos Nivel 1", "Tracks are required before Level 1 events.", config)
    output = stage_dir / "events.json"
    command = [
        python,
        "scripts/run_events.py",
        "--config",
        request.config_path,
        "--tracks",
        _rel(root, tracks),
        "--output",
        _rel(root, output),
        "--fps",
        str(metadata["fps"]),
        "--field-width",
        str(metadata["width"]),
        "--field-height",
        str(metadata["height"]),
    ]
    result = _command_stage(root, "level1_events", "Eventos Nivel 1", "lightweight", "rules_from_tracks", stage_dir, command)
    _ensure_stage_files(root, stage_dir, result, {"tracks": _rel(root, tracks), "metadata": metadata}, config)
    return result


def _level2_stage(
    root: Path,
    request: FullAnalysisRequest,
    experiment_path: Path,
    python: str,
    tracks: Path | None,
    metadata: dict[str, float | int],
) -> StageResult:
    stage_dir = experiment_path / "level2_events"
    if not tracks or not tracks.exists():
        return _skipped_stage(root, stage_dir, "level2_events", "Eventos Nivel 2", "Tracks are required before Level 2 events.")
    command = [
        python,
        "scripts/run_level2_events.py",
        "--config",
        request.config_path,
        "--tracks",
        _rel(root, tracks),
        "--experiment",
        _rel(root, stage_dir),
        "--fps",
        str(metadata["fps"]),
        "--field-width",
        str(metadata["width"]),
        "--field-height",
        str(metadata["height"]),
        "--overlay-dir",
        str(Path(request.level2_root) / request.clip_id),
    ]
    result = _command_stage(root, "level2_events", "Eventos Nivel 2", "lightweight", "rules_from_tracks", stage_dir, command)
    _ensure_stage_files(root, stage_dir, result, {"tracks": _rel(root, tracks), "metadata": metadata})
    return result


def _spatial_stage(
    root: Path,
    request: FullAnalysisRequest,
    experiment_path: Path,
    config: dict[str, Any],
    python: str,
    tracks: Path | None,
) -> StageResult:
    stage_dir = experiment_path / "level3_spatial"
    source_tracks = _repo_path(root, Path(request.level2_root) / request.clip_id / "tracks_level2.csv")
    if source_tracks.exists():
        command = [
            python,
            "scripts/run_level3_spatial_model.py",
            "--config",
            request.config_path,
            "--source-dir",
            request.level2_root,
            "--experiment",
            _rel(root, stage_dir),
            "--clips",
            request.clip_id,
        ]
        if request.calibration_json:
            command.extend(["--calibration-json", request.calibration_json])
        result = _command_stage(root, "level3_spatial", "Nivel 3 espacial", "lightweight", "homography_from_level2_tracks", stage_dir, command, timeout=240)
        _ensure_stage_files(root, stage_dir, result, {"source_tracks": _rel(root, source_tracks)}, config)
        return result

    if tracks and tracks.exists() and _csv_has_fields(tracks, {"x_norm", "y_norm"}):
        stage_dir.mkdir(parents=True, exist_ok=True)
        target = stage_dir / "level3_tracks.csv"
        _copy_file(tracks, target)
        result = StageResult(
            "level3_spatial",
            "Nivel 3 espacial",
            "lightweight",
            "provided_level3_tracks",
            "pass",
            _rel(root, stage_dir),
            command=f"copy {_rel(root, tracks)}",
            outputs=[_rel(root, target)],
            notes="Provided tracks already include x_norm/y_norm; spatial rectification was reused.",
        )
        _ensure_stage_files(root, stage_dir, result, {"source_tracks": _rel(root, tracks)}, config)
        return result

    return _skipped_stage(root, stage_dir, "level3_spatial", "Nivel 3 espacial", "Level 2 tracks or rectified Level 3 tracks are required.", config)


def _team_assignment_stage(root: Path, request: FullAnalysisRequest, experiment_path: Path, python: str, tracks: Path | None) -> StageResult:
    stage_dir = experiment_path / "team_assignment"
    if not tracks or not tracks.exists():
        return _skipped_stage(root, stage_dir, "team_assignment", "Asignacion de equipos", "Level 3 tracks are required before team assignment.")
    command = [
        python,
        "scripts/run_team_assignment.py",
        "--config",
        request.config_path,
        "--tracks",
        _rel(root, tracks),
        "--experiment",
        _rel(root, stage_dir),
    ]
    result = _command_stage(root, "team_assignment", "Asignacion de equipos", "lightweight", "heuristic_or_manual_csv", stage_dir, command, timeout=180)
    _ensure_stage_files(root, stage_dir, result, {"tracks": _rel(root, tracks)})
    return result


def _level3_metrics_stage(root: Path, request: FullAnalysisRequest, experiment_path: Path, python: str, tracks: Path | None) -> StageResult:
    stage_dir = experiment_path / "level3_metrics"
    if not tracks or not tracks.exists():
        return _skipped_stage(root, stage_dir, "level3_metrics", "Metricas Nivel 3", "Level 3 tracks are required before tactical metrics.")
    command = [
        python,
        "scripts/run_level3_tactical_metrics.py",
        "--config",
        request.config_path,
        "--tracks",
        _rel(root, tracks),
        "--experiment",
        _rel(root, stage_dir),
    ]
    result = _command_stage(root, "level3_metrics", "Metricas Nivel 3", "lightweight", "rules_from_rectified_tracks", stage_dir, command, timeout=180)
    _ensure_stage_files(root, stage_dir, result, {"tracks": _rel(root, tracks)})
    return result


def _level3_events_stage(root: Path, request: FullAnalysisRequest, experiment_path: Path, python: str, tracks: Path | None) -> StageResult:
    stage_dir = experiment_path / "level3_events"
    metrics_dir = experiment_path / "level3_metrics"
    interaction_metrics = metrics_dir / "interaction_metrics.csv"
    interaction_edges = metrics_dir / "interaction_edges.csv"
    if not tracks or not tracks.exists() or not interaction_metrics.exists() or not interaction_edges.exists():
        return _skipped_stage(root, stage_dir, "level3_events", "Eventos avanzados Nivel 3", "Tracks and interaction metrics are required before advanced events.")
    command = [
        python,
        "scripts/run_level3_advanced_events.py",
        "--config",
        request.config_path,
        "--experiment",
        _rel(root, stage_dir),
        "--tracks",
        _rel(root, tracks),
        "--interaction-metrics",
        _rel(root, interaction_metrics),
        "--interaction-edges",
        _rel(root, interaction_edges),
        "--level2-root",
        request.level2_root,
        "--primary-clip",
        request.clip_id,
    ]
    result = _command_stage(root, "level3_events", "Eventos avanzados Nivel 3", "lightweight", "rules_and_highlight_ranking", stage_dir, command, timeout=180)
    _ensure_stage_files(root, stage_dir, result, {"tracks": _rel(root, tracks), "interaction_metrics": _rel(root, interaction_metrics)})
    return result


def _level3_visualizations_stage(root: Path, request: FullAnalysisRequest, experiment_path: Path, python: str, tracks: Path | None) -> StageResult:
    stage_dir = experiment_path / "level3_visualizations"
    spatial_dir = experiment_path / "level3_spatial"
    metrics_dir = experiment_path / "level3_metrics"
    events_dir = experiment_path / "level3_events"
    required = [
        tracks,
        spatial_dir / "field_calibration.json",
        metrics_dir / "spatial_control.csv",
        metrics_dir / "voronoi_frames.csv",
        metrics_dir / "interaction_graph.json",
        metrics_dir / "interaction_edges.csv",
        events_dir / "level3_highlights.csv",
        events_dir / "level3_events.json",
    ]
    if not all(path and path.exists() for path in required):
        return _skipped_stage(root, stage_dir, "level3_visualizations", "Visualizaciones Nivel 3", "Level 3 metrics, calibration and highlights are required before visualizations.")
    command = [
        python,
        "scripts/run_level3_visualizations.py",
        "--config",
        request.config_path,
        "--experiment",
        _rel(root, stage_dir),
        "--tracks",
        _rel(root, tracks),  # type: ignore[arg-type]
        "--calibration",
        _rel(root, spatial_dir / "field_calibration.json"),
        "--spatial-control",
        _rel(root, metrics_dir / "spatial_control.csv"),
        "--voronoi-frames",
        _rel(root, metrics_dir / "voronoi_frames.csv"),
        "--interaction-graph",
        _rel(root, metrics_dir / "interaction_graph.json"),
        "--interaction-edges",
        _rel(root, metrics_dir / "interaction_edges.csv"),
        "--highlights",
        _rel(root, events_dir / "level3_highlights.csv"),
        "--events",
        _rel(root, events_dir / "level3_events.json"),
        "--level2-root",
        request.level2_root,
        "--top-highlights",
        str(request.top_highlights),
    ]
    result = _command_stage(root, "level3_visualizations", "Visualizaciones Nivel 3", "lightweight", "static_png_assets", stage_dir, command, timeout=240)
    _ensure_stage_files(root, stage_dir, result, {"tracks": _rel(root, tracks)})  # type: ignore[arg-type]
    return result


def _dashboard_stage(root: Path, request: FullAnalysisRequest, experiment_path: Path, python: str) -> StageResult:
    stage_dir = experiment_path / "dashboard"
    metrics_dir = experiment_path / "level3_metrics"
    events_dir = experiment_path / "level3_events"
    visualizations_dir = experiment_path / "level3_visualizations"
    required = [
        metrics_dir / "level3_metrics.csv",
        metrics_dir / "level3_metrics.json",
        metrics_dir / "interaction_edges.csv",
        events_dir / "level3_highlights.csv",
        events_dir / "level3_events.json",
        events_dir / "level3_narrative.md",
        visualizations_dir / "visualization_manifest.csv",
    ]
    if not all(path.exists() for path in required):
        return _skipped_stage(root, stage_dir, "dashboard", "Dashboard final", "Level 3 metrics, events and visualization manifest are required before dashboard.")
    command = [
        python,
        "scripts/run_level3_dashboard.py",
        "--config",
        request.config_path,
        "--experiment",
        _rel(root, stage_dir),
        "--metrics-csv",
        _rel(root, metrics_dir / "level3_metrics.csv"),
        "--metrics-json",
        _rel(root, metrics_dir / "level3_metrics.json"),
        "--interaction-edges",
        _rel(root, metrics_dir / "interaction_edges.csv"),
        "--highlights",
        _rel(root, events_dir / "level3_highlights.csv"),
        "--events",
        _rel(root, events_dir / "level3_events.json"),
        "--narrative",
        _rel(root, events_dir / "level3_narrative.md"),
        "--visualizations-dir",
        _rel(root, visualizations_dir),
        "--visualization-manifest",
        _rel(root, visualizations_dir / "visualization_manifest.csv"),
    ]
    result = _command_stage(root, "dashboard", "Dashboard final", "lightweight", "static_html", stage_dir, command, timeout=180)
    _ensure_stage_files(root, stage_dir, result, {"visualizations": _rel(root, visualizations_dir)})
    return result


def _reel_stage(root: Path, request: FullAnalysisRequest, experiment_path: Path, python: str) -> StageResult:
    stage_dir = experiment_path / "reel"
    events_dir = experiment_path / "level3_events"
    visualizations_dir = experiment_path / "level3_visualizations"
    dashboard_html = experiment_path / "dashboard" / "dashboard.html"
    required = [
        events_dir / "level3_highlights.csv",
        events_dir / "level3_events.json",
        events_dir / "overlay_validation.csv",
        visualizations_dir / "visualization_manifest.csv",
        visualizations_dir / "highlight_storyboard_manifest.csv",
        dashboard_html,
    ]
    if not all(path.exists() for path in required):
        return _skipped_stage(root, stage_dir, "reel", "Reel local", "Highlights, visualizations and dashboard are required before reel.")
    local_reel = Path("local_outputs") / "full_analysis" / f"{request.clip_id}_{request.start_frame}_{request.end_frame}_reel.mp4"
    command = [
        python,
        "scripts/run_level3_reel.py",
        "--config",
        request.config_path,
        "--experiment",
        _rel(root, stage_dir),
        "--highlights",
        _rel(root, events_dir / "level3_highlights.csv"),
        "--events",
        _rel(root, events_dir / "level3_events.json"),
        "--overlay-validation",
        _rel(root, events_dir / "overlay_validation.csv"),
        "--advanced-events-dir",
        _rel(root, events_dir),
        "--visualization-manifest",
        _rel(root, visualizations_dir / "visualization_manifest.csv"),
        "--storyboard-manifest",
        _rel(root, visualizations_dir / "highlight_storyboard_manifest.csv"),
        "--visualizations-dir",
        _rel(root, visualizations_dir),
        "--dashboard-html",
        _rel(root, dashboard_html),
        "--local-reel-path",
        local_reel.as_posix(),
        "--segment-count",
        str(request.segment_count),
    ]
    result = _command_stage(root, "reel", "Reel local", "lightweight", "static_demo_and_render_plan", stage_dir, command, timeout=180)
    _ensure_stage_files(root, stage_dir, result, {"dashboard_html": _rel(root, dashboard_html)})
    return result


def _command_stage(
    root: Path,
    stage_id: str,
    stage_name: str,
    kind: str,
    execution_policy: str,
    stage_dir: Path,
    command: list[str],
    timeout: int = 180,
) -> StageResult:
    stage_dir.mkdir(parents=True, exist_ok=True)
    started = time.monotonic()
    env = os.environ.copy()
    env.setdefault("MPLCONFIGDIR", "/tmp/matplotlib")
    try:
        completed = subprocess.run(command, cwd=root, env=env, capture_output=True, text=True, timeout=timeout)
        output = (completed.stdout + "\n" + completed.stderr).strip()
        status = "pass" if completed.returncode == 0 else "fail"
        notes = _last_lines(output) if output else f"returncode={completed.returncode}"
    except (FileNotFoundError, subprocess.SubprocessError) as exc:
        status = "fail"
        notes = str(exc)
    outputs = [_rel(root, path) for path in sorted(stage_dir.rglob("*")) if path.is_file()]
    return StageResult(
        stage_id,
        stage_name,
        kind,
        execution_policy,
        status,
        _rel(root, stage_dir),
        command=" ".join(command),
        duration_sec=time.monotonic() - started,
        outputs=outputs,
        notes=notes,
    )


def _ensure_stage_files(
    root: Path,
    stage_dir: Path,
    result: StageResult,
    extra_config: dict[str, Any] | None = None,
    base_config: dict[str, Any] | None = None,
) -> None:
    stage_dir.mkdir(parents=True, exist_ok=True)
    if not (stage_dir / "config.yaml").exists():
        config = dict(base_config or {})
        config["full_analysis_stage"] = {
            "rule_version": RULE_VERSION,
            "stage": asdict(result),
            "inputs": extra_config or {},
        }
        write_config_snapshot(config, stage_dir / "config.yaml")
    if not (stage_dir / "summary.md").exists():
        _write_stage_summary(stage_dir / "summary.md", result)
    _write_stage_manifest(stage_dir / "stage_manifest.csv", result)


def _write_stage_summary(path: Path, result: StageResult) -> None:
    lines = [
        f"# {result.stage_name}",
        "",
        "## Resultado",
        "",
        f"- Estado: `{result.status}`.",
        f"- Regla: `{RULE_VERSION}`.",
        f"- Tipo: `{result.kind}`.",
        f"- Politica: `{result.execution_policy}`.",
        f"- Duracion: `{result.duration_sec:.3f}s`.",
        f"- Notas: {result.notes}",
        "",
        "## Comando",
        "",
        "```bash",
        result.command or "no_aplica",
        "```",
        "",
        "## Artefactos",
        "",
    ]
    for output in result.outputs:
        lines.append(f"- `{output}`.")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_stage_manifest(path: Path, result: StageResult) -> None:
    stage_dir = path.parent
    files = [file for file in sorted(stage_dir.rglob("*")) if file.is_file() and file.name != path.name]
    rows = [
        _manifest_row(
            _asset_id(file.relative_to(stage_dir).as_posix()),
            file.suffix.lstrip(".") or "file",
            file.relative_to(stage_dir).as_posix(),
            result.stage_id,
            True,
            _role_from_path(file.as_posix()),
            f"stage_status={result.status}; size_bytes={file.stat().st_size}",
        )
        for file in files
    ]
    _write_csv(path, rows, MANIFEST_FIELDS)


def _write_root_outputs(
    root: Path,
    request: FullAnalysisRequest,
    config: dict[str, Any],
    experiment_path: Path,
    stages: list[StageResult],
) -> None:
    stage_rows = [_stage_row(stage) for stage in stages]
    _write_csv(experiment_path / "stage_plan.csv", stage_rows, STAGE_FIELDS)
    _write_csv(experiment_path / "runtime_metrics.csv", _runtime_rows(stages), ["stage_id", "status", "duration_sec", "outputs", "notes"])
    snapshot = dict(config)
    snapshot["full_analysis"] = {
        "rule_version": RULE_VERSION,
        "request": asdict(request),
        "stage_statuses": stage_rows,
        "outputs": [
            "config.yaml",
            "summary.md",
            "stage_plan.csv",
            "runtime_metrics.csv",
            "full_analysis_manifest.csv",
        ],
    }
    write_config_snapshot(snapshot, experiment_path / "config.yaml")
    _write_root_summary(root, experiment_path, request, stages)
    root_files = [
        experiment_path / "config.yaml",
        experiment_path / "summary.md",
        experiment_path / "stage_plan.csv",
        experiment_path / "runtime_metrics.csv",
        experiment_path / "request.json",
    ]
    _write_csv(experiment_path / "stage_manifest.csv", manifest_rows_for_paths(root, experiment_path, root_files), MANIFEST_FIELDS)
    paths = [file for file in experiment_path.rglob("*") if file.is_file()]
    _write_csv(experiment_path / "full_analysis_manifest.csv", manifest_rows_for_paths(root, experiment_path, paths), MANIFEST_FIELDS)
    root_files.append(experiment_path / "full_analysis_manifest.csv")
    _write_csv(experiment_path / "stage_manifest.csv", manifest_rows_for_paths(root, experiment_path, root_files), MANIFEST_FIELDS)
    paths = [file for file in experiment_path.rglob("*") if file.is_file()]
    _write_csv(experiment_path / "full_analysis_manifest.csv", manifest_rows_for_paths(root, experiment_path, paths), MANIFEST_FIELDS)


def _write_root_summary(root: Path, experiment_path: Path, request: FullAnalysisRequest, stages: list[StageResult]) -> None:
    fail_count = sum(1 for stage in stages if stage.status == "fail")
    pass_count = sum(1 for stage in stages if stage.status == "pass")
    gpu_count = sum(1 for stage in stages if stage.status == "requires_gpu")
    skipped_count = sum(1 for stage in stages if stage.status == "skipped")
    status = "pass" if fail_count == 0 else "fail"
    lines = [
        "# Pipeline Completo Para Video Nuevo",
        "",
        "## Resultado",
        "",
        f"- Estado: `{status}`.",
        f"- Regla: `{RULE_VERSION}`.",
        f"- Clip: `{request.clip_id}`.",
        f"- Video: `{request.video}`.",
        f"- Frames: `{request.start_frame}-{request.end_frame}`.",
        f"- Experimento: `{_rel(root, experiment_path)}`.",
        f"- Etapas pass: `{pass_count}`.",
        f"- Etapas que requieren GPU/insumo externo: `{gpu_count}`.",
        f"- Etapas saltadas: `{skipped_count}`.",
        f"- Etapas fallidas: `{fail_count}`.",
        "",
        "## Frontera Ligero / GPU",
        "",
        "- Ligeras en escritorio: ingesta de metadatos, tracking desde detecciones existentes, eventos Nivel 1/2, rectificacion Nivel 3, asignacion de equipos, metricas, eventos avanzados, visualizaciones estaticas, dashboard y reel demo.",
        "- Requiere laptop/GPU: SAM 3 para generar detecciones frescas desde video. En este comando se ejecuta si se entrega `--detections`; si no, queda documentado y se reutilizan tracks ligeros disponibles.",
        "- No se versiona MP4 final, checkpoints, frames masivos ni mascaras masivas.",
        "",
        "## Etapas",
        "",
    ]
    for stage in stages:
        lines.append(
            f"- `{stage.stage_id}` `{stage.status}` `{stage.kind}`: {stage.notes}"
        )
    lines.extend(
        [
            "",
            "## Artefactos Raiz",
            "",
            "- `config.yaml`",
            "- `summary.md`",
            "- `stage_plan.csv`",
            "- `runtime_metrics.csv`",
            "- `full_analysis_manifest.csv`",
            "",
            "## Comando",
            "",
            "```bash",
            (
                ".venv/bin/python scripts/run_full_analysis.py "
                f"--video \"{request.video}\" --clip-id {request.clip_id} "
                f"--start-frame {request.start_frame} --end-frame {request.end_frame}"
            ),
            "```",
        ]
    )
    (experiment_path / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def _failed_stage(root: Path, stage_dir: Path, stage_id: str, stage_name: str, notes: str, duration: float) -> StageResult:
    result = StageResult(stage_id, stage_name, "lightweight", "required_input", "fail", _rel(root, stage_dir), duration_sec=duration, notes=notes)
    _ensure_stage_files(root, stage_dir, result)
    return result


def _skipped_stage(
    root: Path,
    stage_dir: Path,
    stage_id: str,
    stage_name: str,
    notes: str,
    config: dict[str, Any] | None = None,
) -> StageResult:
    result = StageResult(stage_id, stage_name, "lightweight", "blocked_by_previous_stage", "skipped", _rel(root, stage_dir), notes=notes)
    _ensure_stage_files(root, stage_dir, result, base_config=config)
    return result


def _planned(stage_id: str, name: str, kind: str, policy: str, status: str) -> StageResult:
    return StageResult(stage_id, name, kind, policy, status, "")


def _stage_row(stage: StageResult) -> dict[str, Any]:
    return {
        "stage_id": stage.stage_id,
        "stage_name": stage.stage_name,
        "kind": stage.kind,
        "execution_policy": stage.execution_policy,
        "status": stage.status,
        "output_dir": stage.output_dir,
        "command": stage.command,
        "duration_sec": f"{stage.duration_sec:.3f}",
        "outputs": "|".join(stage.outputs),
        "notes": stage.notes,
    }


def _runtime_rows(stages: list[StageResult]) -> list[dict[str, Any]]:
    return [
        {
            "stage_id": stage.stage_id,
            "status": stage.status,
            "duration_sec": f"{stage.duration_sec:.3f}",
            "outputs": len(stage.outputs),
            "notes": stage.notes,
        }
        for stage in stages
    ]


def _manifest_row(asset_id: str, asset_type: str, path: str, source: str, versioned: bool, role: str, notes: str) -> dict[str, Any]:
    return {
        "asset_id": asset_id,
        "asset_type": asset_type,
        "path": path,
        "source_artifact": source,
        "is_versioned": str(versioned).lower(),
        "role": role,
        "notes": notes,
    }


def _write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def _copy_file(source: Path, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    if source.resolve() != target.resolve():
        shutil.copyfile(source, target)


def _csv_has_fields(path: Path, fields: set[str]) -> bool:
    with path.open("r", newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        return fields.issubset(set(reader.fieldnames or []))


def _repo_path(root: Path, path: str | Path) -> Path:
    candidate = Path(path)
    return candidate if candidate.is_absolute() else root / candidate


def _optional_repo_path(root: Path, path: str | Path) -> Path | None:
    if not path:
        return None
    return _repo_path(root, path)


def _rel(root: Path, path: str | Path) -> str:
    candidate = Path(path)
    try:
        return candidate.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return candidate.as_posix()


def _asset_id(path: str) -> str:
    return _slug(Path(path).with_suffix("").as_posix().replace("/", "_"))


def _slug(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9]+", "_", value).strip("_").lower()
    return cleaned or "artifact"


def _role_from_path(path: str) -> str:
    name = Path(path).name
    if name == "config.yaml":
        return "configuration"
    if "manifest" in name:
        return "manifest"
    if name == "summary.md":
        return "summary"
    if name.endswith(".png"):
        return "visual_evidence"
    if name.endswith(".html"):
        return "local_demo"
    if name.endswith(".json"):
        return "structured_data"
    if name.endswith(".csv"):
        return "tabular_data"
    return "artifact"


def _last_lines(output: str, limit: int = 700) -> str:
    lines = [line.strip() for line in output.splitlines() if line.strip()]
    text = " | ".join(lines[-3:])
    return text[-limit:]
