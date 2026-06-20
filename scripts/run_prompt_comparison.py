from __future__ import annotations

import argparse
import csv
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
import sys
from typing import Iterable

import cv2

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from futbotmx.config import load_config, write_config_snapshot
from futbotmx.io.detections import (
    Detection,
    FrameDetections,
    filter_detections_by_roi,
    save_detections,
)
from futbotmx.segmentation import SAM3Segmenter, SAM3UnavailableError
from futbotmx.video_io import extract_frame


PROMPT_GROUPS = {
    "ball": ["ball", "orange ball", "small orange ball", "soccer ball"],
    "robot": ["robot", "soccer robot", "wheeled robot", "small robot"],
    "field": ["field", "playing field", "green soccer field"],
}

COLORS = {
    "ball": (0, 220, 255),
    "robot": (0, 180, 80),
    "field": (255, 180, 0),
}


@dataclass(frozen=True)
class PromptSummary:
    group: str
    prompt: str
    frames_evaluated: int
    detected_frames_raw: int
    detected_frames_filtered: int
    total_raw: int
    total_filtered: int
    mean_confidence_raw: float
    mean_confidence_filtered: float
    missing_frames_filtered: tuple[int, ...]


def slugify_prompt(prompt: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", prompt.lower()).strip("_")
    if not slug:
        raise ValueError("prompt must contain at least one alphanumeric character")
    return slug


def frame_counts(frames: Iterable[FrameDetections]) -> dict[int, int]:
    return {frame.frame: len(frame.detections) for frame in frames}


def summarize_prompt(
    group: str,
    prompt: str,
    raw_frames: list[FrameDetections],
    filtered_frames: list[FrameDetections],
) -> PromptSummary:
    raw_counts = frame_counts(raw_frames)
    filtered_counts = frame_counts(filtered_frames)
    raw_confidences = [
        detection.confidence
        for frame in raw_frames
        for detection in frame.detections
    ]
    filtered_confidences = [
        detection.confidence
        for frame in filtered_frames
        for detection in frame.detections
    ]
    missing_frames = tuple(
        frame.frame for frame in raw_frames if filtered_counts.get(frame.frame, 0) == 0
    )
    return PromptSummary(
        group=group,
        prompt=prompt,
        frames_evaluated=len(raw_frames),
        detected_frames_raw=sum(1 for count in raw_counts.values() if count > 0),
        detected_frames_filtered=sum(1 for count in filtered_counts.values() if count > 0),
        total_raw=sum(raw_counts.values()),
        total_filtered=sum(filtered_counts.values()),
        mean_confidence_raw=_mean(raw_confidences),
        mean_confidence_filtered=_mean(filtered_confidences),
        missing_frames_filtered=missing_frames,
    )


def choose_prompt(group: str, summaries: list[PromptSummary]) -> PromptSummary:
    if not summaries:
        raise ValueError("summaries must not be empty")
    if group == "ball":
        return max(
            summaries,
            key=lambda item: (
                item.detected_frames_filtered,
                -abs(item.total_filtered - item.frames_evaluated),
                item.mean_confidence_filtered,
            ),
        )
    if group == "robot":
        return max(
            summaries,
            key=lambda item: (
                item.detected_frames_filtered,
                item.total_filtered,
                item.mean_confidence_filtered,
            ),
        )
    return max(
        summaries,
        key=lambda item: (
            item.detected_frames_raw,
            item.total_raw,
            item.mean_confidence_raw,
        ),
    )


def write_prompt_metrics(
    raw_frames: list[FrameDetections],
    filtered_frames: list[FrameDetections],
    path: str | Path,
) -> None:
    filtered_by_frame = {frame.frame: frame for frame in filtered_frames}
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "frame",
                "raw_count",
                "filtered_count",
                "raw_mean_confidence",
                "filtered_mean_confidence",
            ],
        )
        writer.writeheader()
        for raw_frame in raw_frames:
            filtered_frame = filtered_by_frame.get(raw_frame.frame, FrameDetections(raw_frame.frame, ()))
            writer.writerow(
                {
                    "frame": raw_frame.frame,
                    "raw_count": len(raw_frame.detections),
                    "filtered_count": len(filtered_frame.detections),
                    "raw_mean_confidence": f"{_mean_confidence(raw_frame.detections):.6f}",
                    "filtered_mean_confidence": f"{_mean_confidence(filtered_frame.detections):.6f}",
                }
            )


def write_comparison_csv(summaries: list[PromptSummary], path: str | Path) -> None:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(PromptSummary.__dataclass_fields__.keys()))
        writer.writeheader()
        for summary in summaries:
            writer.writerow(
                {
                    "group": summary.group,
                    "prompt": summary.prompt,
                    "frames_evaluated": summary.frames_evaluated,
                    "detected_frames_raw": summary.detected_frames_raw,
                    "detected_frames_filtered": summary.detected_frames_filtered,
                    "total_raw": summary.total_raw,
                    "total_filtered": summary.total_filtered,
                    "mean_confidence_raw": f"{summary.mean_confidence_raw:.6f}",
                    "mean_confidence_filtered": f"{summary.mean_confidence_filtered:.6f}",
                    "missing_frames_filtered": " ".join(str(frame) for frame in summary.missing_frames_filtered),
                }
            )


def write_detection_overlay_frame(
    video_path: str | Path,
    frames: list[FrameDetections],
    output_path: str | Path,
    frame_index: int,
    group: str,
    label: str,
) -> None:
    frame = extract_frame(video_path, frame_index)
    detections = next((item.detections for item in frames if item.frame == frame_index), ())
    color = COLORS.get(group, (255, 255, 255))
    for detection in detections:
        _draw_detection(frame, detection, color, label)
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(output), frame)


def write_prompt_summary(path: Path, summary: PromptSummary, overlay_frames: list[int]) -> None:
    path.write_text(
        "# Prompt comparison: {prompt}\n\n"
        "## Resultados metricos\n\n"
        "- Grupo: `{group}`.\n"
        "- Frames evaluados: `{frames}`.\n"
        "- Frames con deteccion raw: `{raw_detected}/{frames}`.\n"
        "- Frames con deteccion filtrada por ROI: `{filtered_detected}/{frames}`.\n"
        "- Total raw: `{total_raw}`.\n"
        "- Total filtrado por ROI: `{total_filtered}`.\n"
        "- Confianza media raw: `{mean_raw:.4f}`.\n"
        "- Confianza media filtrada: `{mean_filtered:.4f}`.\n"
        "- Frames sin deteccion filtrada: `{missing}`.\n\n"
        "## Revision visual\n\n"
        "- Precision visual: `requiere revision humana`.\n"
        "- Overlays revisables: `{overlays}`.\n".format(
            prompt=summary.prompt,
            group=summary.group,
            frames=summary.frames_evaluated,
            raw_detected=summary.detected_frames_raw,
            filtered_detected=summary.detected_frames_filtered,
            total_raw=summary.total_raw,
            total_filtered=summary.total_filtered,
            mean_raw=summary.mean_confidence_raw,
            mean_filtered=summary.mean_confidence_filtered,
            missing=", ".join(str(frame) for frame in summary.missing_frames_filtered) or "ninguno",
            overlays=", ".join(str(frame) for frame in overlay_frames) or "ninguno",
        ),
        encoding="utf-8",
    )


def write_experiment_summary(
    path: Path,
    video_path: str,
    frames: list[int],
    summaries: list[PromptSummary],
    choices: dict[str, PromptSummary],
) -> None:
    lines = [
        "# test_002_sam3_prompt_comparison",
        "",
        "## Configuracion",
        "",
        f"- Video: `{video_path}`",
        "- Frames evaluados: `" + ", ".join(str(frame) for frame in frames) + "`.",
        "- Prompts comparados por grupo: `ball`, `robot`, `field`.",
        "",
        "## Resultados metricos",
        "",
    ]
    for group in PROMPT_GROUPS:
        group_summaries = [summary for summary in summaries if summary.group == group]
        lines.append(f"### {group}")
        for summary in group_summaries:
            lines.append(
                "- `{prompt}`: filtrado `{filtered}/{frames}`, total `{total}`, confianza `{confidence:.4f}`, sin deteccion `{missing}`.".format(
                    prompt=summary.prompt,
                    filtered=summary.detected_frames_filtered,
                    frames=summary.frames_evaluated,
                    total=summary.total_filtered,
                    confidence=summary.mean_confidence_filtered,
                    missing=", ".join(str(frame) for frame in summary.missing_frames_filtered) or "ninguno",
                )
            )
        if group in choices:
            lines.append(f"- Seleccion metrica preliminar: `{choices[group].prompt}`.")
        lines.append("")

    lines.extend(
        [
            "## Decision",
            "",
            "- Prompts base recomendados por metrica automatica: `"
            + ", ".join(f"{group}={choice.prompt}" for group, choice in choices.items())
            + "`.",
            "- La seleccion final queda sujeta a revision visual de overlays antes de cambiar `configs/default.yaml`.",
            "",
            "## Artefactos",
            "",
            "- `comparison.csv`",
            "- Subcarpetas por grupo y prompt con `detections.json`, `detections_filtered_roi.json`, `metrics.csv` y `summary.md`.",
            "- Overlays representativos para prompts seleccionados, salvo que se use `--overlay-all-prompts`.",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _draw_detection(image, detection: Detection, color: tuple[int, int, int], label: str) -> None:
    x1, y1, x2, y2 = (int(value) for value in detection.bbox)
    cx, cy = (int(value) for value in detection.centroid)
    cv2.rectangle(image, (x1, y1), (x2, y2), color, 2)
    cv2.circle(image, (cx, cy), 4, color, -1)
    text = f"{label} {detection.confidence:.2f}"
    cv2.putText(image, text, (x1, max(15, y1 - 6)), cv2.FONT_HERSHEY_SIMPLEX, 0.45, color, 1)


def _mean_confidence(detections: Iterable[Detection]) -> float:
    return _mean([detection.confidence for detection in detections])


def _mean(values: Iterable[float]) -> float:
    values = list(values)
    return sum(values) / len(values) if values else 0.0


def _selected_groups(group_args: list[str] | None) -> dict[str, list[str]]:
    if not group_args or "all" in group_args:
        return PROMPT_GROUPS
    return {group: PROMPT_GROUPS[group] for group in group_args}


def _detection_frames(frames: list[FrameDetections]) -> list[int]:
    return [frame.frame for frame in frames if frame.detections]


def _overlay_frames(requested_frames: list[int], filtered_frames: list[FrameDetections]) -> list[int]:
    detected = _detection_frames(filtered_frames)
    if detected:
        candidates = [detected[0], detected[len(detected) // 2], detected[-1]]
    else:
        candidates = [
            requested_frames[0],
            requested_frames[len(requested_frames) // 2],
            requested_frames[-1],
        ]
    result: list[int] = []
    for frame in candidates:
        if frame not in result:
            result.append(frame)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Compare SAM 3 prompts for CopaFutMX videos.")
    parser.add_argument("--config", default="configs/default.yaml")
    parser.add_argument("--video", required=True)
    parser.add_argument("--checkpoint", default=None)
    parser.add_argument("--experiment", default="experiments/test_002_sam3_segmentation/video_836_prompt_comparison_120_180")
    parser.add_argument("--frame", type=int, action="append", dest="frames", default=None)
    parser.add_argument("--group", choices=["all", *PROMPT_GROUPS.keys()], action="append", default=None)
    parser.add_argument("--roi", nargs=4, type=float, default=(0, 620, 1360, 1808))
    parser.add_argument("--skip-overlays", action="store_true")
    parser.add_argument(
        "--overlay-all-prompts",
        action="store_true",
        help="Keep overlays for every prompt. By default, only selected prompt overlays are kept.",
    )
    args = parser.parse_args()

    config = load_config(args.config)
    experiment = Path(args.experiment)
    experiment.mkdir(parents=True, exist_ok=True)
    write_config_snapshot(config, experiment / "config.yaml")

    frames = args.frames or [120, 135, 143, 147, 150, 180]
    roi = tuple(float(value) for value in args.roi)
    selected_groups = _selected_groups(args.group)

    try:
        segmenter = SAM3Segmenter(
            checkpoint_path=args.checkpoint,
            confidence_threshold=float(config["segmentation"].get("confidence_threshold", 0.5)),
        )
        summaries: list[PromptSummary] = []
        filtered_by_prompt: dict[tuple[str, str], list[FrameDetections]] = {}
        for group, prompts in selected_groups.items():
            for prompt in prompts:
                prompt_slug = slugify_prompt(prompt)
                prompt_dir = experiment / group / prompt_slug
                prompt_dir.mkdir(parents=True, exist_ok=True)
                raw_frames = segmenter.segment_video(args.video, frames, [prompt])
                filtered_frames = filter_detections_by_roi(raw_frames, roi)

                save_detections(raw_frames, prompt_dir / "detections.json")
                save_detections(filtered_frames, prompt_dir / "detections_filtered_roi.json")
                write_prompt_metrics(raw_frames, filtered_frames, prompt_dir / "metrics.csv")

                filtered_by_prompt[(group, prompt)] = filtered_frames
                overlay_frames = _overlay_frames(frames, filtered_frames) if args.overlay_all_prompts else []
                if not args.skip_overlays and args.overlay_all_prompts:
                    for frame_index in overlay_frames:
                        write_detection_overlay_frame(
                            args.video,
                            filtered_frames,
                            prompt_dir / f"overlay_frame_{frame_index}_filtered_roi.png",
                            frame_index,
                            group,
                            prompt,
                        )

                summary = summarize_prompt(group, prompt, raw_frames, filtered_frames)
                summaries.append(summary)
                write_prompt_summary(
                    prompt_dir / "summary.md",
                    summary,
                    overlay_frames if not args.skip_overlays else [],
                )

        write_comparison_csv(summaries, experiment / "comparison.csv")
        choices = {
            group: choose_prompt(group, [summary for summary in summaries if summary.group == group])
            for group in selected_groups
        }
        if not args.skip_overlays and not args.overlay_all_prompts:
            for group, choice in choices.items():
                prompt_slug = slugify_prompt(choice.prompt)
                prompt_dir = experiment / group / prompt_slug
                filtered_frames = filtered_by_prompt[(group, choice.prompt)]
                overlay_frames = _overlay_frames(frames, filtered_frames)
                for frame_index in overlay_frames:
                    write_detection_overlay_frame(
                        args.video,
                        filtered_frames,
                        prompt_dir / f"overlay_frame_{frame_index}_filtered_roi.png",
                        frame_index,
                        group,
                        choice.prompt,
                    )
                write_prompt_summary(prompt_dir / "summary.md", choice, overlay_frames)
        write_experiment_summary(experiment / "summary.md", args.video, frames, summaries, choices)
    except SAM3UnavailableError as exc:
        (experiment / "errors.md").write_text(
            "# SAM 3 prompt comparison pending\n\n"
            f"{exc}\n\n"
            "Run this script on the MSI laptop after installing SAM 3 officially.\n",
            encoding="utf-8",
        )
        print(str(exc))
        return 2

    print(f"Wrote prompt comparison experiment to {experiment}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
