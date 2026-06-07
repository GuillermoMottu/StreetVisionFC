from __future__ import annotations

import argparse
from pathlib import Path
import sys
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from futbotmx.config import load_config, write_config_snapshot
from futbotmx.level3 import VideoOverlayConfig, build_video_overlay_package, video_overlay_config_to_dict


DEFAULT_OUTPUT_DIR = Path("experiments/test_037_activity19_video_overlay")


def write_config(config: dict[str, Any], output_dir: Path, overlay_config: VideoOverlayConfig) -> None:
    snapshot = dict(config)
    snapshot["activity19_video_overlay"] = {
        "rule_version": "activity19_video_overlay_v0.1",
        **video_overlay_config_to_dict(overlay_config),
        "policy": {
            "mp4_versioned": False,
            "heavy_inputs_versioned": False,
            "render_local_only": True,
        },
    }
    write_config_snapshot(snapshot, output_dir / "config.yaml")


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate Activity 19 lightweight overlay video evidence package.")
    parser.add_argument("--config", default="configs/default.yaml")
    parser.add_argument("--highlights", default="experiments/test_034_full_analysis/level3_events/level3_highlights.csv")
    parser.add_argument("--overlay-validation", default="experiments/test_034_full_analysis/level3_events/overlay_validation.csv")
    parser.add_argument("--advanced-events-dir", default="experiments/test_034_full_analysis/level3_events")
    parser.add_argument("--storyboard-manifest", default="experiments/test_034_full_analysis/level3_visualizations/highlight_storyboard_manifest.csv")
    parser.add_argument("--visualizations-dir", default="experiments/test_034_full_analysis/level3_visualizations")
    parser.add_argument("--experiment", default=DEFAULT_OUTPUT_DIR.as_posix())
    parser.add_argument("--local-mp4-path", default="local_outputs/activity19/video_595_overlay_clip.mp4")
    parser.add_argument("--segment-count", type=int, default=3)
    parser.add_argument("--segment-duration-sec", type=float, default=2.5)
    parser.add_argument("--min-confidence", type=float, default=0.8)
    args = parser.parse_args()

    output_dir = Path(args.experiment)
    overlay_config = VideoOverlayConfig(
        highlights_csv=args.highlights,
        overlay_validation_csv=args.overlay_validation,
        advanced_events_dir=args.advanced_events_dir,
        storyboard_manifest_csv=args.storyboard_manifest,
        visualizations_dir=args.visualizations_dir,
        output_dir=output_dir.as_posix(),
        local_mp4_path=args.local_mp4_path,
        segment_count=args.segment_count,
        segment_duration_sec=args.segment_duration_sec,
        min_confidence=args.min_confidence,
    )
    context = build_video_overlay_package(overlay_config)
    write_config(load_config(args.config), output_dir, overlay_config)
    print(
        "Wrote Activity 19 video overlay package to "
        f"{output_dir} ({len(context['segments'])} segments; MP4 local {args.local_mp4_path})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
