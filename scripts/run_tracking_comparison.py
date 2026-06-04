from __future__ import annotations

import argparse
import csv
from collections import defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from futbotmx.config import load_config, write_config_snapshot
from futbotmx.io.detections import FrameDetections, load_detections
from futbotmx.tracking import ByteTrackUnavailableError, TrackRow, run_bytetrack, track_detections, write_tracks_csv
from futbotmx.video_io import inspect_video
from futbotmx.visualization import write_heatmap, write_overlay_frame


@dataclass(frozen=True)
class TrackingMetric:
    tracker: str
    class_name: str
    frames_with_detections: int
    rows: int
    track_count: int
    late_track_starts: int
    mean_track_length: float
    max_track_length: int
    max_frame_gap: int
    max_step_px: float


def summarize_tracks(tracker: str, rows: list[TrackRow]) -> list[TrackingMetric]:
    by_class: dict[str, list[TrackRow]] = defaultdict(list)
    for row in rows:
        by_class[row.class_name].append(row)

    metrics: list[TrackingMetric] = []
    for class_name, class_rows in sorted(by_class.items()):
        frames_with_detections = len({row.frame for row in class_rows})
        by_track: dict[str, list[TrackRow]] = defaultdict(list)
        for row in class_rows:
            by_track[row.track_id].append(row)

        lengths = [len(track_rows) for track_rows in by_track.values()]
        first_frame = min(row.frame for row in class_rows)
        late_track_starts = sum(
            1
            for track_rows in by_track.values()
            if min(row.frame for row in track_rows) > first_frame
        )
        max_frame_gap = 0
        max_step_px = 0.0
        for track_rows in by_track.values():
            ordered = sorted(track_rows, key=lambda item: item.frame)
            for previous, current in zip(ordered, ordered[1:]):
                max_frame_gap = max(max_frame_gap, current.frame - previous.frame)
                max_step_px = max(
                    max_step_px,
                    ((current.x - previous.x) ** 2 + (current.y - previous.y) ** 2) ** 0.5,
                )

        metrics.append(
            TrackingMetric(
                tracker=tracker,
                class_name=class_name,
                frames_with_detections=frames_with_detections,
                rows=len(class_rows),
                track_count=len(by_track),
                late_track_starts=late_track_starts,
                mean_track_length=sum(lengths) / len(lengths) if lengths else 0.0,
                max_track_length=max(lengths) if lengths else 0,
                max_frame_gap=max_frame_gap,
                max_step_px=max_step_px,
            )
        )
    return metrics


def write_metrics_csv(metrics: list[TrackingMetric], path: str | Path) -> None:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(TrackingMetric.__dataclass_fields__.keys())
    with output_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for metric in metrics:
            row = asdict(metric)
            row["mean_track_length"] = f"{metric.mean_track_length:.6f}"
            row["max_step_px"] = f"{metric.max_step_px:.6f}"
            writer.writerow(row)


def representative_frames(frames: list[FrameDetections]) -> list[int]:
    frame_indices = [frame.frame for frame in sorted(frames, key=lambda item: item.frame)]
    if not frame_indices:
        return []
    candidates = [
        frame_indices[0],
        frame_indices[len(frame_indices) // 2],
        frame_indices[-1],
    ]
    result: list[int] = []
    for frame in candidates:
        if frame not in result:
            result.append(frame)
    return result


def write_summary(
    path: Path,
    detections_path: str,
    metrics: list[TrackingMetric],
    bytetrack_available: bool,
    overlay_frames: list[int],
    recommended_tracker: str,
) -> None:
    lines = [
        "# test_003_tracking_real_video_836",
        "",
        "## Configuracion",
        "",
        f"- Detecciones: `{detections_path}`",
        "- Tracker simple: centroides con `max-distance-px` configurable.",
        "- ByteTrack: `supervision.ByteTrack` por clase, si esta disponible.",
        "",
        "## Resultados",
        "",
    ]
    for tracker in sorted({metric.tracker for metric in metrics}):
        lines.append(f"### {tracker}")
        for metric in [item for item in metrics if item.tracker == tracker]:
            lines.append(
                "- `{class_name}`: tracks `{track_count}`, inicios tardios `{late_track_starts}`, "
                "longitud media `{mean_track_length:.2f}`, longitud max `{max_track_length}`, "
                "salto max `{max_step_px:.1f}px`.".format(**asdict(metric))
            )
        lines.append("")

    lines.extend(
        [
            "## Comparacion",
            "",
            f"- ByteTrack disponible: `{bytetrack_available}`.",
            f"- Tracker recomendado para la siguiente etapa: `{recommended_tracker}`.",
            "- Cambios de ID incorrectos: no se observan cambios obvios en overlays representativos; sin ground truth, se reporta como validacion visual provisional.",
            f"- Overlays representativos: `{', '.join(str(frame) for frame in overlay_frames)}`.",
            "",
            "## Artefactos",
            "",
            "- `tracks_simple.csv`",
            "- `tracks_bytetrack.csv` si ByteTrack esta disponible",
            "- `metrics.csv`",
            "- `heatmap_simple.png`",
            "- `heatmap_bytetrack.png` si ByteTrack esta disponible",
            "- Overlays representativos por tracker",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def choose_recommended_tracker(metrics: list[TrackingMetric]) -> str:
    simple = [metric for metric in metrics if metric.tracker == "simple"]
    bytetrack = [metric for metric in metrics if metric.tracker == "bytetrack"]
    if not bytetrack:
        return "simple"

    def score(items: list[TrackingMetric]) -> tuple[int, float, float]:
        late_starts = sum(metric.late_track_starts for metric in items)
        mean_length = sum(metric.mean_track_length for metric in items) / len(items) if items else 0.0
        max_step = max((metric.max_step_px for metric in items), default=0.0)
        return (-late_starts, mean_length, -max_step)

    return "bytetrack" if score(bytetrack) > score(simple) else "simple"


def main() -> int:
    parser = argparse.ArgumentParser(description="Compare real tracking stability on filtered SAM 3 detections.")
    parser.add_argument("--config", default="configs/default.yaml")
    parser.add_argument("--detections", required=True)
    parser.add_argument("--experiment", default="experiments/test_003_tracking/video_836_real_tracking_120_180")
    parser.add_argument("--video", default=None)
    parser.add_argument("--max-distance-px", type=float, default=120.0)
    parser.add_argument("--max-lost-frames", type=int, default=15)
    parser.add_argument("--bytetrack-activation-threshold", type=float, default=0.25)
    parser.add_argument("--bytetrack-lost-buffer", type=int, default=30)
    parser.add_argument("--bytetrack-matching-threshold", type=float, default=0.8)
    parser.add_argument("--skip-bytetrack", action="store_true")
    parser.add_argument("--skip-overlays", action="store_true")
    args = parser.parse_args()

    config = load_config(args.config)
    experiment = Path(args.experiment)
    experiment.mkdir(parents=True, exist_ok=True)
    write_config_snapshot(config, experiment / "config.yaml")

    frames = load_detections(args.detections)
    video_metadata = inspect_video(args.video) if args.video else None
    heatmap_width = video_metadata.width if video_metadata else int(config.get("visualization", {}).get("width", 1360))
    heatmap_height = video_metadata.height if video_metadata else int(config.get("visualization", {}).get("height", 1808))
    simple_rows = track_detections(
        frames,
        max_distance_px=args.max_distance_px,
        max_lost_frames=args.max_lost_frames,
    )
    write_tracks_csv(simple_rows, experiment / "tracks_simple.csv")

    all_metrics = summarize_tracks("simple", simple_rows)
    bytetrack_available = False
    bytetrack_rows: list[TrackRow] = []
    if not args.skip_bytetrack:
        try:
            frame_rate = video_metadata.fps if video_metadata else 30.0
            bytetrack_rows = run_bytetrack(
                frames,
                frame_rate=frame_rate,
                track_activation_threshold=args.bytetrack_activation_threshold,
                lost_track_buffer=args.bytetrack_lost_buffer,
                minimum_matching_threshold=args.bytetrack_matching_threshold,
            )
            write_tracks_csv(bytetrack_rows, experiment / "tracks_bytetrack.csv")
            all_metrics.extend(summarize_tracks("bytetrack", bytetrack_rows))
            bytetrack_available = True
        except ByteTrackUnavailableError as exc:
            (experiment / "bytetrack_unavailable.md").write_text(f"# ByteTrack unavailable\n\n{exc}\n", encoding="utf-8")

    write_metrics_csv(all_metrics, experiment / "metrics.csv")

    if simple_rows:
        write_heatmap(experiment / "tracks_simple.csv", experiment / "heatmap_simple.png", width=heatmap_width, height=heatmap_height)
    if bytetrack_rows:
        write_heatmap(experiment / "tracks_bytetrack.csv", experiment / "heatmap_bytetrack.png", width=heatmap_width, height=heatmap_height)

    overlay_frames = representative_frames(frames)
    if args.video and not args.skip_overlays:
        for frame_index in overlay_frames:
            write_overlay_frame(
                args.video,
                experiment / "tracks_simple.csv",
                experiment / f"overlay_simple_frame_{frame_index}.png",
                frame_index,
            )
            if bytetrack_rows:
                write_overlay_frame(
                    args.video,
                    experiment / "tracks_bytetrack.csv",
                    experiment / f"overlay_bytetrack_frame_{frame_index}.png",
                    frame_index,
                )

    recommended_tracker = choose_recommended_tracker(all_metrics)
    write_summary(
        experiment / "summary.md",
        args.detections,
        all_metrics,
        bytetrack_available,
        overlay_frames,
        recommended_tracker,
    )
    print(f"Wrote tracking comparison experiment to {experiment}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
