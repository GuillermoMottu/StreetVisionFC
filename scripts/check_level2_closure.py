from __future__ import annotations

import argparse
import csv
import json
import os
import subprocess
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


HEAVY_EXTENSIONS = (".mov", ".mp4", ".avi", ".mkv", ".m4v", ".pt", ".pth", ".onnx", ".safetensors")
ALLOWED_TRACKED_HEAVY_FILES = {"outputs/videos/futbotmx_demo_h264.mp4"}
DEFAULT_OUTPUT_DIR = Path("experiments/test_017_level2_closure")


@dataclass(frozen=True)
class ClosureCheck:
    check_id: str
    status: str
    evidence: str
    notes: str


def read_json(path: str | Path) -> Any:
    with Path(path).open("r", encoding="utf-8") as handle:
        return json.load(handle)


def read_csv(path: str | Path) -> list[dict[str, str]]:
    with Path(path).open("r", newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def path_exists(root: Path, path: str) -> bool:
    return (root / path).exists()


def git_has_tracked_heavy_files(root: Path) -> bool:
    try:
        result = subprocess.run(["git", "ls-files"], cwd=root, check=True, capture_output=True, text=True, timeout=10)
    except (FileNotFoundError, subprocess.SubprocessError):
        return False
    return any(
        line.lower().endswith(HEAVY_EXTENSIONS) and line not in ALLOWED_TRACKED_HEAVY_FILES
        for line in result.stdout.splitlines()
    )


def unit_tests_pass(root: Path) -> bool:
    env = os.environ.copy()
    env.setdefault("MPLCONFIGDIR", "/tmp/matplotlib")
    command = [str(root / ".venv/bin/python"), "-m", "unittest", "discover", "-s", "tests", "-q"]
    if not Path(command[0]).exists():
        command = [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-q"]
    try:
        result = subprocess.run(command, cwd=root, env=env, capture_output=True, text=True, timeout=60)
    except (FileNotFoundError, subprocess.SubprocessError):
        return False
    return result.returncode == 0


def docs_are_current(root: Path) -> tuple[bool, str]:
    checks = {
        "README.md": [
            "SAM 3 real pendiente",
            "Nivel 1 en preparacion",
            "test_002_sam3_segmentation`: bloqueado",
        ],
        "docs/EVALUATOR_GUIDE.md": [
            "SAM 3 pendiente de validación en laptop MSI",
            "Tracking pendiente de prueba real",
            "Eventos pendientes de validación con datos reales",
            "Visualizaciones pendientes de generación",
            "Nivel 2 pendiente",
        ],
        "docs/PROFESSIONAL_EVALUATION.md": [
            "| Posesión | Nivel 1 | Pendiente de validar |",
            "| Timeline de posesión | Nivel 2 | Pendiente |",
        ],
        "docs/RESULTS_SUMMARY.md": [
            "Nivel 3 permanece bloqueado hasta documentar Nivel 2 con resultados.",
        ],
    }
    offenders: list[str] = []
    for relative_path, forbidden_items in checks.items():
        path = root / relative_path
        if not path.exists():
            offenders.append(f"{relative_path}: missing")
            continue
        text = path.read_text(encoding="utf-8")
        for item in forbidden_items:
            if item in text:
                offenders.append(f"{relative_path}: {item}")
    return not offenders, "; ".join(offenders)


def level2_artifact_set_complete(root: Path) -> bool:
    required = [
        "experiments/test_012_level2_metrics/video_836_real_metrics_120_180/level2_metrics.json",
        "experiments/test_013_level2_events/video_836_real_events_120_180/level2_events.json",
        "experiments/test_014_level2_visualizations/video_836_real_visuals_120_180/event_timeline.png",
        "experiments/test_016_level2_demo/LEVEL2_FINAL_SUMMARY.md",
    ]
    return all(path_exists(root, path) for path in required)


def dense_clip_ready(root: Path, clip_id: str, minimum_frames: int) -> tuple[bool, str]:
    clip_dir = root / DEFAULT_OUTPUT_DIR / clip_id
    metrics_path = clip_dir / "level2_metrics.json"
    tracks_path = clip_dir / "tracks_level2.csv"
    events_path = clip_dir / "level2_events.json"
    summary_path = clip_dir / "summary.md"
    missing = [str(path.relative_to(root)) for path in (metrics_path, tracks_path, events_path, summary_path) if not path.exists()]
    if missing:
        return False, "missing " + ", ".join(missing)

    metrics = read_json(metrics_path)
    observed_frames = int(metrics.get("summary", {}).get("observed_frames", 0))
    if observed_frames < minimum_frames:
        return False, f"observed_frames={observed_frames}, expected>={minimum_frames}"

    rows = read_csv(tracks_path)
    if not any("_bt_" in row.get("track_id", "") for row in rows):
        return False, "tracks do not look like ByteTrack output"
    return True, f"observed_frames={observed_frames}, tracks={len(rows)}"


def diagnostic_clip_ready(root: Path, clip_id: str) -> tuple[bool, str]:
    clip_dir = root / DEFAULT_OUTPUT_DIR / clip_id
    required = [clip_dir / "summary.md", clip_dir / "diagnostic_summary.md"]
    missing = [str(path.relative_to(root)) for path in required if not path.exists()]
    if missing:
        return False, "missing " + ", ".join(missing)
    return True, "diagnostic summary present"


def closure_summary_current(root: Path) -> bool:
    path = root / DEFAULT_OUTPUT_DIR / "LEVEL2_CLOSURE_SUMMARY.md"
    if not path.exists():
        return False
    text = path.read_text(encoding="utf-8")
    return "Nivel 2 cerrado" in text and "Nivel 3 listo para gate/decision" in text


def build_checks(root: Path) -> list[ClosureCheck]:
    docs_ok, docs_notes = docs_are_current(root)
    video_595_ok, video_595_notes = dense_clip_ready(root, "video_595", minimum_frames=61)
    video_667_ok, video_667_notes = dense_clip_ready(root, "video_667", minimum_frames=61)
    video_480_ok, video_480_notes = diagnostic_clip_ready(root, "video_480")
    unit_tests_ok = unit_tests_pass(root)
    heavy_files_ok = not git_has_tracked_heavy_files(root)
    baseline_ok = level2_artifact_set_complete(root)
    prerequisites_ok = all((unit_tests_ok, heavy_files_ok, docs_ok, baseline_ok, video_595_ok, video_667_ok, video_480_ok))
    return [
        ClosureCheck(
            "unit_tests_green",
            "pass" if unit_tests_ok else "fail",
            "env MPLCONFIGDIR=/tmp/matplotlib .venv/bin/python -m unittest discover -s tests -q",
            "La suite unitaria debe pasar antes de cerrar Nivel 2.",
        ),
        ClosureCheck(
            "no_tracked_heavy_files",
            "pass" if heavy_files_ok else "fail",
            "git ls-files",
            "Solo el demo publico versionado puede ser MP4 en Git; videos fuente, checkpoints y modelos quedan fuera.",
        ),
        ClosureCheck(
            "docs_current",
            "pass" if docs_ok else "fail",
            "README/docs",
            docs_notes or "No se encontraron estados obsoletos de Nivel 1/Nivel 2 en docs principales.",
        ),
        ClosureCheck(
            "level2_baseline_artifacts",
            "pass" if baseline_ok else "fail",
            "experiments/test_012..016",
            "Metricas, eventos, visualizaciones y demo Nivel 2 base deben existir.",
        ),
        ClosureCheck(
            "video_595_dense_bytetrack",
            "pass" if video_595_ok else "fail",
            "experiments/test_017_level2_closure/video_595",
            video_595_notes,
        ),
        ClosureCheck(
            "video_667_dense_bytetrack",
            "pass" if video_667_ok else "fail",
            "experiments/test_017_level2_closure/video_667",
            video_667_notes,
        ),
        ClosureCheck(
            "video_480_diagnostic",
            "pass" if video_480_ok else "fail",
            "experiments/test_017_level2_closure/video_480",
            video_480_notes,
        ),
        ClosureCheck(
            "closure_summary",
            "pass" if prerequisites_ok or closure_summary_current(root) else "fail",
            "experiments/test_017_level2_closure/LEVEL2_CLOSURE_SUMMARY.md",
            "El resumen final debe declarar Nivel 2 cerrado y Nivel 3 listo para gate/decision.",
        ),
    ]


def write_report(checks: list[ClosureCheck], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    with (output_dir / "closure_checks.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(asdict(checks[0]).keys()), lineterminator="\n")
        writer.writeheader()
        for check in checks:
            writer.writerow(asdict(check))

    passed = sum(1 for check in checks if check.status == "pass")
    failed = sum(1 for check in checks if check.status == "fail")
    status = "cerrado" if failed == 0 else "requiere_atencion"
    lines = [
        "# Cierre Nivel 2",
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
        lines.append(f"- `{check.check_id}`: `{check.status}`; evidencia `{check.evidence}`; nota: {check.notes}")
    lines.extend(
        [
            "",
            "## Decision",
            "",
            "Nivel 2 cerrado; Nivel 3 listo para gate/decision, no iniciado." if failed == 0 else "Nivel 2 aun no esta completamente cerrado.",
        ]
    )
    (output_dir / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    closure_lines = [
        "# LEVEL2_CLOSURE_SUMMARY",
        "",
        "Nivel 2 cerrado." if failed == 0 else "Nivel 2 requiere atencion antes del cierre.",
        "",
        "Nivel 3 listo para gate/decision, no iniciado." if failed == 0 else "Nivel 3 no debe iniciarse hasta resolver checks fallidos.",
        "",
        f"- Checks pass: `{passed}`.",
        f"- Checks fail: `{failed}`.",
    ]
    (output_dir / "LEVEL2_CLOSURE_SUMMARY.md").write_text("\n".join(closure_lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Check whether Level 2 is fully closed and ready for a Level 3 decision.")
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    args = parser.parse_args()

    root = Path(args.repo_root).resolve()
    output_dir = root / args.output_dir
    checks = build_checks(root)
    write_report(checks, output_dir)
    failed = sum(1 for check in checks if check.status == "fail")
    print(f"Wrote Level 2 closure report to {output_dir}")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
