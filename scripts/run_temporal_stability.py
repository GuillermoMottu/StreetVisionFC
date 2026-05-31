from __future__ import annotations

import argparse
import csv
from collections import Counter
from pathlib import Path
import sys
from typing import Iterable

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from futbotmx.config import load_config, write_config_snapshot
from futbotmx.io.detections import (
    FrameDetections,
    filter_detections_by_roi,
    save_detections,
)
from futbotmx.segmentation import SAM3Segmenter, SAM3UnavailableError
from futbotmx.tracking import track_detections, write_tracks_csv
from futbotmx.video_io import inspect_video
from futbotmx.visualization import write_heatmap, write_overlay_frame


def select_frames(start_frame: int, end_frame: int, stride: int) -> list[int]:
    if stride <= 0:
        raise ValueError("stride must be greater than 0")
    if end_frame < start_frame:
        raise ValueError("end_frame must be greater than or equal to start_frame")
    return list(range(start_frame, end_frame + 1, stride))


def representative_frames(frames: list[int]) -> list[int]:
    if not frames:
        return []
    candidates = [frames[0], frames[len(frames) // 2], frames[-1]]
    result: list[int] = []
    for frame in candidates:
        if frame not in result:
            result.append(frame)
    return result


def count_detections_by_frame(
    raw_frames: list[FrameDetections],
    filtered_frames: list[FrameDetections],
    class_names: Iterable[str],
) -> list[dict[str, int]]:
    filtered_by_frame = {frame.frame: frame for frame in filtered_frames}
    rows: list[dict[str, int]] = []
    for raw_frame in raw_frames:
        filtered_frame = filtered_by_frame.get(raw_frame.frame, FrameDetections(raw_frame.frame, ()))
        raw_counts = Counter(detection.class_name for detection in raw_frame.detections)
        filtered_counts = Counter(detection.class_name for detection in filtered_frame.detections)
        row = {
            "frame": raw_frame.frame,
            "raw_total": sum(raw_counts.values()),
            "filtered_total": sum(filtered_counts.values()),
        }
        for class_name in class_names:
            row[f"raw_{class_name}"] = raw_counts[class_name]
            row[f"filtered_{class_name}"] = filtered_counts[class_name]
        rows.append(row)
    return rows


def write_metrics_csv(rows: list[dict[str, int]], path: str | Path) -> None:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(rows[0].keys()) if rows else ["frame", "raw_total", "filtered_total"]
    with output_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _format_counts(rows: list[dict[str, int]], class_name: str) -> tuple[int, int, list[int]]:
    column = f"filtered_{class_name}"
    detected = sum(1 for row in rows if row.get(column, 0) > 0)
    total = len(rows)
    missing = [row["frame"] for row in rows if row.get(column, 0) == 0]
    return detected, total, missing


def _write_stride_summary(
    path: Path,
    stride: int,
    frames: list[int],
    metrics_rows: list[dict[str, int]],
    prompts: list[str],
    roi: tuple[float, float, float, float],
    overlay_frames: list[int],
) -> None:
    ball_detected, frame_count, ball_missing = _format_counts(metrics_rows, "ball")
    robot_detected, _, robot_missing = _format_counts(metrics_rows, "robot")
    removed = sum(row["raw_total"] - row["filtered_total"] for row in metrics_rows)
    by_frame_lines = "\n".join(
        "- Frame `{frame}`: ball `{ball}`, robot `{robot}`, total `{total}`".format(
            frame=row["frame"],
            ball=row.get("filtered_ball", 0),
            robot=row.get("filtered_robot", 0),
            total=row["filtered_total"],
        )
        for row in metrics_rows
    )

    path.write_text(
        "# Temporal stability stride {stride}\n\n"
        "## Configuracion\n\n"
        "- Frames: `{first}` a `{last}` con stride `{stride}` (`{frame_count}` frames).\n"
        "- Prompts: `{prompts}`.\n"
        "- ROI: `{roi}`.\n\n"
        "## Resultados\n\n"
        "- Balon detectado: `{ball_detected}/{frame_count}` frames filtrados.\n"
        "- Robots detectados: `{robot_detected}/{frame_count}` frames filtrados.\n"
        "- Detecciones removidas por ROI: `{removed}`.\n"
        "- Frames sin balon: `{ball_missing}`.\n"
        "- Frames sin robots: `{robot_missing}`.\n"
        "- Overlays representativos: `{overlay_frames}`.\n\n"
        "## Resumen por frame\n\n"
        "{by_frame_lines}\n\n"
        "## Artefactos\n\n"
        "- `detections.json`\n"
        "- `detections_filtered_roi.json`\n"
        "- `tracks_filtered_roi.csv`\n"
        "- `metrics.csv`\n"
        "- `heatmap_filtered_roi.png`\n".format(
            stride=stride,
            first=frames[0] if frames else "",
            last=frames[-1] if frames else "",
            frame_count=frame_count,
            prompts=", ".join(prompts),
            roi=roi,
            ball_detected=ball_detected,
            robot_detected=robot_detected,
            removed=removed,
            ball_missing=", ".join(str(frame) for frame in ball_missing) or "ninguno",
            robot_missing=", ".join(str(frame) for frame in robot_missing) or "ninguno",
            overlay_frames=", ".join(str(frame) for frame in overlay_frames) or "ninguno",
            by_frame_lines=by_frame_lines,
        ),
        encoding="utf-8",
    )


def _write_experiment_summary(
    path: Path,
    video_path: str,
    start_frame: int,
    end_frame: int,
    stride_summaries: list[dict[str, object]],
) -> None:
    lines = [
        "# test_002_sam3_temporal_stability",
        "",
        "## Configuracion",
        "",
        f"- Video: `{video_path}`",
        f"- Ventana: `{start_frame}` a `{end_frame}`.",
        "- Strides comparados: `"
        + ", ".join(str(item["stride"]) for item in stride_summaries)
        + "`.",
        "",
        "## Resultados",
        "",
    ]
    for item in stride_summaries:
        lines.append(
            "- Stride `{stride}`: balon `{ball_detected}/{frame_count}`, robots "
            "`{robot_detected}/{frame_count}`, removidas por ROI `{removed}`, sin balon `{missing_ball}`.".format(
                **item
            )
        )
    lines.extend(
        [
            "",
            "## Artefactos",
            "",
            "- Subcarpetas `stride_1`, `stride_3` y `stride_5` con detecciones, tracking, metricas y overlays.",
            "- Cada `summary.md` incluye resumen por frame.",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Compare SAM 3 temporal stability across frame strides.")
    parser.add_argument("--config", default="configs/default.yaml")
    parser.add_argument("--video", required=True)
    parser.add_argument("--checkpoint", default=None)
    parser.add_argument("--experiment", default="experiments/test_002_sam3_segmentation/video_836_temporal_stability_120_180")
    parser.add_argument("--start-frame", type=int, default=120)
    parser.add_argument("--end-frame", type=int, default=180)
    parser.add_argument("--stride", type=int, action="append", dest="strides", default=None)
    parser.add_argument("--prompt", action="append", dest="prompts", default=None)
    parser.add_argument("--roi", nargs=4, type=float, default=(0, 620, 1360, 1808))
    parser.add_argument("--max-distance-px", type=float, default=120.0)
    parser.add_argument("--skip-overlays", action="store_true")
    args = parser.parse_args()

    config = load_config(args.config)
    experiment = Path(args.experiment)
    experiment.mkdir(parents=True, exist_ok=True)
    write_config_snapshot(config, experiment / "config.yaml")

    prompts = [prompt.replace("_", " ") for prompt in (args.prompts or ["ball", "robot"])]
    class_names = [prompt.replace(" ", "_") for prompt in prompts]
    strides = args.strides or [1, 3, 5]
    roi = tuple(float(value) for value in args.roi)
    video_metadata = inspect_video(args.video)

    try:
        segmenter = SAM3Segmenter(
            checkpoint_path=args.checkpoint,
            confidence_threshold=float(config["segmentation"].get("confidence_threshold", 0.5)),
        )
        stride_summaries: list[dict[str, object]] = []
        for stride in strides:
            frames = select_frames(args.start_frame, args.end_frame, stride)
            stride_dir = experiment / f"stride_{stride}"
            stride_dir.mkdir(parents=True, exist_ok=True)

            raw_frames = segmenter.segment_video(args.video, frames, prompts)
            filtered_frames = filter_detections_by_roi(raw_frames, roi)
            save_detections(raw_frames, stride_dir / "detections.json")
            save_detections(filtered_frames, stride_dir / "detections_filtered_roi.json")

            rows = track_detections(filtered_frames, max_distance_px=args.max_distance_px)
            tracks_path = stride_dir / "tracks_filtered_roi.csv"
            write_tracks_csv(rows, tracks_path)
            write_heatmap(tracks_path, stride_dir / "heatmap_filtered_roi.png", video_metadata.width, video_metadata.height)

            metrics_rows = count_detections_by_frame(raw_frames, filtered_frames, class_names)
            write_metrics_csv(metrics_rows, stride_dir / "metrics.csv")

            overlay_frames = representative_frames([frame.frame for frame in filtered_frames])
            if not args.skip_overlays:
                for frame_index in overlay_frames:
                    write_overlay_frame(
                        args.video,
                        tracks_path,
                        stride_dir / f"overlay_frame_{frame_index}_filtered_roi.png",
                        frame_index,
                    )

            _write_stride_summary(
                stride_dir / "summary.md",
                stride,
                frames,
                metrics_rows,
                prompts,
                roi,
                overlay_frames if not args.skip_overlays else [],
            )
            ball_detected, frame_count, ball_missing = _format_counts(metrics_rows, "ball")
            robot_detected, _, _ = _format_counts(metrics_rows, "robot")
            removed = sum(row["raw_total"] - row["filtered_total"] for row in metrics_rows)
            stride_summaries.append(
                {
                    "stride": stride,
                    "frame_count": frame_count,
                    "ball_detected": ball_detected,
                    "robot_detected": robot_detected,
                    "removed": removed,
                    "missing_ball": ", ".join(str(frame) for frame in ball_missing) or "ninguno",
                }
            )

        _write_experiment_summary(
            experiment / "summary.md",
            args.video,
            args.start_frame,
            args.end_frame,
            stride_summaries,
        )
    except SAM3UnavailableError as exc:
        (experiment / "errors.md").write_text(
            "# SAM 3 temporal stability pending\n\n"
            f"{exc}\n\n"
            "Run this script on the MSI laptop after installing SAM 3 officially.\n",
            encoding="utf-8",
        )
        print(str(exc))
        return 2

    print(f"Wrote temporal stability experiment to {experiment}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
