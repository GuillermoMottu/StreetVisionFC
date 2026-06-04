from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
import sys
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from futbotmx.config import load_config, write_config_snapshot
from futbotmx.events import detect_level2_events, write_level2_event_metrics, write_level2_events_json
from futbotmx.io.detections import FrameDetections, load_detections
from futbotmx.metrics import (
    compute_level2_metrics,
    read_tracks_csv,
    write_level2_metrics_csv,
    write_level2_metrics_json,
)
from futbotmx.tracking import ByteTrackUnavailableError, run_bytetrack, track_detections, write_tracks_csv


@dataclass(frozen=True)
class ClipSpec:
    clip_id: str
    role: str
    width: int
    height: int
    fps: float
    detections: str | None = None
    tracks: str | None = None
    metrics: str | None = None
    events: str | None = None
    notes: str = ""


DEFAULT_CLIPS = [
    ClipSpec(
        clip_id="video_595",
        role="candidate",
        width=1344,
        height=1792,
        fps=59.71505265331406,
        detections="experiments/test_009_level1_solidity/deduplication/video_595_detections_cleaned.json",
        notes="Buen recall de balon/robots; muestra sparse en frames 60,90,120,150,180.",
    ),
    ClipSpec(
        clip_id="video_667",
        role="candidate",
        width=1360,
        height=1808,
        fps=59.70695970695971,
        detections="experiments/test_009_level1_solidity/deduplication/video_667_detections_cleaned.json",
        notes="Robots visibles y multiples candidatos por frame; se usa deduplicacion/top-k previa.",
    ),
    ClipSpec(
        clip_id="video_836",
        role="baseline",
        width=1360,
        height=1808,
        fps=59.707724425887264,
        tracks="experiments/test_003_tracking/video_836_real_tracking_120_180/tracks_bytetrack.csv",
        metrics="experiments/test_012_level2_metrics/video_836_real_metrics_120_180/level2_metrics.json",
        events="experiments/test_013_level2_events/video_836_real_events_120_180/level2_events.json",
        notes="Baseline Nivel 2 con tracks ByteTrack densos en frames 120-180.",
    ),
    ClipSpec(
        clip_id="video_480",
        role="diagnostic",
        width=1360,
        height=1808,
        fps=59.6995427824951,
        detections="experiments/test_006_more_copafutmx_videos/video_480_short_window/detections_filtered_roi.json",
        notes="Diagnostico: no hay deteccion de balon en la muestra; no se ejecutan eventos deportivos.",
    ),
]


def sports_frames(frames: list[FrameDetections]) -> list[FrameDetections]:
    result: list[FrameDetections] = []
    for frame in frames:
        detections = tuple(
            detection
            for detection in frame.detections
            if detection.class_name == "ball" or "robot" in detection.class_name
        )
        result.append(FrameDetections(frame=frame.frame, detections=detections))
    return result


def clip_specs_from_config(config: dict[str, Any]) -> list[ClipSpec]:
    raw_clips = config.get("level2_multiclip", {}).get("clips", [])
    specs: list[ClipSpec] = []
    for raw in raw_clips:
        specs.append(
            ClipSpec(
                clip_id=str(raw["clip_id"]),
                role=str(raw["role"]),
                width=int(raw["width"]),
                height=int(raw["height"]),
                fps=float(raw["fps"]),
                detections=raw.get("detections"),
                tracks=raw.get("tracks"),
                metrics=raw.get("metrics"),
                events=raw.get("events"),
                notes=str(raw.get("notes", "")),
            )
        )
    return specs


def count_classes_from_detections(path: str | Path) -> Counter[str]:
    counts: Counter[str] = Counter()
    for frame in load_detections(path):
        counts.update(detection.class_name for detection in frame.detections)
    return counts


def load_json(path: str | Path) -> Any:
    with Path(path).open("r", encoding="utf-8") as handle:
        return json.load(handle)


def write_event_count_csv(path: Path, events: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    counts = Counter(event["event_type"] for event in events)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["event_type", "count"], lineterminator="\n")
        writer.writeheader()
        for event_type, count in sorted(counts.items()):
            writer.writerow({"event_type": event_type, "count": count})


def write_clip_summary(
    path: Path,
    clip: ClipSpec,
    tracks_path: Path | None,
    metrics: dict[str, Any] | None,
    events: list[dict[str, Any]] | None,
    detection_counts: Counter[str] | None,
    tracker_used: str = "",
) -> None:
    event_counts = Counter(event["event_type"] for event in events or [])
    reliability_counts = Counter(event.get("reliability", "unknown") for event in events or [])
    lines = [
        f"# {clip.clip_id}_level2_multiclip",
        "",
        "## Configuracion",
        "",
        f"- Rol: `{clip.role}`.",
        f"- FPS: `{clip.fps}`.",
        f"- Resolucion: `{clip.width}x{clip.height}`.",
        f"- Notas: {clip.notes}",
    ]
    if tracks_path:
        lines.append(f"- Tracks generados/usados: `{tracks_path}`.")
    if tracker_used:
        lines.append(f"- Tracker usado: `{tracker_used}`.")
    if detection_counts is not None:
        lines.extend(["", "## Detecciones", ""])
        for class_name, count in sorted(detection_counts.items()):
            lines.append(f"- `{class_name}`: `{count}`.")
    if metrics:
        summary = metrics.get("summary", {})
        lines.extend(
            [
                "",
                "## Metricas Nivel 2",
                "",
                f"- Frames observados: `{summary.get('observed_frames', 0)}`.",
                f"- Tracks: `{summary.get('track_count', 0)}`.",
                f"- Tiempo observado: `{summary.get('total_observed_seconds', 0)}s`.",
                f"- Posesion asignada: `{summary.get('possession_assigned_seconds', 0)}s`.",
            ]
        )
    if events is not None:
        lines.extend(["", "## Eventos Nivel 2", ""])
        if event_counts:
            for event_type, count in sorted(event_counts.items()):
                lines.append(f"- `{event_type}`: `{count}`.")
        else:
            lines.append("- Sin eventos generados.")
        lines.extend(["", "## Confiabilidad", ""])
        if reliability_counts:
            for reliability, count in sorted(reliability_counts.items()):
                lines.append(f"- `{reliability}`: `{count}`.")
        else:
            lines.append("- Sin confiabilidad reportada.")
    lines.extend(["", "## Politica De Archivos", "", "- No se genero ni versiono video completo."])
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def clip_row(
    clip: ClipSpec,
    metrics: dict[str, Any] | None,
    events: list[dict[str, Any]] | None,
    detection_counts: Counter[str] | None,
    tracks_path: Path | None,
) -> dict[str, Any]:
    summary = metrics.get("summary", {}) if metrics else {}
    event_counts = Counter(event["event_type"] for event in events or [])
    reliability_counts = Counter(event.get("reliability", "unknown") for event in events or [])
    return {
        "clip_id": clip.clip_id,
        "role": clip.role,
        "fps": f"{clip.fps:.6f}",
        "resolution": f"{clip.width}x{clip.height}",
        "tracks_file": str(tracks_path or clip.tracks or ""),
        "observed_frames": summary.get("observed_frames", 0),
        "track_count": summary.get("track_count", 0),
        "possession_assigned_seconds": summary.get("possession_assigned_seconds", 0),
        "ball_detections": detection_counts.get("ball", 0) if detection_counts else "",
        "robot_detections": sum(count for name, count in (detection_counts or {}).items() if "robot" in name),
        "ball_recovery": event_counts.get("ball_recovery", 0),
        "interception": event_counts.get("interception", 0),
        "highlight_play": event_counts.get("highlight_play", 0),
        "confiable": reliability_counts.get("confiable", 0),
        "provisional": reliability_counts.get("provisional", 0),
        "descartado": reliability_counts.get("descartado", 0),
        "notes": clip.notes,
    }


def process_candidate_clip(
    clip: ClipSpec,
    output_dir: Path,
    event_config: dict[str, Any],
    tracker_method: str,
    allow_simple_fallback: bool,
    max_distance_px: float,
    max_lost_frames: int,
    bytetrack_activation_threshold: float,
    bytetrack_lost_buffer: int,
    bytetrack_matching_threshold: float,
) -> tuple[dict[str, Any], list[dict[str, Any]], Counter[str], Path]:
    if clip.detections is None:
        raise ValueError(f"Candidate clip needs detections: {clip.clip_id}")
    frames = sports_frames(load_detections(clip.detections))
    tracker_used = tracker_method
    if tracker_method == "bytetrack":
        try:
            tracks = run_bytetrack(
                frames,
                frame_rate=clip.fps,
                track_activation_threshold=bytetrack_activation_threshold,
                lost_track_buffer=bytetrack_lost_buffer,
                minimum_matching_threshold=bytetrack_matching_threshold,
            )
        except ByteTrackUnavailableError:
            if not allow_simple_fallback:
                raise
            tracks = track_detections(frames, max_distance_px=max_distance_px, max_lost_frames=max_lost_frames)
            tracker_used = "simple_fallback"
    elif tracker_method == "simple":
        tracks = track_detections(frames, max_distance_px=max_distance_px, max_lost_frames=max_lost_frames)
    else:
        raise ValueError(f"Unsupported tracker for Level 2 multi-clip: {tracker_method}")
    tracks_path = output_dir / "tracks_level2.csv"
    write_tracks_csv(tracks, tracks_path)

    rows = read_tracks_csv(tracks_path)
    metrics = compute_level2_metrics(
        rows,
        fps=clip.fps,
        possession_distance_px=float(event_config["possession_distance_px"]),
        tracks_file=str(tracks_path),
        field_width=clip.width,
        field_height=clip.height,
        source_experiment=str(output_dir),
    )
    write_level2_metrics_csv(metrics, output_dir / "level2_metrics.csv")
    write_level2_metrics_json(metrics, output_dir / "level2_metrics.json")

    events = detect_level2_events(
        tracks_path,
        fps=clip.fps,
        field_width=clip.width,
        field_height=clip.height,
        config=event_config,
        source_experiment=str(output_dir),
    )
    write_level2_events_json(events, output_dir / "level2_events.json")
    write_level2_event_metrics(events, output_dir / "level2_event_metrics.csv")
    write_event_count_csv(output_dir / "level2_event_counts.csv", events)

    detection_counts = count_classes_from_detections(clip.detections)
    write_clip_summary(output_dir / "summary.md", clip, tracks_path, metrics.to_json_dict(), events, detection_counts, tracker_used=tracker_used)
    return metrics.to_json_dict(), events, detection_counts, tracks_path


def process_baseline_clip(clip: ClipSpec) -> tuple[dict[str, Any], list[dict[str, Any]], Counter[str] | None, Path | None]:
    metrics = load_json(clip.metrics) if clip.metrics else {}
    events = load_json(clip.events) if clip.events else []
    tracks_path = Path(clip.tracks) if clip.tracks else None
    return metrics, events, None, tracks_path


def process_diagnostic_clip(clip: ClipSpec, output_dir: Path) -> tuple[None, list[dict[str, Any]], Counter[str], None]:
    if clip.detections is None:
        raise ValueError(f"Diagnostic clip needs detections: {clip.clip_id}")
    detection_counts = count_classes_from_detections(clip.detections)
    events: list[dict[str, Any]] = []
    write_clip_summary(output_dir / "summary.md", clip, None, None, events, detection_counts)
    return None, events, detection_counts, None


def write_comparison(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(rows[0].keys()) if rows else ["clip_id"]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def write_summary(path: Path, comparison_rows: list[dict[str, Any]]) -> None:
    by_clip = {row["clip_id"]: row for row in comparison_rows}
    lines = [
        "# test_015_level2_multiclip",
        "",
        "## Objetivo",
        "",
        "Ejecutar tracking/eventos Nivel 2 en clips reales adicionales y compararlos contra `video_836`.",
        "",
        "## Clips",
        "",
    ]
    for row in comparison_rows:
        lines.append(
            f"- `{row['clip_id']}` (`{row['role']}`): frames `{row['observed_frames']}`, tracks `{row['track_count']}`, "
            f"posesion `{row['possession_assigned_seconds']}s`, eventos recovery/interception/highlight "
            f"`{row['ball_recovery']}/{row['interception']}/{row['highlight_play']}`."
        )
    lines.extend(
        [
            "",
            "## Comparacion Contra video_836",
            "",
            "- `video_836` conserva la referencia mas densa: tracks ByteTrack en frames `120-180` y eventos ya validados.",
            "- `video_595` y `video_667` deben usar evidencia densa en el cierre Nivel 2; si el insumo sigue siendo sparse, el resumen lo conserva como limitacion.",
            "- `video_595` y `video_667` se comparan con el mismo contrato de metricas/eventos que `video_836`.",
            "- `video_480` queda como diagnostico de balon: robot/cancha estables, balon no detectado en la muestra, sin eventos deportivos.",
            "",
            "## Diferencias Por Camara, Iluminacion Y Oclusion",
            "",
            "- `video_595`: perspectiva vertical similar pero resolucion `1344x1792`; duplicados puntuales sugieren ambiguedad visual/occlusion local.",
            "- `video_667`: resolucion `1360x1808`; robots mas numerosos o mas visibles elevan candidatos por frame y riesgo de cambios de ID.",
            "- `video_836`: ventana densa y ByteTrack reducen fragmentacion, por lo que es la mejor referencia para comparar.",
            "- `video_480`: probable ausencia, oclusion o bajo recall del prompt de balon; se reserva para diagnostico antes de eventos.",
            "",
            "## Politica De Archivos",
            "",
            "- No se generaron ni versionaron videos completos.",
            "- Solo se versionan CSV/JSON/Markdown ligeros.",
        ]
    )
    if "video_836" in by_clip:
        lines.extend(["", "## Baseline", "", f"- Tracks base: `{by_clip['video_836']['tracks_file']}`."])
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Level 2 multi-clip tracking/events comparison.")
    parser.add_argument("--config", default="configs/default.yaml")
    parser.add_argument("--experiment", default="experiments/test_015_level2_multiclip")
    parser.add_argument("--tracker", choices=["bytetrack", "simple"], default=None)
    parser.add_argument("--allow-simple-fallback", action="store_true")
    parser.add_argument("--max-distance-px", type=float, default=260)
    parser.add_argument("--max-lost-frames", type=int, default=40)
    parser.add_argument("--bytetrack-activation-threshold", type=float, default=0.25)
    parser.add_argument("--bytetrack-lost-buffer", type=int, default=30)
    parser.add_argument("--bytetrack-matching-threshold", type=float, default=0.8)
    args = parser.parse_args()

    config = load_config(args.config)
    level2_multiclip = config.get("level2_multiclip", {})
    event_config = dict(config.get("level2_events", {}))
    event_config.setdefault("possession_distance_px", config.get("events", {}).get("possession_distance_px", 190))
    tracker_method = args.tracker or str(level2_multiclip.get("tracker", config.get("tracking", {}).get("method", "bytetrack")))
    allow_simple_fallback = args.allow_simple_fallback or bool(level2_multiclip.get("allow_simple_fallback", False))
    clips = clip_specs_from_config(config) or DEFAULT_CLIPS
    experiment = Path(args.experiment)
    experiment.mkdir(parents=True, exist_ok=True)
    write_config_snapshot(config, experiment / "config.yaml")

    comparison_rows: list[dict[str, Any]] = []
    for clip in clips:
        clip_dir = experiment / clip.clip_id
        clip_dir.mkdir(parents=True, exist_ok=True)
        if clip.role == "candidate":
            metrics, events, detections, tracks_path = process_candidate_clip(
                clip,
                clip_dir,
                event_config,
                tracker_method=tracker_method,
                allow_simple_fallback=allow_simple_fallback,
                max_distance_px=args.max_distance_px,
                max_lost_frames=args.max_lost_frames,
                bytetrack_activation_threshold=args.bytetrack_activation_threshold,
                bytetrack_lost_buffer=args.bytetrack_lost_buffer,
                bytetrack_matching_threshold=args.bytetrack_matching_threshold,
            )
        elif clip.role == "baseline":
            metrics, events, detections, tracks_path = process_baseline_clip(clip)
            write_clip_summary(clip_dir / "summary.md", clip, tracks_path, metrics, events, detections)
        else:
            metrics, events, detections, tracks_path = process_diagnostic_clip(clip, clip_dir)
        comparison_rows.append(clip_row(clip, metrics, events, detections, tracks_path))

    write_comparison(experiment / "multiclip_comparison.csv", comparison_rows)
    write_summary(experiment / "summary.md", comparison_rows)
    print(f"Wrote Level 2 multi-clip experiment to {experiment}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
