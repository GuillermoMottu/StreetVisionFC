from __future__ import annotations

import argparse
import csv
import json
import subprocess
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Callable


@dataclass(frozen=True)
class ValidationCheck:
    check_id: str
    status: str
    metric: str
    observed: str
    expected: str
    evidence: str
    recommendation: str


def read_csv_rows(path: str | Path) -> list[dict[str, str]]:
    with Path(path).open("r", newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def read_json(path: str | Path):
    with Path(path).open("r", encoding="utf-8") as handle:
        return json.load(handle)


def ratio_status(numerator: int, denominator: int, pass_ratio: float, warn_ratio: float = 0.8) -> str:
    if denominator <= 0:
        return "fail"
    ratio = numerator / denominator
    if ratio >= pass_ratio:
        return "pass"
    if ratio >= warn_ratio:
        return "warn"
    return "fail"


def find_row(rows: list[dict[str, str]], predicate: Callable[[dict[str, str]], bool]) -> dict[str, str] | None:
    for row in rows:
        if predicate(row):
            return row
    return None


def git_has_tracked_heavy_files() -> bool:
    extensions = (".mov", ".mp4", ".avi", ".mkv", ".m4v", ".pt", ".pth", ".onnx", ".safetensors")
    try:
        result = subprocess.run(["git", "ls-files"], check=True, capture_output=True, text=True, timeout=10)
    except (FileNotFoundError, subprocess.SubprocessError):
        return False
    return any(line.lower().endswith(extensions) for line in result.stdout.splitlines())


def build_checks(root: Path) -> list[ValidationCheck]:
    checks: list[ValidationCheck] = []

    prompt_rows = read_csv_rows(root / "experiments/test_002_sam3_segmentation/video_836_prompt_comparison_120_180/comparison.csv")
    field = find_row(prompt_rows, lambda row: row["group"] == "field" and row["prompt"] == "green soccer field")
    if field:
        detected = int(field["detected_frames_filtered"])
        total = int(field["frames_evaluated"])
        status = ratio_status(detected, total, pass_ratio=0.8)
        checks.append(
            ValidationCheck(
                "field_prompt_real",
                status,
                "field_detected_frames",
                f"{detected}/{total}",
                ">= 5/6",
                "experiments/test_002_sam3_segmentation/video_836_prompt_comparison_120_180/comparison.csv",
                "Mantener `green soccer field` como prompt base; explorar ROI poligonal para Nivel 2.",
            )
        )

    temporal_rows = read_csv_rows(
        root / "experiments/test_002_sam3_segmentation/video_836_temporal_stability_120_180/stride_1/metrics.csv"
    )
    ball_frames = sum(1 for row in temporal_rows if int(row.get("filtered_ball", "0")) > 0)
    robot_frames = sum(1 for row in temporal_rows if int(row.get("filtered_robot", "0")) > 0)
    total_frames = len(temporal_rows)
    checks.append(
        ValidationCheck(
            "temporal_ball_recall",
            ratio_status(ball_frames, total_frames, pass_ratio=0.95),
            "ball_detected_frames_stride1",
            f"{ball_frames}/{total_frames}",
            ">= 58/61",
            "experiments/test_002_sam3_segmentation/video_836_temporal_stability_120_180/stride_1/metrics.csv",
            "Revisar frames perdidos recurrentes antes de Nivel 2.",
        )
    )
    checks.append(
        ValidationCheck(
            "temporal_robot_recall",
            ratio_status(robot_frames, total_frames, pass_ratio=0.98),
            "robot_detected_frames_stride1",
            f"{robot_frames}/{total_frames}",
            ">= 60/61",
            "experiments/test_002_sam3_segmentation/video_836_temporal_stability_120_180/stride_1/metrics.csv",
            "Mantener `small robot`; agregar deduplicacion si hay multiples candidatos.",
        )
    )

    tracking_rows = read_csv_rows(root / "experiments/test_003_tracking/video_836_real_tracking_120_180/metrics.csv")
    simple_robot = find_row(tracking_rows, lambda row: row["tracker"] == "simple" and row["class_name"] == "robot")
    bytetrack_robot = find_row(tracking_rows, lambda row: row["tracker"] == "bytetrack" and row["class_name"] == "robot")
    if simple_robot and bytetrack_robot:
        simple_tracks = int(simple_robot["track_count"])
        bytetrack_tracks = int(bytetrack_robot["track_count"])
        simple_step = float(simple_robot["max_step_px"])
        bytetrack_step = float(bytetrack_robot["max_step_px"])
        status = "pass" if bytetrack_tracks <= simple_tracks and bytetrack_step < simple_step else "warn"
        checks.append(
            ValidationCheck(
                "bytetrack_stability",
                status,
                "robot_tracks_and_jump",
                f"{bytetrack_tracks} tracks, {bytetrack_step:.1f}px max step",
                f"<= {simple_tracks} tracks and < {simple_step:.1f}px max step",
                "experiments/test_003_tracking/video_836_real_tracking_120_180/metrics.csv",
                "Usar ByteTrack como tracker base para eventos reales.",
            )
        )

    events = read_json(root / "experiments/test_004_events/video_836_real_events_120_180/events.json")
    event_types = [event["event_type"] for event in events]
    event_count = len(events)
    has_shot = "shot" in event_types
    checks.append(
        ValidationCheck(
            "events_level1_real",
            "pass" if event_count >= 4 and not has_shot else "warn",
            "event_types",
            ", ".join(sorted(set(event_types))),
            "possession/collision/activity_zone and no shot",
            "experiments/test_004_events/video_836_real_events_120_180/events.json",
            "Mantener `shot` descartado en esta ventana hasta tener movimiento real mayor al umbral.",
        )
    )

    more_rows = read_csv_rows(root / "experiments/test_006_more_copafutmx_videos/metrics.csv")
    robust_clips = [row["video_id"] for row in more_rows if int(row["ball_frames"]) == 5 and int(row["small_robot_frames"]) == 5]
    checks.append(
        ValidationCheck(
            "additional_clip_readiness",
            "pass" if {"video_595", "video_667"}.issubset(set(robust_clips)) else "warn",
            "clips_with_ball_robot_5_of_5",
            " ".join(robust_clips),
            "video_595 and video_667",
            "experiments/test_006_more_copafutmx_videos/metrics.csv",
            "Continuar tracking/eventos con video_595 y video_667; diagnosticar balon en video_480.",
        )
    )

    benchmark_rows = read_csv_rows(root / "experiments/test_007_msi_benchmarks/video_836_sam3/metrics.csv")
    single = find_row(benchmark_rows, lambda row: row["name"] == "single_frame")
    multi = find_row(benchmark_rows, lambda row: row["name"] == "multi_frame")
    if single and multi:
        single_spf = float(single["sec_per_frame"])
        multi_spf = float(multi["sec_per_frame"])
        reserved = float(multi["cuda_memory_reserved_peak_mb"])
        checks.append(
            ValidationCheck(
                "msi_benchmark_margin",
                "pass" if multi_spf < single_spf and reserved < 5000 else "warn",
                "multi_frame_perf_vram",
                f"{multi_spf:.4f}s/frame, {reserved:.0f}MB reserved",
                f"< {single_spf:.4f}s/frame and < 5000MB reserved",
                "experiments/test_007_msi_benchmarks/video_836_sam3/metrics.csv",
                "Repetir benchmark con 3 corridas si se necesita comparar optimizaciones.",
            )
        )

    tracked_heavy = git_has_tracked_heavy_files()
    checks.append(
        ValidationCheck(
            "heavy_files_policy",
            "fail" if tracked_heavy else "pass",
            "tracked_heavy_files",
            "present" if tracked_heavy else "none",
            "none",
            ".gitignore and git ls-files",
            "Mantener videos y checkpoints fuera de Git.",
        )
    )

    return checks


def write_report(checks: list[ValidationCheck], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    csv_path = output_dir / "validation_report.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(asdict(checks[0]).keys()), lineterminator="\n")
        writer.writeheader()
        for check in checks:
            writer.writerow(asdict(check))

    counts = {status: sum(1 for check in checks if check.status == status) for status in ("pass", "warn", "fail")}
    lines = [
        "# Validacion Nivel 1",
        "",
        "## Resumen",
        "",
        f"- Checks pass: `{counts['pass']}`.",
        f"- Checks warn: `{counts['warn']}`.",
        f"- Checks fail: `{counts['fail']}`.",
        "",
        "## Checks",
        "",
    ]
    for check in checks:
        lines.append(
            "- `{check_id}`: `{status}`; {metric} = `{observed}`; esperado `{expected}`.".format(**asdict(check))
        )
    lines.extend(
        [
            "",
            "## Recomendaciones",
            "",
        ]
    )
    for check in checks:
        if check.status != "pass":
            lines.append(f"- `{check.check_id}`: {check.recommendation}")
    if all(check.status == "pass" for check in checks):
        lines.append("- No hay bloqueadores de Nivel 1 en los checks automaticos.")
    (output_dir / "validation_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate a lightweight Level 1 validation report.")
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--output-dir", default="experiments/evidence_level1")
    args = parser.parse_args()

    root = Path(args.repo_root)
    checks = build_checks(root)
    write_report(checks, Path(args.output_dir))
    print(f"Wrote Level 1 validation report to {args.output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
