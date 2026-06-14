"""
Unified pipeline validation script.

Checks all pipeline components are present, importable, and functional
without requiring GPU or video files. Exits 0 if all checks pass.

Usage:
    python scripts/validate_pipeline.py
"""
from __future__ import annotations

import sys
import subprocess
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / "src"))

PASS = "[PASS]"
FAIL = "[FAIL]"
WARN = "[WARN]"


def check(label: str, fn):
    try:
        result = fn()
        status = WARN if result is False else PASS
        print(f"  {status} {label}")
        return result is not False
    except Exception as e:
        print(f"  {FAIL} {label}: {e}")
        return False


def main():
    failures = []

    print("\n=== FutBotMX Pipeline Validation ===\n")

    # ── 1. Config ─────────────────────────────────────────────────────────────
    print("1. Configuration")

    def config_loads():
        from futbotmx.config import load_config
        cfg = load_config(str(ROOT / "configs" / "default.yaml"))
        assert cfg is not None
        assert cfg["segmentation"]["provider"] == "grounded_sam"

    if not check("configs/default.yaml loads, provider=grounded_sam", config_loads):
        failures.append("config")

    # ── 2. Core imports ───────────────────────────────────────────────────────
    print("\n2. Core imports")

    def import_segmentation():
        from futbotmx.segmentation import (
            SAM3Segmenter, SAM3UnavailableError,
            OWLv2Detector, OWLv2UnavailableError,
            GroundedSAMSegmenter,
            detect_goalposts, detect_goalposts_with_mask,
        )

    if not check("futbotmx.segmentation (all classes)", import_segmentation):
        failures.append("imports:segmentation")

    def import_io():
        from futbotmx.io.detections import Detection, FrameDetections

    if not check("futbotmx.io.detections", import_io):
        failures.append("imports:io")

    # ── 3. Checkpoint files ───────────────────────────────────────────────────
    print("\n3. Checkpoint files")

    sam3_path = ROOT / "checkpoints" / "sam3" / "sam3.pt"
    if not check(f"SAM3 checkpoint ({sam3_path.stat().st_size // 1_000_000} MB)",
                 lambda: sam3_path.exists()):
        failures.append("checkpoint:sam3")

    owlv2_path = ROOT / "checkpoints" / "owlv2-base"
    if not check(f"OWLv2 checkpoint dir present",
                 lambda: owlv2_path.is_dir() and any(owlv2_path.iterdir())):
        failures.append("checkpoint:owlv2")

    # ── 4. Key artefact files ─────────────────────────────────────────────────
    print("\n4. Evaluation artefacts")

    artefacts = {
        "ByteTrack tracks with teams":
            "experiments/current_evaluation/phase4_team_assignment/tracks_bytetrack_with_teams.csv",
        "Benchmark summary":
            "experiments/current_evaluation/phase5_metrics/benchmark_summary.json",
        "Annotation template":
            "data/annotations/annotation_template.json",
        "Demo video (H.264)":
            "outputs/videos/futbotmx_demo_h264.mp4",
        "SAM3 masks dir":
            "experiments/current_evaluation/masks",
        "Grounded-SAM masks dir":
            "experiments/current_evaluation/masks_grounded_sam",
    }

    for label, rel_path in artefacts.items():
        path = ROOT / rel_path
        if not check(label, lambda p=path: p.exists()):
            failures.append(f"artefact:{rel_path}")

    # ── 5. Goalpost fallback ──────────────────────────────────────────────────
    print("\n5. Goalpost fallback (no GPU)")

    def goalpost_fallback():
        from futbotmx.segmentation.goalpost_fallback import detect_goalposts, _CLIP_GOALS
        assert set(_CLIP_GOALS.keys()) == {"video_836", "video_480", "video_595", "video_667"}
        fd = detect_goalposts(frame_index=143, clip_id="video_836")
        assert len(fd.detections) == 1
        assert fd.detections[0].class_name == "goalpost"

    if not check("detect_goalposts() for all 4 clips", goalpost_fallback):
        failures.append("goalpost_fallback")

    # ── 6. Team assignment round-trip ─────────────────────────────────────────
    print("\n6. Team assignment")

    def team_csv():
        import pandas as pd
        df = pd.read_csv(ROOT / "experiments/current_evaluation/phase4_team_assignment/tracks_bytetrack_with_teams.csv")
        assert "team" in df.columns
        non_neutral = df[df["team"].isin(["team_left", "team_right"])]
        assert len(non_neutral) > 0
        return True

    if not check("tracks_bytetrack_with_teams.csv has team column, non-neutral rows", team_csv):
        failures.append("team_csv")

    # ── 7. Test suite ─────────────────────────────────────────────────────────
    print("\n7. Test suite")

    result = subprocess.run(
        [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-q"],
        cwd=ROOT, capture_output=True, text=True
    )
    test_line = (result.stderr or result.stdout).strip().split("\n")[-1]
    if result.returncode == 0:
        print(f"  {PASS} {test_line}")
    else:
        print(f"  {FAIL} Test suite failed: {test_line}")
        failures.append("test_suite")

    # ── Summary ───────────────────────────────────────────────────────────────
    print(f"\n{'='*40}")
    if not failures:
        print(f"{PASS} All checks passed.")
        sys.exit(0)
    else:
        print(f"{FAIL} {len(failures)} check(s) failed: {', '.join(failures)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
