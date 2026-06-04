from __future__ import annotations

import argparse
import csv
import json
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


HEAVY_EXTENSIONS = (".mov", ".mp4", ".avi", ".mkv", ".m4v", ".pt", ".pth", ".onnx", ".safetensors")
LEVEL2_CLOSURE_DIR = Path("experiments/test_017_level2_closure")
DEFAULT_OUTPUT_DIR = Path("experiments/test_018_level3_readiness")
MINIMUM_OBSERVED_FRAMES = 61


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
        "video_595",
        "principal",
        "selected",
        "experiments/test_017_level2_closure/video_595",
        "Mejor candidato narrativo: 61 frames observados, ByteTrack denso y highlight provisional con confianza 0.717.",
    ),
    ClipSelection(
        "video_667",
        "secundario",
        "selected",
        "experiments/test_017_level2_closure/video_667",
        "Clip de contraste multi-clip: 61 frames observados, mas robots visibles y eventos descartados utiles para validar degradacion.",
    ),
    ClipSelection(
        "video_480",
        "diagnostico",
        "kept",
        "experiments/test_017_level2_closure/video_480",
        "Se mantiene como diagnostico porque la muestra existente no detecta balon y requiere prompts pesados en MSI.",
    ),
)


def read_json(path: str | Path) -> Any:
    with Path(path).open("r", encoding="utf-8") as handle:
        return json.load(handle)


def read_csv(path: str | Path) -> list[dict[str, str]]:
    with Path(path).open("r", newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def git_has_tracked_heavy_files(root: Path) -> bool:
    try:
        result = subprocess.run(["git", "ls-files"], cwd=root, check=True, capture_output=True, text=True, timeout=10)
    except (FileNotFoundError, subprocess.SubprocessError):
        return False
    return any(line.lower().endswith(HEAVY_EXTENSIONS) for line in result.stdout.splitlines())


def decision_registered(root: Path) -> bool:
    path = root / "FutBotMX_documentacion_markdown/DECISIONS.md"
    if not path.exists():
        return False
    text = path.read_text(encoding="utf-8")
    return "DEC-012 - Inicio controlado Nivel 3" in text and "Nivel 3 queda iniciado" in text


def level2_closure_summary_ready(root: Path) -> bool:
    path = root / LEVEL2_CLOSURE_DIR / "LEVEL2_CLOSURE_SUMMARY.md"
    if not path.exists():
        return False
    text = path.read_text(encoding="utf-8")
    return "Nivel 2 cerrado" in text and "Nivel 3 listo para gate/decision" in text


def level2_closure_report_exists(root: Path) -> tuple[bool, str]:
    path = root / LEVEL2_CLOSURE_DIR / "summary.md"
    if not path.exists():
        return False, "missing summary.md"
    text = path.read_text(encoding="utf-8")
    if "Nivel 2 cerrado" not in text:
        return False, "summary.md does not declare Nivel 2 cerrado"
    return True, "closure report present"


def level2_closure_checks_green(root: Path) -> tuple[bool, str]:
    path = root / LEVEL2_CLOSURE_DIR / "closure_checks.csv"
    if not path.exists():
        return False, "missing closure_checks.csv"
    rows = read_csv(path)
    if not rows:
        return False, "empty closure_checks.csv"
    failing = [row.get("check_id", "unknown") for row in rows if row.get("status") != "pass"]
    if failing:
        return False, "failing checks: " + ", ".join(failing)
    return True, f"{len(rows)} closure checks pass"


def candidate_clip_ready(root: Path, clip_id: str, minimum_frames: int = MINIMUM_OBSERVED_FRAMES) -> tuple[bool, str]:
    clip_dir = root / LEVEL2_CLOSURE_DIR / clip_id
    required = [
        clip_dir / "config.yaml",
        clip_dir / "summary.md",
        clip_dir / "tracks_level2.csv",
        clip_dir / "level2_events.json",
        clip_dir / "level2_metrics.json",
    ]
    missing = [str(path.relative_to(root)) for path in required if not path.exists()]
    if missing:
        return False, "missing " + ", ".join(missing)

    metrics = read_json(clip_dir / "level2_metrics.json")
    observed_frames = int(metrics.get("summary", {}).get("observed_frames", 0))
    if observed_frames < minimum_frames:
        return False, f"observed_frames={observed_frames}, expected>={minimum_frames}"

    tracks = read_csv(clip_dir / "tracks_level2.csv")
    if not tracks:
        return False, "tracks_level2.csv is empty"
    if not any("_bt_" in row.get("track_id", "") for row in tracks):
        return False, "tracks do not look like ByteTrack output"

    events = read_json(clip_dir / "level2_events.json")
    if not isinstance(events, list) or not events:
        return False, "level2_events.json has no events"

    return True, f"observed_frames={observed_frames}, tracks={len(tracks)}, events={len(events)}"


def diagnostic_clip_ready(root: Path, clip_id: str) -> tuple[bool, str]:
    clip_dir = root / LEVEL2_CLOSURE_DIR / clip_id
    required = [clip_dir / "summary.md", clip_dir / "diagnostic_summary.md"]
    missing = [str(path.relative_to(root)) for path in required if not path.exists()]
    if missing:
        return False, "missing " + ", ".join(missing)
    return True, "diagnostic summary present"


def clip_selection_defined() -> tuple[bool, str]:
    primary = [clip for clip in CLIP_SELECTIONS if clip.role == "principal" and clip.status == "selected"]
    secondary = [clip for clip in CLIP_SELECTIONS if clip.role == "secundario" and clip.status == "selected"]
    diagnostic = [clip for clip in CLIP_SELECTIONS if clip.role == "diagnostico"]
    if not primary:
        return False, "missing primary clip"
    if not secondary:
        return False, "missing secondary clip"
    if not diagnostic:
        return False, "missing diagnostic clip"
    return True, f"primary={primary[0].clip_id}, secondary={secondary[0].clip_id}, diagnostic={diagnostic[0].clip_id}"


def build_checks(root: Path) -> list[ReadinessCheck]:
    closure_report_ok, closure_report_notes = level2_closure_report_exists(root)
    closure_checks_ok, closure_checks_notes = level2_closure_checks_green(root)
    video_595_ok, video_595_notes = candidate_clip_ready(root, "video_595")
    video_667_ok, video_667_notes = candidate_clip_ready(root, "video_667")
    video_480_ok, video_480_notes = diagnostic_clip_ready(root, "video_480")
    selection_ok, selection_notes = clip_selection_defined()
    dense_clip_count = sum(1 for ok in (video_595_ok, video_667_ok) if ok)

    return [
        ReadinessCheck(
            "level3_decision_registered",
            "pass" if decision_registered(root) else "fail",
            "FutBotMX_documentacion_markdown/DECISIONS.md",
            "DEC-012 debe formalizar el inicio controlado de Nivel 3.",
        ),
        ReadinessCheck(
            "level2_closure_report_present",
            "pass" if closure_report_ok else "fail",
            "experiments/test_017_level2_closure/summary.md",
            closure_report_notes,
        ),
        ReadinessCheck(
            "level2_closure_summary_ready",
            "pass" if level2_closure_summary_ready(root) else "fail",
            "experiments/test_017_level2_closure/LEVEL2_CLOSURE_SUMMARY.md",
            "Nivel 2 debe estar cerrado y Nivel 3 listo para gate/decision.",
        ),
        ReadinessCheck(
            "level2_closure_checks_green",
            "pass" if closure_checks_ok else "fail",
            "experiments/test_017_level2_closure/closure_checks.csv",
            closure_checks_notes,
        ),
        ReadinessCheck(
            "no_tracked_heavy_files",
            "pass" if not git_has_tracked_heavy_files(root) else "fail",
            "git ls-files",
            "Videos, checkpoints, modelos y renders pesados deben quedar fuera de Git.",
        ),
        ReadinessCheck(
            "primary_clip_video_595_ready",
            "pass" if video_595_ok else "fail",
            "experiments/test_017_level2_closure/video_595",
            video_595_notes,
        ),
        ReadinessCheck(
            "secondary_clip_video_667_ready",
            "pass" if video_667_ok else "fail",
            "experiments/test_017_level2_closure/video_667",
            video_667_notes,
        ),
        ReadinessCheck(
            "minimum_two_dense_clips",
            "pass" if dense_clip_count >= 2 else "fail",
            "experiments/test_017_level2_closure/video_595, experiments/test_017_level2_closure/video_667",
            f"dense_clips_ready={dense_clip_count}, expected>=2",
        ),
        ReadinessCheck(
            "diagnostic_clip_video_480_ready",
            "pass" if video_480_ok else "fail",
            "experiments/test_017_level2_closure/video_480",
            video_480_notes,
        ),
        ReadinessCheck(
            "level3_clip_selection_defined",
            "pass" if selection_ok else "fail",
            "experiments/test_018_level3_readiness/clip_selection.csv",
            selection_notes,
        ),
    ]


def write_config(output_dir: Path) -> None:
    lines = [
        "level3_readiness:",
        "  rule_version: level3_readiness_v0.1",
        f"  source_gate: {LEVEL2_CLOSURE_DIR.as_posix()}",
        "  primary_clip: video_595",
        "  secondary_clips:",
        "    - video_667",
        "  diagnostic_clips:",
        "    - video_480",
        f"  minimum_observed_frames: {MINIMUM_OBSERVED_FRAMES}",
        "  heavy_file_policy: no_tracked_heavy_files",
        "  scope_control:",
        "    - no_new_sam3_inference_required_for_activity_0",
        "    - keep_heavy_outputs_out_of_git",
        "    - continue_to_activity_1_only_after_zero_fail_readiness",
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
    status = "desbloqueado" if failed == 0 else "bloqueado"
    lines = [
        "# Readiness Nivel 3",
        "",
        "## Resultado",
        "",
        f"- Estado: `{status}`.",
        f"- Checks pass: `{passed}`.",
        f"- Checks fail: `{failed}`.",
        "",
        "## Seleccion De Clips",
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
                "Nivel 3 queda desbloqueado para implementacion controlada desde Actividad 1."
                if failed == 0
                else "Nivel 3 permanece bloqueado hasta corregir checks fallidos."
            ),
            "",
            "## Alcance",
            "",
            "- Actividad 0 no requiere inferencia SAM 3 nueva.",
            "- `video_595` sera el clip principal para demo Nivel 3.",
            "- `video_667` sera el clip secundario para validacion multi-clip.",
            "- `video_480` se conserva como diagnostico por inestabilidad de balon.",
            "- Los siguientes pasos deben producir solo evidencia ligera versionable.",
        ]
    )
    (output_dir / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Check whether FutBotMX Level 3 can start in controlled scope.")
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
