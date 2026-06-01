from __future__ import annotations

import argparse
import csv
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass(frozen=True)
class ReadinessCheck:
    check_id: str
    status: str
    evidence: str
    notes: str


def path_exists(path: str | Path) -> bool:
    return Path(path).exists()


def read_csv(path: str | Path) -> list[dict[str, str]]:
    with Path(path).open("r", newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def git_has_tracked_heavy_files() -> bool:
    extensions = (".mov", ".mp4", ".avi", ".mkv", ".m4v", ".pt", ".pth", ".onnx", ".safetensors")
    try:
        result = subprocess.run(["git", "ls-files"], check=True, capture_output=True, text=True, timeout=10)
    except (FileNotFoundError, subprocess.SubprocessError):
        return False
    return any(line.lower().endswith(extensions) for line in result.stdout.splitlines())


def validation_report_is_green(path: str | Path) -> bool:
    rows = read_csv(path)
    return bool(rows) and all(row["status"] == "pass" for row in rows)


def build_checks(root: Path) -> list[ReadinessCheck]:
    checks = [
        ReadinessCheck(
            "level1_validation_green",
            "pass" if validation_report_is_green(root / "experiments/evidence_level1/validation_report.csv") else "fail",
            "experiments/evidence_level1/validation_report.csv",
            "Nivel 1 debe tener todos los checks automaticos en pass.",
        ),
        ReadinessCheck(
            "level1_delivery_summary",
            "pass" if path_exists(root / "experiments/evidence_level1/DELIVERY_SUMMARY.md") else "fail",
            "experiments/evidence_level1/DELIVERY_SUMMARY.md",
            "Resumen de entrega Nivel 1 disponible.",
        ),
        ReadinessCheck(
            "level1_demo_documented",
            "pass" if path_exists(root / "experiments/evidence_level1/demo_local.md") else "fail",
            "experiments/evidence_level1/demo_local.md",
            "Demo local anotada documentada; MP4 permanece fuera de Git.",
        ),
        ReadinessCheck(
            "level1_events_real",
            "pass" if path_exists(root / "experiments/test_004_events/video_836_real_events_120_180/events.json") else "fail",
            "experiments/test_004_events/video_836_real_events_120_180/events.json",
            "Eventos Nivel 1 reales generados desde tracks ByteTrack.",
        ),
        ReadinessCheck(
            "level1_tracks_real",
            "pass" if path_exists(root / "experiments/test_003_tracking/video_836_real_tracking_120_180/tracks_bytetrack.csv") else "fail",
            "experiments/test_003_tracking/video_836_real_tracking_120_180/tracks_bytetrack.csv",
            "Tracks reales ByteTrack disponibles.",
        ),
        ReadinessCheck(
            "no_tracked_heavy_files",
            "fail" if git_has_tracked_heavy_files() else "pass",
            "git ls-files",
            "Videos, checkpoints y modelos pesados deben quedar fuera de Git.",
        ),
    ]
    return checks


def write_report(checks: list[ReadinessCheck], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    with (output_dir / "readiness_checks.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(asdict(checks[0]).keys()), lineterminator="\n")
        writer.writeheader()
        for check in checks:
            writer.writerow(asdict(check))

    passed = sum(1 for check in checks if check.status == "pass")
    failed = sum(1 for check in checks if check.status == "fail")
    status = "desbloqueado" if failed == 0 else "bloqueado"
    lines = [
        "# Level 2 unlock readiness",
        "",
        "## Resultado",
        "",
        f"- Estado: `{status}`.",
        f"- Checks pass: `{passed}`.",
        f"- Checks fail: `{failed}`.",
        "",
        "## Checks",
        "",
    ]
    for check in checks:
        lines.append(f"- `{check.check_id}`: `{check.status}`; evidencia `{check.evidence}`.")
    lines.extend(
        [
            "",
            "## Decision",
            "",
            "Nivel 2 queda desbloqueado para planeacion e implementacion inicial." if failed == 0 else "Nivel 2 permanece bloqueado hasta corregir checks fallidos.",
        ]
    )
    (output_dir / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Check whether FutBotMX Level 2 can be unlocked.")
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--output-dir", default="experiments/test_011_level2_unlock")
    args = parser.parse_args()

    checks = build_checks(Path(args.repo_root))
    write_report(checks, Path(args.output_dir))
    failed = sum(1 for check in checks if check.status == "fail")
    print(f"Wrote Level 2 readiness report to {args.output_dir}")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
