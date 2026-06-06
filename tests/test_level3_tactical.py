from __future__ import annotations

from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from futbotmx.level3 import (
    TacticalConfig,
    aggregate_control_by_clip,
    aggregate_interaction_edges,
    build_interaction_graph,
    build_level3_metric_rows,
    compute_interactions,
    compute_spatial_control,
    grid_cells,
    spatial_control_for_frame,
)


def track(
    frame: int,
    track_id: str,
    class_name: str,
    x_norm: float,
    y_norm: float,
    confidence: float = 0.9,
    clip_id: str = "video_test",
) -> dict[str, object]:
    return {
        "clip_id": clip_id,
        "frame": frame,
        "time_sec": frame / 10,
        "track_id": track_id,
        "source_track_id": track_id,
        "class_name": class_name,
        "team": "neutral",
        "confidence": confidence,
        "x_norm": x_norm,
        "y_norm": y_norm,
        "zone": "middle_third",
        "calibration_status": "rectified",
        "calibration_confidence": 0.8,
        "track_quality": "usable",
    }


class Level3TacticalTests(unittest.TestCase):
    def test_grid_cells_cover_centers_and_tactical_zones(self) -> None:
        config = TacticalConfig(grid_x=2, grid_y=3)

        cells = grid_cells(config)

        self.assertEqual(len(cells), 6)
        self.assertAlmostEqual(float(cells[0]["x_norm"]), 0.25)
        self.assertAlmostEqual(float(cells[0]["y_norm"]), 1.0 / 6.0)
        self.assertEqual(cells[0]["zone"], "defensive_third")
        self.assertEqual(cells[2]["zone"], "middle_third")
        self.assertEqual(cells[4]["zone"], "attacking_third")

    def test_spatial_control_assigns_grid_cells_to_nearest_robot(self) -> None:
        config = TacticalConfig(grid_x=2, grid_y=1)
        rows = [
            track(10, "robot_left", "small_robot", 0.1, 0.5),
            track(10, "robot_right", "small_robot", 0.9, 0.5),
        ]

        control_rows, assignments, summary = spatial_control_for_frame("video_test", 10, rows, config)

        self.assertEqual(len(assignments), 2)
        self.assertEqual(summary["robot_count"], 2)
        self.assertAlmostEqual(summary["entropy"], 1.0)
        by_robot = {row["track_id"]: row for row in control_rows}
        self.assertAlmostEqual(by_robot["robot_left"]["control_percent"], 50.0)
        self.assertAlmostEqual(by_robot["robot_right"]["control_percent"], 50.0)
        self.assertEqual(by_robot["robot_left"]["control_mode"], "track_fallback")

    def test_interactions_detect_possession_pressure_and_graph_edges(self) -> None:
        config = TacticalConfig(
            grid_x=2,
            grid_y=2,
            possession_distance_norm=0.2,
            pressure_distance_norm=0.3,
            robot_interaction_distance_norm=0.25,
            dispute_distance_norm=0.3,
        )
        rows = []
        for frame in (10, 11):
            rows.extend(
                [
                    track(frame, "ball_01", "ball", 0.5, 0.5),
                    track(frame, "robot_owner", "small_robot", 0.55, 0.5),
                    track(frame, "robot_press", "small_robot", 0.7, 0.5),
                ]
            )

        interaction_samples, edge_events = compute_interactions(rows, config)
        edge_rows = aggregate_interaction_edges(edge_events, {"video_test": 10.0})
        graph = build_interaction_graph(rows, edge_rows, interaction_samples)

        sample_types = {sample["metric_type"] for sample in interaction_samples}
        self.assertIn("possession_candidate", sample_types)
        self.assertIn("pressure_candidate", sample_types)
        self.assertIn("robot_proximity", sample_types)
        self.assertTrue(any(edge["edge_type"] == "pressure_candidate" for edge in edge_rows))
        self.assertEqual(graph["summary"]["nodes"], 3)
        self.assertGreaterEqual(graph["summary"]["edges"], 3)

    def test_metric_rows_include_control_and_interaction_categories(self) -> None:
        config = TacticalConfig(grid_x=2, grid_y=2, source_tracks="synthetic_level3_tracks.csv")
        rows = []
        for frame in (10, 11):
            rows.extend(
                [
                    track(frame, "ball_01", "ball", 0.5, 0.5),
                    track(frame, "robot_owner", "small_robot", 0.55, 0.5),
                ]
            )
        control_rows, _, frame_summaries = compute_spatial_control(rows, config)
        control_aggregate = aggregate_control_by_clip(control_rows)
        interaction_samples, edge_events = compute_interactions(rows, config)
        edge_rows = aggregate_interaction_edges(edge_events, {"video_test": 10.0})

        metric_rows = build_level3_metric_rows(
            rows,
            control_rows,
            control_aggregate,
            frame_summaries,
            interaction_samples,
            edge_rows,
            config,
        )

        metric_names = {row["metric_name"] for row in metric_rows}
        categories = {row["metric_category"] for row in metric_rows}
        self.assertIn("mean_control_percent", metric_names)
        self.assertIn("mean_robot_ball_distance_norm", metric_names)
        self.assertIn("spatial_control", categories)
        self.assertIn("interaction", categories)


if __name__ == "__main__":
    unittest.main()
