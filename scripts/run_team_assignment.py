from __future__ import annotations

import argparse
import copy
from pathlib import Path
import sys
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from futbotmx.artifact_names import TEAM_TRACKS_CSV
from futbotmx.config import load_config, write_config_snapshot
from futbotmx.level3 import (
    TEAM_ASSIGNMENT_RULE_VERSION,
    TeamAssignmentConfig,
    build_team_assignment_package,
    team_assignment_config_to_dict,
    write_team_assignment_json_summary,
)


DEFAULT_SOURCE_TRACKS = Path("experiments/test_020_spatial_model/spatial_tracks.csv")
DEFAULT_OUTPUT_DIR = Path("experiments/test_031_team_assignment")


def write_config(config: dict[str, Any], output_dir: Path, team_config: TeamAssignmentConfig) -> None:
    snapshot = copy.deepcopy(config)
    snapshot["team_assignment"] = {
        "rule_version": TEAM_ASSIGNMENT_RULE_VERSION,
        **team_assignment_config_to_dict(team_config),
        "outputs": [
            "team_assignment.csv",
            "team_assignment_validation.csv",
            "strategy_evaluation.csv",
            TEAM_TRACKS_CSV,
            "team_assignment_summary.json",
            "team_assignment_manifest.csv",
            "summary.md",
        ],
    }
    write_config_snapshot(snapshot, output_dir / "config.yaml")


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate approximate team assignments for spatial tracks.")
    parser.add_argument("--config", default="configs/default.yaml")
    parser.add_argument("--tracks", default=str(DEFAULT_SOURCE_TRACKS))
    parser.add_argument("--manual-assignment", default="")
    parser.add_argument("--experiment", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--fallback-split-axis", default="x_norm", choices=["x_norm", "y_norm"])
    parser.add_argument("--fallback-left-team", default="team_left")
    parser.add_argument("--fallback-right-team", default="team_right")
    parser.add_argument("--initial-window-frames", type=int, default=8)
    parser.add_argument("--min-side-spread-norm", type=float, default=0.12)
    args = parser.parse_args()

    output_dir = Path(args.experiment)
    team_config = TeamAssignmentConfig(
        tracks_csv=args.tracks,
        manual_assignment_csv=args.manual_assignment,
        output_dir=output_dir.as_posix(),
        fallback_split_axis=args.fallback_split_axis,
        fallback_left_team=args.fallback_left_team,
        fallback_right_team=args.fallback_right_team,
        initial_window_frames=args.initial_window_frames,
        min_side_spread_norm=args.min_side_spread_norm,
    )
    outputs = build_team_assignment_package(team_config)
    write_config(load_config(args.config), output_dir, team_config)
    write_team_assignment_json_summary(
        output_dir / "team_assignment_summary.json",
        outputs["assignments"],
        outputs["strategy_rows"],
    )
    print(
        "Wrote team assignment package to "
        f"{output_dir} ({len(outputs['assignments'])} robot tracks, {len(outputs['validation_rows'])} validation rows)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
