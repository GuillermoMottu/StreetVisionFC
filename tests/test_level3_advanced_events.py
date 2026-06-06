from __future__ import annotations

from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from futbotmx.level3 import (
    AdvancedEventsConfig,
    ball_speed_segments,
    build_highlight_events,
    build_pass_chain_events,
    possession_segments,
)


def ball_row(frame: int, x_norm: float, y_norm: float = 0.5, clip_id: str = "video_test") -> dict[str, object]:
    return {
        "clip_id": clip_id,
        "frame": frame,
        "time_sec": frame / 10,
        "track_id": "ball_01",
        "class_name": "ball",
        "team": "neutral",
        "x_norm": x_norm,
        "y_norm": y_norm,
        "zone": "middle_third",
        "confidence": 0.9,
        "calibration_confidence": 0.8,
        "calibration_status": "rectified",
        "track_quality": "usable",
    }


def robot_row(track_id: str, team: str = "ally", clip_id: str = "video_test") -> dict[str, object]:
    return {
        "clip_id": clip_id,
        "frame": 10,
        "time_sec": 1.0,
        "track_id": track_id,
        "class_name": "small_robot",
        "team": team,
        "x_norm": 0.5,
        "y_norm": 0.5,
        "zone": "middle_third",
        "confidence": 0.9,
        "calibration_confidence": 0.8,
        "calibration_status": "rectified",
        "track_quality": "usable",
    }


class Level3AdvancedEventsTests(unittest.TestCase):
    def test_ball_speed_segments_use_normalized_distance_and_time(self) -> None:
        rows = [ball_row(10, 0.1), ball_row(11, 0.2)]

        segments = ball_speed_segments(rows)

        self.assertEqual(len(segments), 1)
        self.assertEqual(segments[0]["frame_start"], 10)
        self.assertAlmostEqual(segments[0]["distance_norm"], 0.1)
        self.assertAlmostEqual(segments[0]["speed_norm_per_sec"], 1.0)

    def test_pass_chain_marks_same_team_owner_change(self) -> None:
        config = AdvancedEventsConfig(max_pass_gap_frames=4)
        interactions = [
            possession_sample(10, "robot_a"),
            possession_sample(11, "robot_a"),
            possession_sample(12, "robot_b"),
            possession_sample(13, "robot_b"),
        ]
        possessions = possession_segments(interactions, config)
        tracks = [robot_row("robot_a", "ally"), robot_row("robot_b", "ally")]

        events = build_pass_chain_events(possessions, tracks, config)

        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["event_type"], "pass_chain")
        self.assertEqual(events[0]["event_subtype"], "same_team_chain")
        self.assertEqual(events[0]["reliability"], "provisional")
        self.assertEqual(events[0]["primary_object_id"], "robot_a")
        self.assertEqual(events[0]["secondary_object_ids"], ["robot_b"])

    def test_pass_chain_is_doubtful_without_team_assignment(self) -> None:
        config = AdvancedEventsConfig(max_pass_gap_frames=4)
        interactions = [possession_sample(10, "robot_a"), possession_sample(11, "robot_a")]
        possessions = possession_segments(interactions, config)
        tracks = [robot_row("robot_a", "neutral")]

        events = build_pass_chain_events(possessions, tracks, config)

        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["event_subtype"], "dudoso_sin_equipo")
        self.assertIn("falta equipo confiable", events[0]["narrative"])

    def test_highlight_scoring_combines_speed_interaction_and_level2_support(self) -> None:
        config = AdvancedEventsConfig(ball_speed_reference_norm_per_sec=0.5)
        speed_segments = [
            {
                "clip_id": "video_test",
                "ball_id": "ball_01",
                "frame_start": 10,
                "frame_end": 11,
                "time_start_sec": 1.0,
                "time_end_sec": 1.1,
                "speed_norm_per_sec": 0.5,
                "distance_norm": 0.05,
                "zone": "defensive_third",
                "position_start": {"x_norm": 0.5, "y_norm": 0.2},
                "position_end": {"x_norm": 0.55, "y_norm": 0.2},
                "confidence": 0.8,
            }
        ]
        interactions = [
            possession_sample(10, "robot_a"),
            {
                **possession_sample(10, "robot_b"),
                "metric_type": "pressure_candidate",
                "secondary_track_id": "robot_a",
            },
        ]
        level2_events = {"video_test": [{"event_id": "lvl2_evt_000001", "frame_start": 10, "frame_end": 11}]}

        events, highlights = build_highlight_events([], speed_segments, interactions, [], level2_events, config, start_index=1)

        self.assertEqual(len(events), 1)
        self.assertEqual(highlights[0]["rank"], 1)
        self.assertGreater(highlights[0]["score"], 80)
        self.assertIn("presion_o_disputa", highlights[0]["reason"])
        self.assertIn("lvl2_evt_000001", highlights[0]["source_event_ids"])


def possession_sample(frame: int, robot_id: str) -> dict[str, str]:
    return {
        "clip_id": "video_test",
        "frame": str(frame),
        "time_sec": str(frame / 10),
        "metric_type": "possession_candidate",
        "primary_track_id": robot_id,
        "secondary_track_id": "ball_01",
        "distance_norm": "0.1",
        "zone": "middle_third",
        "confidence": "0.75",
        "reliability": "provisional",
        "notes": "synthetic",
    }


if __name__ == "__main__":
    unittest.main()
