from __future__ import annotations

from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from futbotmx.level3 import (
    TeamAssignmentConfig,
    apply_team_assignments,
    build_team_assignments,
    evaluate_assignment_strategies,
    robot_track_summaries,
)


def robot_row(frame: int, track_id: str, x_norm: float, clip_id: str = "clip") -> dict[str, object]:
    return {
        "clip_id": clip_id,
        "frame": frame,
        "time_sec": frame / 10,
        "track_id": track_id,
        "source_track_id": track_id,
        "class_name": "small_robot",
        "team": "neutral",
        "confidence": 0.9,
        "x_norm": x_norm,
        "y_norm": 0.5,
        "zone": "middle_third",
        "calibration_status": "rectified",
        "calibration_confidence": 0.8,
        "track_quality": "usable",
        "notes": "",
    }


class TeamAssignmentTests(unittest.TestCase):
    def test_side_fallback_assigns_left_and_right_teams(self) -> None:
        rows = [robot_row(10, "robot_left", 0.2), robot_row(10, "robot_right", 0.8)]
        config = TeamAssignmentConfig()
        summaries = robot_track_summaries(rows, config)

        assignments, validation = build_team_assignments(summaries, [], config)
        tracks_with_teams = apply_team_assignments(rows, assignments)

        by_track = {row["track_id"]: row for row in assignments}
        self.assertEqual(by_track["robot_left"]["team"], "team_left")
        self.assertEqual(by_track["robot_right"]["team"], "team_right")
        self.assertTrue(all(row["status"] == "pass" for row in validation))
        enriched = {row["track_id"]: row for row in tracks_with_teams}
        self.assertEqual(enriched["robot_left"]["team"], "team_left")

    def test_manual_assignment_validates_track_ids_and_overrides_fallback(self) -> None:
        rows = [robot_row(10, "robot_left", 0.2)]
        config = TeamAssignmentConfig()
        summaries = robot_track_summaries(rows, config)
        manual = [
            {"clip_id": "clip", "track_id": "robot_left", "team": "blue", "confidence": "0.95", "notes": "reviewed"},
            {"clip_id": "clip", "track_id": "missing", "team": "red", "confidence": "0.9"},
        ]

        assignments, validation = build_team_assignments(summaries, manual, config)

        self.assertEqual(assignments[0]["team"], "blue")
        self.assertEqual(assignments[0]["source"], "manual_by_id")
        self.assertTrue(any(row["status"] == "fail" and row["track_id"] == "missing" for row in validation))

    def test_strategy_evaluation_documents_color_unavailable(self) -> None:
        rows = [robot_row(10, "robot_left", 0.2)]
        config = TeamAssignmentConfig()
        summaries = robot_track_summaries(rows, config)

        strategies = evaluate_assignment_strategies(summaries, [], config)

        by_strategy = {row["strategy"]: row for row in strategies}
        self.assertEqual(by_strategy["dominant_color"]["status"], "not_available")
        self.assertEqual(by_strategy["initial_side_fallback"]["status"], "available")


if __name__ == "__main__":
    unittest.main()
