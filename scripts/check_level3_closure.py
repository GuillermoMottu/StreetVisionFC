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
DEFAULT_OUTPUT_DIR = Path("experiments/test_027_level3_closure")
READINESS_OUTPUT_DIR = Path("experiments/test_018_level3_readiness")
REEL_URL = "https://www.instagram.com/reel/DZynpB2pH_L_Mxq8V9Iq3bN5WHSFDGvsy_17iw0/"


@dataclass(frozen=True)
class Level3ClosureCheck:
    check_id: str
    status: str
    evidence: str
    notes: str


def read_csv(path: str | Path) -> list[dict[str, str]]:
    with Path(path).open("r", newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def read_json(path: str | Path) -> Any:
    with Path(path).open("r", encoding="utf-8") as handle:
        return json.load(handle)


def run_command(root: Path, command: list[str], timeout: int = 120) -> tuple[bool, str]:
    env = os.environ.copy()
    env.setdefault("MPLCONFIGDIR", "/tmp/matplotlib")
    try:
        result = subprocess.run(command, cwd=root, env=env, capture_output=True, text=True, timeout=timeout)
    except (FileNotFoundError, subprocess.SubprocessError) as exc:
        return False, str(exc)
    output = (result.stdout + "\n" + result.stderr).strip()
    if result.returncode == 0:
        return True, output.splitlines()[-1] if output else "command completed"
    return False, (output[-500:] if output else f"returncode={result.returncode}")


def python_executable(root: Path) -> str:
    venv_python = root / ".venv/bin/python"
    return str(venv_python) if venv_python.exists() else sys.executable


def required_paths_exist(root: Path, paths: list[str]) -> tuple[bool, str]:
    missing = [path for path in paths if not (root / path).exists()]
    if missing:
        return False, "missing " + ", ".join(missing)
    return True, f"{len(paths)} required paths present"


def text_contains_all(root: Path, relative_path: str, needles: list[str]) -> tuple[bool, str]:
    path = root / relative_path
    if not path.exists():
        return False, f"missing {relative_path}"
    text = path.read_text(encoding="utf-8")
    missing = [needle for needle in needles if needle not in text]
    if missing:
        return False, "missing text: " + ", ".join(missing)
    return True, f"{relative_path} contains required evidence"


def all_csv_status_pass(root: Path, relative_path: str, status_field: str = "status") -> tuple[bool, str]:
    path = root / relative_path
    if not path.exists():
        return False, f"missing {relative_path}"
    rows = read_csv(path)
    if not rows:
        return False, f"empty {relative_path}"
    failing = [row.get("check_id", "unknown") for row in rows if row.get(status_field) != "pass"]
    if failing:
        return False, "failing rows: " + ", ".join(failing)
    return True, f"{len(rows)} rows pass"


def unit_tests_green(root: Path) -> tuple[bool, str]:
    return run_command(root, [python_executable(root), "-m", "unittest", "discover", "-s", "tests", "-q"], timeout=180)


def readiness_green(root: Path) -> tuple[bool, str]:
    command_ok, command_notes = run_command(root, [python_executable(root), "scripts/check_level3_readiness.py"], timeout=90)
    csv_ok, csv_notes = all_csv_status_pass(root, (READINESS_OUTPUT_DIR / "readiness_checks.csv").as_posix())
    return command_ok and csv_ok, f"{command_notes}; {csv_notes}"


def git_has_tracked_heavy_files(root: Path) -> tuple[bool, str]:
    try:
        result = subprocess.run(["git", "ls-files"], cwd=root, check=True, capture_output=True, text=True, timeout=10)
    except (FileNotFoundError, subprocess.SubprocessError) as exc:
        return False, str(exc)
    heavy = [
        line
        for line in result.stdout.splitlines()
        if line.lower().endswith(HEAVY_EXTENSIONS) and line not in ALLOWED_TRACKED_HEAVY_FILES
    ]
    return bool(heavy), ", ".join(heavy[:8]) if heavy else "no unapproved tracked heavy files"


def professional_docs_ok(root: Path) -> tuple[bool, str]:
    paths_ok, paths_notes = required_paths_exist(
        root,
        [
            "README.md",
            "docs/EVALUATOR_GUIDE.md",
            "docs/PROFESSIONAL_EVALUATION.md",
            "docs/RESULTS_SUMMARY.md",
            "docs/SAM3_PIPELINE.md",
            "docs/TECHNICAL_ARCHITECTURE.md",
        ],
    )
    if not paths_ok:
        return False, paths_notes
    return text_contains_all(
        root,
        "docs/PROFESSIONAL_EVALUATION.md",
        [
            "Functional SAM 3 processing flow",
            "Professional innovation is demonstrated",
            "Level 3 closure gate",
            "461 tests",
        ],
    )


def public_demo_ok(root: Path) -> tuple[bool, str]:
    path = root / "outputs/videos/futbotmx_demo_h264.mp4"
    if not path.exists():
        return False, "missing outputs/videos/futbotmx_demo_h264.mp4"
    size = path.stat().st_size
    if size < 1_000_000:
        return False, f"demo too small: {size} bytes"
    return True, f"demo present ({size} bytes, documented as 46.6 s)"


def public_outputs_ok(root: Path) -> tuple[bool, str]:
    paths_ok, paths_notes = required_paths_exist(
        root,
        [
            "outputs/tracking/tracks.csv",
            "outputs/events/events.json",
            "outputs/visualizations/heatmap.png",
        ],
    )
    if not paths_ok:
        return False, paths_notes
    tracks = read_csv(root / "outputs/tracking/tracks.csv")
    events = read_json(root / "outputs/events/events.json")
    heatmap_size = (root / "outputs/visualizations/heatmap.png").stat().st_size
    if len(tracks) < 10:
        return False, f"tracking rows={len(tracks)}, expected>=10"
    if not isinstance(events, list) or not events:
        return False, "events.json has no events"
    if heatmap_size <= 0:
        return False, "heatmap is empty"
    return True, f"tracks={len(tracks)}, events={len(events)}, heatmap_bytes={heatmap_size}"


def annotation_package_ok(root: Path) -> tuple[bool, str]:
    paths_ok, paths_notes = required_paths_exist(
        root,
        [
            "data/annotations/annotation_template.json",
            "data/annotations/train_COCO/_annotations.coco.json",
        ],
    )
    if not paths_ok:
        return False, paths_notes
    frames = sorted((root / "data/annotations/frames").glob("*.png"))
    if len(frames) < 8:
        return False, f"annotation frames={len(frames)}, expected>=8"
    return True, f"annotation frames={len(frames)}, supervised labels documented"


def level3_code_ok(root: Path) -> tuple[bool, str]:
    return required_paths_exist(
        root,
        [
            "src/futbotmx/level3/schema.py",
            "src/futbotmx/level3/spatial.py",
            "src/futbotmx/level3/tactical.py",
            "src/futbotmx/level3/advanced_events.py",
            "src/futbotmx/level3/visualizations.py",
            "src/futbotmx/level3/dashboard.py",
            "src/futbotmx/level3/reel.py",
            "src/futbotmx/level3/multiclip.py",
        ],
    )


def quantitative_results_ok(root: Path) -> tuple[bool, str]:
    return text_contains_all(
        root,
        "docs/RESULTS_SUMMARY.md",
        [
            "0.857",
            "0.447 FPS",
            "VRAM peak",
            "461 tests: PASS",
        ],
    )


def external_reel_ok(root: Path) -> tuple[bool, str]:
    for relative_path in ("README.md", "ARTIFACTS_INDEX.md", "docs/EVALUATOR_GUIDE.md", "docs/PROFESSIONAL_EVALUATION.md"):
        ok, notes = text_contains_all(root, relative_path, [REEL_URL])
        if not ok:
            return False, notes
    return True, "Instagram Reel URL registered across public docs"


def reproducibility_package_ok(root: Path) -> tuple[bool, str]:
    paths_ok, paths_notes = required_paths_exist(
        root,
        [
            ".env.example",
            "configs/local_paths.example.yaml",
            "requirements-gpu.txt",
            "THIRD_PARTY_NOTICES.md",
            "LICENSE",
            ".github/workflows/ci.yml",
        ],
    )
    if not paths_ok:
        return False, paths_notes
    ci_text = (root / ".github/workflows/ci.yml").read_text(encoding="utf-8")
    temporary_branch = "fix/" + "master-audit-corrections"
    if temporary_branch in ci_text:
        return False, "CI still references temporary branch"
    return True, "install, environment, CI, license and notices are present"


def build_checks(root: Path) -> list[Level3ClosureCheck]:
    tests_ok, tests_notes = unit_tests_green(root)
    readiness_ok, readiness_notes = readiness_green(root)
    docs_ok, docs_notes = professional_docs_ok(root)
    demo_ok, demo_notes = public_demo_ok(root)
    outputs_ok, outputs_notes = public_outputs_ok(root)
    annotations_ok, annotations_notes = annotation_package_ok(root)
    code_ok, code_notes = level3_code_ok(root)
    quantitative_ok, quantitative_notes = quantitative_results_ok(root)
    reel_ok, reel_notes = external_reel_ok(root)
    reproducibility_ok, reproducibility_notes = reproducibility_package_ok(root)
    has_heavy, heavy_notes = git_has_tracked_heavy_files(root)

    return [
        Level3ClosureCheck("unit_tests_green", "pass" if tests_ok else "fail", "python -m unittest discover -s tests -q", tests_notes),
        Level3ClosureCheck("level3_readiness_green", "pass" if readiness_ok else "fail", "scripts/check_level3_readiness.py", readiness_notes),
        Level3ClosureCheck("professional_docs_complete", "pass" if docs_ok else "fail", "README.md, docs/", docs_notes),
        Level3ClosureCheck("public_demo_video", "pass" if demo_ok else "fail", "outputs/videos/futbotmx_demo_h264.mp4", demo_notes),
        Level3ClosureCheck("public_outputs_present", "pass" if outputs_ok else "fail", "outputs/", outputs_notes),
        Level3ClosureCheck("annotation_package", "pass" if annotations_ok else "fail", "data/annotations/", annotations_notes),
        Level3ClosureCheck("level3_code_surface", "pass" if code_ok else "fail", "src/futbotmx/level3/", code_notes),
        Level3ClosureCheck("quantitative_results_documented", "pass" if quantitative_ok else "fail", "docs/RESULTS_SUMMARY.md", quantitative_notes),
        Level3ClosureCheck("external_reel_publication", "pass" if reel_ok else "fail", "README/docs/ARTIFACTS_INDEX.md", reel_notes),
        Level3ClosureCheck("reproducibility_package", "pass" if reproducibility_ok else "fail", ".env.example, requirements-gpu.txt, CI", reproducibility_notes),
        Level3ClosureCheck("no_unapproved_tracked_heavy_files", "pass" if not has_heavy else "fail", "git ls-files", heavy_notes),
    ]


def write_report(checks: list[Level3ClosureCheck], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    with (output_dir / "closure_checks.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(asdict(checks[0]).keys()), lineterminator="\n")
        writer.writeheader()
        for check in checks:
            writer.writerow(asdict(check))

    passed = sum(1 for check in checks if check.status == "pass")
    failed = sum(1 for check in checks if check.status == "fail")
    status = "completado" if failed == 0 else "requiere_atencion"
    lines = [
        "# Cierre Profesional Nivel 3",
        "",
        "## Resultado",
        "",
        f"- Estado: `{status}`.",
        f"- Checks pass: `{passed}`.",
        f"- Checks fail: `{failed}`.",
        "- Alcance: paquete publico profesional listo para evaluacion.",
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
            "Nivel 3 queda profesionalmente completado y listo para evaluacion." if failed == 0 else "Nivel 3 requiere corregir checks fallidos antes de evaluacion.",
            "",
            "## Comandos",
            "",
            "```bash",
            ".venv/bin/python -m unittest discover -s tests -q",
            ".venv/bin/python scripts/check_level3_readiness.py",
            ".venv/bin/python scripts/check_level3_closure.py",
            "```",
        ]
    )
    (output_dir / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Check whether the public professional package is closed.")
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    args = parser.parse_args()

    root = Path(args.repo_root).resolve()
    output_dir = root / args.output_dir
    checks = build_checks(root)
    write_report(checks, output_dir)

    failed = sum(1 for check in checks if check.status == "fail")
    passed = len(checks) - failed
    print(f"Level 3 closure checks: {passed} pass, {failed} fail. Report: {output_dir / 'summary.md'}")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
