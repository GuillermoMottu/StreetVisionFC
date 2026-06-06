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
DEFAULT_OUTPUT_DIR = Path("experiments/test_027_level3_closure")
READINESS_OUTPUT_DIR = Path("experiments/test_018_level3_readiness")


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


def git_has_tracked_heavy_files(root: Path) -> tuple[bool, str]:
    try:
        result = subprocess.run(["git", "ls-files"], cwd=root, check=True, capture_output=True, text=True, timeout=10)
    except (FileNotFoundError, subprocess.SubprocessError) as exc:
        return False, str(exc)
    heavy = [line for line in result.stdout.splitlines() if line.lower().endswith(HEAVY_EXTENSIONS)]
    return bool(heavy), ", ".join(heavy[:8]) if heavy else "no tracked heavy files"


def required_paths_exist(root: Path, paths: list[str]) -> tuple[bool, str]:
    missing = [path for path in paths if not (root / path).exists()]
    if missing:
        return False, "missing " + ", ".join(missing)
    return True, f"{len(paths)} required paths present"


def csv_non_empty(root: Path, relative_path: str) -> tuple[bool, list[dict[str, str]], str]:
    path = root / relative_path
    if not path.exists():
        return False, [], f"missing {relative_path}"
    rows = read_csv(path)
    if not rows:
        return False, rows, f"empty {relative_path}"
    return True, rows, f"{len(rows)} rows"


def all_csv_status_pass(root: Path, relative_path: str, status_field: str = "status") -> tuple[bool, str]:
    ok, rows, notes = csv_non_empty(root, relative_path)
    if not ok:
        return False, notes
    failing = [row.get("check_id", row.get("asset_id", "unknown")) for row in rows if row.get(status_field) != "pass"]
    if failing:
        return False, "failing rows: " + ", ".join(failing)
    return True, f"{len(rows)} rows pass"


def unit_tests_green(root: Path) -> tuple[bool, str]:
    return run_command(root, [python_executable(root), "-m", "unittest", "discover", "-s", "tests", "-q"], timeout=180)


def readiness_green(root: Path) -> tuple[bool, str]:
    command_ok, command_notes = run_command(root, [python_executable(root), "scripts/check_level3_readiness.py"], timeout=90)
    csv_ok, csv_notes = all_csv_status_pass(root, (READINESS_OUTPUT_DIR / "readiness_checks.csv").as_posix())
    return command_ok and csv_ok, f"{command_notes}; {csv_notes}"


def data_contract_ok(root: Path) -> tuple[bool, str]:
    required = [
        "experiments/test_019_level3_data_contract/config.yaml",
        "experiments/test_019_level3_data_contract/level2_audit.csv",
        "experiments/test_019_level3_data_contract/level3_schema_manifest.csv",
        "experiments/test_019_level3_data_contract/level3_schema.json",
        "experiments/test_019_level3_data_contract/summary.md",
    ]
    paths_ok, paths_notes = required_paths_exist(root, required)
    if not paths_ok:
        return False, paths_notes
    rows = read_csv(root / "experiments/test_019_level3_data_contract/level3_schema_manifest.csv")
    artifact_names = {row.get("artifact_name", "") for row in rows}
    expected = {
        "level3_tracks.csv",
        "level3_metrics.csv",
        "level3_metrics.json",
        "level3_events.json",
        "level3_highlights.csv",
        "level3_narrative.md",
        "level3_visualization_manifest.csv",
    }
    missing = sorted(expected - artifact_names)
    if missing:
        return False, "missing schemas: " + ", ".join(missing)
    return True, f"{paths_notes}; {len(rows)} schemas"


def spatial_model_ok(root: Path) -> tuple[bool, str]:
    required = [
        "experiments/test_020_level3_spatial_model/config.yaml",
        "experiments/test_020_level3_spatial_model/field_calibration.json",
        "experiments/test_020_level3_spatial_model/level3_tracks.csv",
        "experiments/test_020_level3_spatial_model/minimap_base.png",
        "experiments/test_020_level3_spatial_model/minimap_tracks.png",
        "experiments/test_020_level3_spatial_model/spatial_validation.csv",
        "experiments/test_020_level3_spatial_model/summary.md",
    ]
    paths_ok, paths_notes = required_paths_exist(root, required)
    if not paths_ok:
        return False, paths_notes
    validation = read_csv(root / "experiments/test_020_level3_spatial_model/spatial_validation.csv")
    tracks = read_csv(root / "experiments/test_020_level3_spatial_model/level3_tracks.csv")
    usable = [row for row in validation if row.get("calibration_status") == "usable" and int(float(row.get("rectified_rows", 0) or 0)) > 0]
    if len(usable) < 1 or not tracks:
        return False, f"usable_clips={len(usable)}, track_rows={len(tracks)}"
    return True, f"{paths_notes}; usable_clips={len(usable)}, track_rows={len(tracks)}"


def tactical_metrics_ok(root: Path) -> tuple[bool, str]:
    required = [
        "experiments/test_021_level3_tactical_metrics/level3_metrics.csv",
        "experiments/test_021_level3_tactical_metrics/level3_metrics.json",
        "experiments/test_021_level3_tactical_metrics/interaction_metrics.csv",
        "experiments/test_021_level3_tactical_metrics/interaction_edges.csv",
        "experiments/test_021_level3_tactical_metrics/spatial_control.csv",
        "experiments/test_021_level3_tactical_metrics/voronoi_frames.csv",
        "experiments/test_021_level3_tactical_metrics/summary.md",
    ]
    paths_ok, paths_notes = required_paths_exist(root, required)
    if not paths_ok:
        return False, paths_notes
    metrics_rows = read_csv(root / "experiments/test_021_level3_tactical_metrics/level3_metrics.csv")
    metrics_json = read_json(root / "experiments/test_021_level3_tactical_metrics/level3_metrics.json")
    summary = metrics_json.get("summary", {}) if isinstance(metrics_json, dict) else {}
    if len(metrics_rows) == 0 or int(summary.get("interaction_samples", 0)) <= 0:
        return False, f"metric_rows={len(metrics_rows)}, interaction_samples={summary.get('interaction_samples')}"
    return True, f"{paths_notes}; metrics={len(metrics_rows)}, interaction_samples={summary.get('interaction_samples')}"


def advanced_events_ok(root: Path) -> tuple[bool, str]:
    required = [
        "experiments/test_022_level3_advanced_events/level3_events.json",
        "experiments/test_022_level3_advanced_events/level3_highlights.csv",
        "experiments/test_022_level3_advanced_events/level3_narrative.md",
        "experiments/test_022_level3_advanced_events/overlay_validation.csv",
        "experiments/test_022_level3_advanced_events/summary.md",
    ]
    paths_ok, paths_notes = required_paths_exist(root, required)
    if not paths_ok:
        return False, paths_notes
    events = read_json(root / "experiments/test_022_level3_advanced_events/level3_events.json")
    highlights = read_csv(root / "experiments/test_022_level3_advanced_events/level3_highlights.csv")
    overlays = read_csv(root / "experiments/test_022_level3_advanced_events/overlay_validation.csv")
    narrative = (root / "experiments/test_022_level3_advanced_events/level3_narrative.md").read_text(encoding="utf-8")
    if not isinstance(events, list) or len(highlights) < 3 or len(overlays) < 3:
        return False, f"events={len(events) if isinstance(events, list) else 'invalid'}, highlights={len(highlights)}, overlays={len(overlays)}"
    if "no afirma goles" not in narrative:
        return False, "narrative does not include conservative limitation"
    return True, f"{paths_notes}; events={len(events)}, highlights={len(highlights)}, overlays={len(overlays)}"


def manifest_assets_exist(root: Path, manifest_path: str, asset_root: str) -> tuple[bool, str]:
    ok, rows, notes = csv_non_empty(root, manifest_path)
    if not ok:
        return False, notes
    base = root / asset_root
    missing: list[str] = []
    for row in rows:
        if row.get("is_versioned") == "false":
            continue
        asset_type = row.get("asset_type", "")
        if asset_type not in {"png", "csv", "html", "md", "yaml", "json", "sh", "txt"}:
            continue
        path = str(row.get("path", ""))
        if not path:
            continue
        candidate = base / path
        if not candidate.exists():
            missing.append(path)
    if missing:
        return False, "missing manifest assets: " + ", ".join(missing[:8])
    return True, notes


def visualizations_ok(root: Path) -> tuple[bool, str]:
    required = [
        "experiments/test_023_level3_visualizations/visualization_manifest.csv",
        "experiments/test_023_level3_visualizations/highlight_storyboard.png",
        "experiments/test_023_level3_visualizations/highlight_storyboard_manifest.csv",
        "experiments/test_023_level3_visualizations/interaction_graph.png",
        "experiments/test_023_level3_visualizations/summary.md",
    ]
    paths_ok, paths_notes = required_paths_exist(root, required)
    if not paths_ok:
        return False, paths_notes
    manifest_ok, manifest_notes = manifest_assets_exist(
        root,
        "experiments/test_023_level3_visualizations/visualization_manifest.csv",
        "experiments/test_023_level3_visualizations",
    )
    return manifest_ok, f"{paths_notes}; {manifest_notes}"


def dashboard_ok(root: Path) -> tuple[bool, str]:
    required = [
        "experiments/test_024_level3_dashboard/dashboard.html",
        "experiments/test_024_level3_dashboard/dashboard_manifest.csv",
        "experiments/test_024_level3_dashboard/config.yaml",
        "experiments/test_024_level3_dashboard/summary.md",
    ]
    paths_ok, paths_notes = required_paths_exist(root, required)
    if not paths_ok:
        return False, paths_notes
    html = (root / "experiments/test_024_level3_dashboard/dashboard.html").read_text(encoding="utf-8")
    if "Dashboard tactico avanzado" not in html or "level3_metrics.csv" not in html:
        return False, "dashboard HTML does not reference expected Level 3 evidence"
    rows = read_csv(root / "experiments/test_024_level3_dashboard/dashboard_manifest.csv")
    return bool(rows), f"{paths_notes}; manifest_rows={len(rows)}"


def reel_ok(root: Path) -> tuple[bool, str]:
    required = [
        "experiments/test_025_level3_reel/reel_segments.csv",
        "experiments/test_025_level3_reel/reel_manifest.csv",
        "experiments/test_025_level3_reel/reel_demo.html",
        "experiments/test_025_level3_reel/reel_contact_sheet.png",
        "experiments/test_025_level3_reel/summary.md",
    ]
    paths_ok, paths_notes = required_paths_exist(root, required)
    if not paths_ok:
        return False, paths_notes
    segments = read_csv(root / "experiments/test_025_level3_reel/reel_segments.csv")
    manifest = read_csv(root / "experiments/test_025_level3_reel/reel_manifest.csv")
    local_mp4 = [row for row in manifest if row.get("asset_id") == "local_reel_mp4" and row.get("is_versioned") == "false"]
    if len(segments) < 3 or not local_mp4:
        return False, f"segments={len(segments)}, local_mp4_manifested={bool(local_mp4)}"
    return True, f"{paths_notes}; segments={len(segments)}, manifest_rows={len(manifest)}"


def multiclip_ok(root: Path) -> tuple[bool, str]:
    required = [
        "experiments/test_026_level3_multiclip/level3_multiclip_comparison.csv",
        "experiments/test_026_level3_multiclip/level3_multiclip_manifest.csv",
        "experiments/test_026_level3_multiclip/summary.md",
        "experiments/test_026_level3_multiclip/video_595/config.yaml",
        "experiments/test_026_level3_multiclip/video_595/summary.md",
        "experiments/test_026_level3_multiclip/video_595/human_review.csv",
        "experiments/test_026_level3_multiclip/video_667/config.yaml",
        "experiments/test_026_level3_multiclip/video_667/summary.md",
        "experiments/test_026_level3_multiclip/video_667/human_review.csv",
    ]
    paths_ok, paths_notes = required_paths_exist(root, required)
    if not paths_ok:
        return False, paths_notes
    rows = read_csv(root / "experiments/test_026_level3_multiclip/level3_multiclip_comparison.csv")
    generated = [row for row in rows if row.get("pipeline_status") == "generated"]
    if len(generated) < 2:
        return False, f"generated_clips={len(generated)}, expected>=2"
    return True, f"{paths_notes}; generated_clips={len(generated)}"


def build_checks(root: Path) -> list[Level3ClosureCheck]:
    tests_ok, tests_notes = unit_tests_green(root)
    readiness_ok, readiness_notes = readiness_green(root)
    contract_ok, contract_notes = data_contract_ok(root)
    spatial_ok, spatial_notes = spatial_model_ok(root)
    tactical_ok, tactical_notes = tactical_metrics_ok(root)
    events_ok, events_notes = advanced_events_ok(root)
    visuals_ok, visuals_notes = visualizations_ok(root)
    dash_ok, dash_notes = dashboard_ok(root)
    reel_status_ok, reel_notes = reel_ok(root)
    multiclip_status_ok, multiclip_notes = multiclip_ok(root)
    has_heavy, heavy_notes = git_has_tracked_heavy_files(root)

    return [
        Level3ClosureCheck("unit_tests_green", "pass" if tests_ok else "fail", "env MPLCONFIGDIR=/tmp/matplotlib .venv/bin/python -m unittest discover -s tests -q", tests_notes),
        Level3ClosureCheck("level3_readiness_green", "pass" if readiness_ok else "fail", "scripts/check_level3_readiness.py", readiness_notes),
        Level3ClosureCheck("level3_data_contract", "pass" if contract_ok else "fail", "experiments/test_019_level3_data_contract", contract_notes),
        Level3ClosureCheck("level3_spatial_model", "pass" if spatial_ok else "fail", "experiments/test_020_level3_spatial_model", spatial_notes),
        Level3ClosureCheck("level3_tactical_metrics", "pass" if tactical_ok else "fail", "experiments/test_021_level3_tactical_metrics", tactical_notes),
        Level3ClosureCheck("level3_advanced_events", "pass" if events_ok else "fail", "experiments/test_022_level3_advanced_events", events_notes),
        Level3ClosureCheck("level3_visualizations", "pass" if visuals_ok else "fail", "experiments/test_023_level3_visualizations", visuals_notes),
        Level3ClosureCheck("level3_dashboard", "pass" if dash_ok else "fail", "experiments/test_024_level3_dashboard", dash_notes),
        Level3ClosureCheck("level3_reel", "pass" if reel_status_ok else "fail", "experiments/test_025_level3_reel", reel_notes),
        Level3ClosureCheck("level3_multiclip", "pass" if multiclip_status_ok else "fail", "experiments/test_026_level3_multiclip", multiclip_notes),
        Level3ClosureCheck("no_tracked_heavy_files", "pass" if not has_heavy else "fail", "git ls-files", heavy_notes),
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
    status = "completado" if failed == 0 else "pendiente"
    lines = [
        "# Cierre Tecnico Nivel 3",
        "",
        "## Resultado",
        "",
        f"- Estado: `{status}`.",
        f"- Checks pass: `{passed}`.",
        f"- Checks fail: `{failed}`.",
        "- Alcance: cierre tecnico reproducible; documentacion final queda en Actividad 10.",
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
            "Nivel 3 queda tecnicamente completado y listo para documentacion final." if failed == 0 else "Nivel 3 aun no debe cerrarse hasta resolver checks fallidos.",
            "",
            "## Comandos",
            "",
            "```bash",
            "env MPLCONFIGDIR=/tmp/matplotlib .venv/bin/python -m unittest discover -s tests -q",
            ".venv/bin/python scripts/check_level3_readiness.py",
            ".venv/bin/python scripts/check_level3_closure.py",
            "```",
        ]
    )
    (output_dir / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Check whether Level 3 is technically closed.")
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
