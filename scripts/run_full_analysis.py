from __future__ import annotations

import argparse
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from futbotmx.full_analysis import DEFAULT_CACHE_DIR, FullAnalysisRequest, next_experiment_dir, run_full_analysis


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the FutBotMX full local analysis pipeline for one clip.")
    parser.add_argument("--config", default="configs/default.yaml")
    parser.add_argument("--video", required=True)
    parser.add_argument("--clip-id", required=True)
    parser.add_argument("--start-frame", type=int, required=True)
    parser.add_argument("--end-frame", type=int, required=True)
    parser.add_argument("--experiment", default="")
    parser.add_argument("--detections", default="", help="Optional normalized detections JSON produced by SAM 3 on the GPU laptop.")
    parser.add_argument("--tracks", default="", help="Optional precomputed tracks CSV to reuse.")
    parser.add_argument("--context-root", default="experiments/test_017_level2_closure", help="Optional root with historical/reference tracks and contextual event artifacts.")
    parser.add_argument("--level2-root", dest="context_root", help=argparse.SUPPRESS)
    parser.add_argument("--calibration-json", default="")
    parser.add_argument("--manual-assignment", default="", help="Optional human-reviewed team assignment CSV.")
    parser.add_argument("--top-highlights", type=int, default=4)
    parser.add_argument("--segment-count", type=int, default=4)
    parser.add_argument("--cache-dir", default=DEFAULT_CACHE_DIR.as_posix(), help="Local cache directory for reusable lightweight artifacts.")
    parser.add_argument("--force", action="store_true", help="Recompute stages and refresh matching cache entries instead of restoring them.")
    args = parser.parse_args()

    root = Path.cwd()
    experiment = args.experiment or next_experiment_dir(root, args.clip_id, args.start_frame, args.end_frame).as_posix()
    request = FullAnalysisRequest(
        video=args.video,
        clip_id=args.clip_id,
        start_frame=args.start_frame,
        end_frame=args.end_frame,
        config_path=args.config,
        experiment_dir=experiment,
        detections=args.detections,
        tracks=args.tracks,
        level2_root=args.context_root,
        calibration_json=args.calibration_json,
        manual_assignment=args.manual_assignment,
        top_highlights=args.top_highlights,
        segment_count=args.segment_count,
        cache_dir=args.cache_dir,
        force=args.force,
    )
    result = run_full_analysis(root, request)
    print(
        "Wrote full analysis pipeline to "
        f"{result.experiment_dir} ({result.status}; {len(result.stages)} stages, manifest {result.manifest_path})"
    )
    return 0 if result.status == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
