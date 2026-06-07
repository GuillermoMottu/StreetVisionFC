from __future__ import annotations

import argparse
import copy
from pathlib import Path
import sys
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from futbotmx.config import load_config, write_config_snapshot
from futbotmx.level3 import (
    HIGHLIGHT_REVIEW_RULE_VERSION,
    HighlightReviewConfig,
    build_highlight_review_package,
    highlight_review_config_to_dict,
)


DEFAULT_OUTPUT_DIR = Path("experiments/test_035_human_review")


def write_config(config: dict[str, Any], output_dir: Path, review_config: HighlightReviewConfig) -> None:
    snapshot = copy.deepcopy(config)
    snapshot["highlight_human_review"] = {
        "rule_version": HIGHLIGHT_REVIEW_RULE_VERSION,
        "format": "static_html_plus_editable_csv",
        "review_statuses": ["confiable", "provisional", "descartado"],
        **highlight_review_config_to_dict(review_config),
        "outputs": [
            "human_review_panel.html",
            "human_review.csv",
            "human_review_validation.csv",
            "human_review_manifest.csv",
            "config.yaml",
            "summary.md",
        ],
    }
    write_config_snapshot(snapshot, output_dir / "config.yaml")


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate the Level 3 human review panel for ranked highlights.")
    parser.add_argument("--config", default="configs/default.yaml")
    parser.add_argument("--experiment", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--highlights", default="experiments/test_022_level3_advanced_events/level3_highlights.csv")
    parser.add_argument("--events", default="experiments/test_022_level3_advanced_events/level3_events.json")
    parser.add_argument("--overlay-validation", default="experiments/test_022_level3_advanced_events/overlay_validation.csv")
    parser.add_argument("--advanced-events-dir", default="experiments/test_022_level3_advanced_events")
    parser.add_argument("--visualization-manifest", default="experiments/test_023_level3_visualizations/visualization_manifest.csv")
    parser.add_argument("--storyboard-manifest", default="experiments/test_023_level3_visualizations/highlight_storyboard_manifest.csv")
    parser.add_argument("--visualizations-dir", default="experiments/test_023_level3_visualizations")
    parser.add_argument("--reviewer", default="human_reviewer")
    parser.add_argument("--reviewed-at", default="")
    parser.add_argument("--top-highlights", type=int, default=6)
    args = parser.parse_args()

    review_config = HighlightReviewConfig(
        highlights_csv=args.highlights,
        events_json=args.events,
        overlay_validation_csv=args.overlay_validation,
        advanced_events_dir=args.advanced_events_dir,
        visualization_manifest_csv=args.visualization_manifest,
        storyboard_manifest_csv=args.storyboard_manifest,
        visualizations_dir=args.visualizations_dir,
        output_dir=args.experiment,
        reviewer=args.reviewer,
        reviewed_at=args.reviewed_at,
        top_highlights=args.top_highlights,
    )
    context = build_highlight_review_package(review_config)
    write_config(load_config(args.config), Path(args.experiment), review_config)
    print(
        "Wrote highlight review panel to "
        f"{args.experiment} ({len(context['review_rows'])} rows, {context['status_counts']})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
