from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from futbotmx.events import detect_level1_events
from futbotmx.io.detections import (
    Detection,
    FrameDetections,
    filter_detections_by_roi,
    load_detections,
    save_detections,
)
from futbotmx.tracking import track_detections, write_tracks_csv
from futbotmx.visualization import write_heatmap
from scripts.run_temporal_stability import (
    count_detections_by_frame,
    representative_frames,
    select_frames,
)


def synthetic_detections() -> list[FrameDetections]:
    frames: list[FrameDetections] = []
    for frame in range(12):
        frames.append(
            FrameDetections(
                frame=frame,
                detections=(
                    Detection("ball", (40 + frame, 40, 50 + frame, 50), (45 + frame, 45), 0.9),
                    Detection("ally_robot", (20 + frame, 30, 42 + frame, 60), (31 + frame, 45), 0.85),
                    Detection("opponent_robot", (120, 30, 145, 60), (132, 45), 0.8),
                ),
            )
        )
    return frames


class PipelineUnitTests(unittest.TestCase):
    def test_detection_roundtrip(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "detections.json"
            save_detections(synthetic_detections(), path)

            loaded = load_detections(path)

            self.assertEqual(len(loaded), 12)
            self.assertEqual(loaded[0].detections[0].class_name, "ball")

    def test_filter_detections_by_roi(self) -> None:
        frames = [
            FrameDetections(
                frame=1,
                detections=(
                    Detection("ball", (10, 10, 20, 20), (15, 15), 0.9),
                    Detection("robot", (80, 80, 120, 120), (100, 100), 0.8),
                ),
            )
        ]

        filtered = filter_detections_by_roi(frames, roi=(0, 0, 50, 50))

        self.assertEqual(len(filtered), 1)
        self.assertEqual(len(filtered[0].detections), 1)
        self.assertEqual(filtered[0].detections[0].class_name, "ball")

    def test_temporal_stability_frame_selection(self) -> None:
        self.assertEqual(select_frames(120, 130, 5), [120, 125, 130])
        self.assertEqual(representative_frames([120, 125, 130, 135, 140]), [120, 130, 140])

    def test_temporal_stability_counts_by_frame(self) -> None:
        raw_frames = [
            FrameDetections(
                frame=1,
                detections=(
                    Detection("ball", (10, 10, 20, 20), (15, 15), 0.9),
                    Detection("robot", (80, 80, 120, 120), (100, 100), 0.8),
                ),
            ),
            FrameDetections(
                frame=2,
                detections=(Detection("robot", (80, 80, 120, 120), (100, 100), 0.8),),
            ),
        ]
        filtered_frames = [
            FrameDetections(
                frame=1,
                detections=(Detection("ball", (10, 10, 20, 20), (15, 15), 0.9),),
            ),
            FrameDetections(frame=2, detections=()),
        ]

        rows = count_detections_by_frame(raw_frames, filtered_frames, ["ball", "robot"])

        self.assertEqual(rows[0]["raw_total"], 2)
        self.assertEqual(rows[0]["filtered_ball"], 1)
        self.assertEqual(rows[0]["filtered_robot"], 0)
        self.assertEqual(rows[1]["filtered_ball"], 0)

    def test_tracking_events_and_heatmap(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tracks_path = Path(tmp) / "tracks.csv"
            heatmap_path = Path(tmp) / "heatmap.png"
            rows = track_detections(synthetic_detections(), max_distance_px=50)
            write_tracks_csv(rows, tracks_path)

            events = detect_level1_events(
                tracks_path,
                fps=15,
                field_width=160,
                field_height=90,
                config={
                    "rule_version": "events_v0.1",
                    "possession_distance_px": 25,
                    "possession_min_frames": 3,
                    "collision_distance_px": 10,
                    "collision_min_frames": 3,
                    "shot_min_ball_speed_px_per_sec": 999,
                },
            )
            write_heatmap(tracks_path, heatmap_path, width=160, height=90)

            self.assertTrue(tracks_path.exists())
            self.assertTrue(heatmap_path.exists())
            self.assertTrue(any(event["event_type"] == "possession" for event in events))
            self.assertTrue(any(event["event_type"] == "activity_zone" for event in events))


if __name__ == "__main__":
    unittest.main()
