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
    bbox_iou,
    deduplicate_detections,
    filter_detections_by_roi,
    load_detections,
    save_detections,
)
from futbotmx.tracking import TrackRow, track_detections, write_tracks_csv
from futbotmx.visualization import write_heatmap
from scripts.run_prompt_comparison import (
    choose_prompt,
    slugify_prompt,
    summarize_prompt,
)
from scripts.run_sam3_benchmark import parse_float, parse_nvidia_smi_row
from scripts.run_level1_validation_report import ratio_status
from scripts.build_level1_evidence_package import mib
from scripts.clean_detections import parse_top_k
from scripts.run_event_validation import ball_speed_rows, nearest_robot_rows
from scripts.run_tracking_comparison import (
    choose_recommended_tracker,
    summarize_tracks,
)
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

    def test_deduplicate_detections_applies_nms_and_top_k(self) -> None:
        frames = [
            FrameDetections(
                frame=1,
                detections=(
                    Detection("ball", (10, 10, 20, 20), (15, 15), 0.9),
                    Detection("ball", (11, 11, 21, 21), (16, 16), 0.8),
                    Detection("ball", (80, 80, 90, 90), (85, 85), 0.7),
                    Detection("small_robot", (30, 30, 60, 60), (45, 45), 0.9),
                ),
            )
        ]

        cleaned = deduplicate_detections(frames, iou_threshold=0.5, top_k_by_class={"ball": 1})

        self.assertGreater(bbox_iou(frames[0].detections[0].bbox, frames[0].detections[1].bbox), 0.5)
        self.assertEqual(parse_top_k(["ball=1", "small_robot=3"]), {"ball": 1, "small_robot": 3})
        self.assertEqual(len(cleaned[0].detections), 2)
        self.assertEqual(sum(1 for item in cleaned[0].detections if item.class_name == "ball"), 1)
        self.assertEqual(cleaned[0].detections[0].class_name, "ball")

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

    def test_prompt_comparison_helpers(self) -> None:
        raw_frames = [
            FrameDetections(
                frame=120,
                detections=(Detection("small_orange_ball", (1, 1, 4, 4), (2.5, 2.5), 0.8),),
            ),
            FrameDetections(frame=135, detections=()),
        ]
        filtered_frames = [
            FrameDetections(
                frame=120,
                detections=(Detection("small_orange_ball", (1, 1, 4, 4), (2.5, 2.5), 0.8),),
            ),
            FrameDetections(frame=135, detections=()),
        ]

        summary = summarize_prompt("ball", "small orange ball", raw_frames, filtered_frames)

        self.assertEqual(slugify_prompt("Small Orange Ball!"), "small_orange_ball")
        self.assertEqual(summary.detected_frames_filtered, 1)
        self.assertEqual(summary.missing_frames_filtered, (135,))
        self.assertEqual(choose_prompt("ball", [summary]).prompt, "small orange ball")

    def test_tracking_comparison_metrics(self) -> None:
        rows = [
            TrackRow(1, "ball_01", "ball", 10, 10, 8, 8, 12, 12, 0.9),
            TrackRow(2, "ball_01", "ball", 13, 14, 11, 12, 15, 16, 0.9),
            TrackRow(4, "ball_02", "ball", 30, 30, 28, 28, 32, 32, 0.8),
        ]

        metrics = summarize_tracks("simple", rows)

        self.assertEqual(metrics[0].class_name, "ball")
        self.assertEqual(metrics[0].track_count, 2)
        self.assertEqual(metrics[0].late_track_starts, 1)
        self.assertEqual(metrics[0].max_frame_gap, 1)
        self.assertEqual(choose_recommended_tracker(metrics), "simple")

    def test_event_validation_diagnostics(self) -> None:
        rows = [
            {"frame": 1, "track_id": "ball_01", "class_name": "ball", "x": 10.0, "y": 10.0},
            {"frame": 1, "track_id": "robot_01", "class_name": "robot", "x": 13.0, "y": 14.0},
            {"frame": 2, "track_id": "ball_01", "class_name": "ball", "x": 16.0, "y": 18.0},
            {"frame": 2, "track_id": "robot_01", "class_name": "robot", "x": 18.0, "y": 18.0},
        ]

        nearest = nearest_robot_rows(rows)
        speeds = ball_speed_rows(rows, fps=10, field_width=20)

        self.assertEqual(nearest[0]["nearest_robot_id"], "robot_01")
        self.assertAlmostEqual(nearest[0]["distance_px"], 5.0)
        self.assertAlmostEqual(speeds[0]["speed_px_per_sec"], 100.0)
        self.assertTrue(speeds[0]["moving_toward_goal"])

    def test_sam3_benchmark_parses_nvidia_smi_output(self) -> None:
        snapshot = parse_nvidia_smi_row("NVIDIA GeForce RTX 4050 Laptop GPU, 595.71.05, 6141, 4230, 51, 28.47")

        self.assertEqual(snapshot.name, "NVIDIA GeForce RTX 4050 Laptop GPU")
        self.assertEqual(snapshot.driver_version, "595.71.05")
        self.assertEqual(snapshot.memory_total_mb, 6141)
        self.assertEqual(snapshot.memory_used_mb, 4230)
        self.assertEqual(snapshot.temperature_c, 51)
        self.assertEqual(snapshot.power_draw_w, 28.47)
        self.assertIsNone(parse_float("N/A"))

    def test_level1_validation_helpers(self) -> None:
        self.assertEqual(ratio_status(59, 61, pass_ratio=0.95), "pass")
        self.assertEqual(ratio_status(50, 61, pass_ratio=0.95), "warn")
        self.assertEqual(ratio_status(10, 61, pass_ratio=0.95), "fail")
        self.assertEqual(ratio_status(1, 0, pass_ratio=0.95), "fail")

    def test_level1_evidence_size_formatting(self) -> None:
        self.assertEqual(mib(0), "0.00")
        self.assertEqual(mib(1024 * 1024), "1.00")

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
            self.assertEqual(events[0]["evidence"]["tracks_file"], "tracks.csv")


if __name__ == "__main__":
    unittest.main()
