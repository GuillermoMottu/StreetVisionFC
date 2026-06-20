from __future__ import annotations

import argparse
import csv
import json
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


HEAVY_EXTENSIONS = (".mov", ".mp4", ".avi", ".mkv", ".m4v", ".pt", ".pth", ".onnx", ".safetensors")
ALLOWED_TRACKED_HEAVY_FILES = {"outputs/videos/futbotmx_demo_h264.mp4"}
DEFAULT_OUTPUT_DIR = Path("experiments/test_018_level3_readiness")
REEL_URL = "https://www.instagram.com/reel/DZynpB2pH_L_Mxq8V9Iq3bN5WHSFDGvsy_17iw0/"


@dataclass(frozen=True)
class ReadinessCheck:
    check_id: str
    status: str
    evidence: str
    notes: str


@dataclass(frozen=True)
class ClipSelection:
    clip_id: str
    role: str
    status: str
    evidence: str
    rationale: str


CLIP_SELECTIONS = (
    ClipSelection(
        "video_836",
        "principal",
        "selected",
        "outputs/videos/futbotmx_demo_h264.mp4",
        "Clip principal de evaluacion publica, con segmentacion, tracking, eventos y heatmap.",
    ),
    ClipSelection(
        "frame_143",
        "supervised_metrics",
        "selected",
        "data/annotations/train_COCO/_annotations.coco.json",
        "Frame con anotaciones humanas y metricas supervisadas IoU@0.5.",
    ),
    ClipSelection(
        "multi_clip_support",
        "configuration",
        "ready",
        ".env.example",
        "Las rutas de clips adicionales se configuran localmente sin exponer rutas personales.",
    ),
)


def read_csv(path: str | Path) -> list[dict[str, str]]:
    with Path(path).open("r", newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def read_json(path: str | Path) -> Any:
    with Path(path).open("r", encoding="utf-8") as handle:
        return json.load(handle)


def git_has_tracked_heavy_files(root: Path) -> bool:
    try:
        result = subprocess.run(["git", "ls-files"], cwd=root, check=True, capture_output=True, text=True, timeout=10)
    except (FileNotFoundError, subprocess.SubprocessError):
        return False
    return any(
        line.lower().endswith(HEAVY_EXTENSIONS) and line not in ALLOWED_TRACKED_HEAVY_FILES
        for line in result.stdout.splitlines()
    )


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


def public_demo_ready(root: Path) -> tuple[bool, str]:
    path = root / "outputs/videos/futbotmx_demo_h264.mp4"
    if not path.exists():
        return False, "missing public demo MP4"
    size = path.stat().st_size
    if size < 1_000_000:
        return False, f"demo too small: {size} bytes"
    return True, f"demo present ({size} bytes)"


def public_outputs_ready(root: Path) -> tuple[bool, str]:
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
        return False, f"tracking rows too low: {len(tracks)}"
    if not isinstance(events, list) or not events:
        return False, "events.json has no events"
    if heatmap_size <= 0:
        return False, "heatmap is empty"
    return True, f"tracks={len(tracks)}, events={len(events)}, heatmap_bytes={heatmap_size}"


def annotation_package_ready(root: Path) -> tuple[bool, str]:
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
    return True, f"annotation frames={len(frames)}"


def level3_code_ready(root: Path) -> tuple[bool, str]:
    return required_paths_exist(
        root,
        [
            "src/futbotmx/level3/spatial.py",
            "src/futbotmx/level3/tactical.py",
            "src/futbotmx/level3/advanced_events.py",
            "src/futbotmx/level3/visualizations.py",
            "src/futbotmx/level3/dashboard.py",
            "src/futbotmx/level3/reel.py",
        ],
    )


def professional_docs_ready(root: Path) -> tuple[bool, str]:
    docs_ok, docs_notes = required_paths_exist(
        root,
        [
            "README.md",
            "docs/EVALUATOR_GUIDE.md",
            "docs/PROFESSIONAL_EVALUATION.md",
            "docs/REPRODUCIBILITY.md",
            "docs/RESULTS_SUMMARY.md",
            "THIRD_PARTY_NOTICES.md",
        ],
    )
    if not docs_ok:
        return False, docs_notes
    return text_contains_all(
        root,
        "docs/PROFESSIONAL_EVALUATION.md",
        [
            "Professional innovation is demonstrated",
            "Demo video under 2 minutes",
            "Public Instagram Reel link",
            "Level 3 closure gate",
        ],
    )


def reproducibility_ready(root: Path) -> tuple[bool, str]:
    paths_ok, paths_notes = required_paths_exist(
        root,
        [
            ".env.example",
            "configs/local_paths.example.yaml",
            "requirements-gpu.txt",
            ".github/workflows/ci.yml",
        ],
    )
    if not paths_ok:
        return False, paths_notes
    ci_text = (root / ".github/workflows/ci.yml").read_text(encoding="utf-8")
    temporary_branch = "fix/" + "master-audit-corrections"
    if temporary_branch in ci_text:
        return False, "CI still references temporary branch"
    return True, "environment templates and CI are ready"


def reel_registered(root: Path) -> tuple[bool, str]:
    for relative_path in ("README.md", "ARTIFACTS_INDEX.md", "docs/EVALUATOR_GUIDE.md"):
        ok, notes = text_contains_all(root, relative_path, [REEL_URL])
        if not ok:
            return False, notes
    return True, "public reel URL registered in README, evaluator guide and artifact index"


def build_checks(root: Path) -> list[ReadinessCheck]:
    docs_ok, docs_notes = professional_docs_ready(root)
    demo_ok, demo_notes = public_demo_ready(root)
    outputs_ok, outputs_notes = public_outputs_ready(root)
    annotations_ok, annotations_notes = annotation_package_ready(root)
    code_ok, code_notes = level3_code_ready(root)
    reproducibility_ok, reproducibility_notes = reproducibility_ready(root)
    reel_ok, reel_notes = reel_registered(root)
    has_heavy = git_has_tracked_heavy_files(root)

    return [
        ReadinessCheck("professional_docs_ready", "pass" if docs_ok else "fail", "README.md, docs/", docs_notes),
        ReadinessCheck("public_demo_ready", "pass" if demo_ok else "fail", "outputs/videos/futbotmx_demo_h264.mp4", demo_notes),
        ReadinessCheck("public_outputs_ready", "pass" if outputs_ok else "fail", "outputs/", outputs_notes),
        ReadinessCheck("annotation_package_ready", "pass" if annotations_ok else "fail", "data/annotations/", annotations_notes),
        ReadinessCheck("level3_code_ready", "pass" if code_ok else "fail", "src/futbotmx/level3/", code_notes),
        ReadinessCheck("reproducibility_ready", "pass" if reproducibility_ok else "fail", ".env.example, configs/, CI", reproducibility_notes),
        ReadinessCheck("reel_registered", "pass" if reel_ok else "fail", "README/docs/ARTIFACTS_INDEX.md", reel_notes),
        ReadinessCheck(
            "no_unapproved_heavy_files",
            "pass" if not has_heavy else "fail",
            "git ls-files",
            "Solo el demo publico versionado puede ser MP4 en Git; videos fuente, checkpoints y modelos quedan fuera.",
        ),
    ]


def write_config(output_dir: Path) -> None:
    lines = [
        "level3_readiness:",
        "  rule_version: public_professional_readiness_v1",
        "  package: public_repository_main",
        "  primary_clip: video_836",
        "  public_demo: outputs/videos/futbotmx_demo_h264.mp4",
        "  evidence_policy:",
        "    - public_demo_mp4_allowed",
        "    - source_videos_configured_by_env",
        "    - model_checkpoints_from_official_sources",
        "    - lightweight_outputs_and_docs_in_git",
    ]
    (output_dir / "config.yaml").write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_report(checks: list[ReadinessCheck], clip_selections: tuple[ClipSelection, ...], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    with (output_dir / "readiness_checks.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(asdict(checks[0]).keys()), lineterminator="\n")
        writer.writeheader()
        for check in checks:
            writer.writerow(asdict(check))

    with (output_dir / "clip_selection.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(asdict(clip_selections[0]).keys()), lineterminator="\n")
        writer.writeheader()
        for clip in clip_selections:
            writer.writerow(asdict(clip))

    write_config(output_dir)

    passed = sum(1 for check in checks if check.status == "pass")
    failed = sum(1 for check in checks if check.status == "fail")
    status = "desbloqueado" if failed == 0 else "requiere_atencion"
    lines = [
        "# Readiness Nivel 3",
        "",
        "## Resultado",
        "",
        f"- Estado: `{status}`.",
        f"- Checks pass: `{passed}`.",
        f"- Checks fail: `{failed}`.",
        "",
        "## Seleccion De Evidencia",
        "",
    ]
    for clip in clip_selections:
        lines.append(f"- `{clip.clip_id}`: `{clip.role}` / `{clip.status}`; evidencia `{clip.evidence}`; motivo: {clip.rationale}")

    lines.extend(["", "## Checks", ""])
    for check in checks:
        lines.append(f"- `{check.check_id}`: `{check.status}`; evidencia `{check.evidence}`; nota: {check.notes}")

    lines.extend(
        [
            "",
            "## Decision",
            "",
            (
                "El paquete publico profesional queda listo para evaluacion."
                if failed == 0
                else "El paquete publico profesional requiere corregir checks fallidos antes de evaluacion."
            ),
        ]
    )
    (output_dir / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Check whether the public Level 3 professional package is ready.")
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    args = parser.parse_args()

    root = Path(args.repo_root).resolve()
    output_dir = root / args.output_dir
    checks = build_checks(root)
    write_report(checks, CLIP_SELECTIONS, output_dir)
    failed = sum(1 for check in checks if check.status == "fail")
    print(f"Wrote Level 3 readiness report to {output_dir}")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
