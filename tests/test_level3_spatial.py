from __future__ import annotations

import csv
from pathlib import Path
import sys
import tempfile
import unittest

import matplotlib

matplotlib.use("Agg")

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from futbotmx.level3 import (
    ClipSpatialSpec,
    compare_calibrations,
    estimate_manual_calibration_confidence,
    FieldModel,
    apply_homography_point,
    build_calibration_from_tracks,
    normalized_zone,
    rectify_track_rows,
    solve_homography,
    summarize_rectified_tracks,
)
from run_level3_spatial_model import run_spatial_model_from_tracks


class Level3SpatialTests(unittest.TestCase):
    def test_homography_maps_image_rectangle_to_normalized_field(self) -> None:
        image_points = ((10.0, 20.0), (110.0, 20.0), (110.0, 220.0), (10.0, 220.0))
        field_points = ((0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0))

        homography = solve_homography(image_points, field_points)

        for source, expected in zip(image_points, field_points):
            actual = apply_homography_point(homography, *source)
            self.assertAlmostEqual(actual[0], expected[0], places=6)
            self.assertAlmostEqual(actual[1], expected[1], places=6)
        center = apply_homography_point(homography, 60.0, 120.0)
        self.assertAlmostEqual(center[0], 0.5, places=6)
        self.assertAlmostEqual(center[1], 0.5, places=6)

    def test_rectification_preserves_identity_and_assigns_zone(self) -> None:
        rows = [
            {
                "frame": 10,
                "track_id": "green_soccer_field_bt_01",
                "class_name": "green_soccer_field",
                "x": 60.0,
                "y": 120.0,
                "bbox_x1": 10.0,
                "bbox_y1": 20.0,
                "bbox_x2": 110.0,
                "bbox_y2": 220.0,
                "confidence": 0.9,
                "team": "neutral",
            },
            {
                "frame": 10,
                "track_id": "ball_bt_01",
                "class_name": "ball",
                "x": 60.0,
                "y": 120.0,
                "bbox_x1": 58.0,
                "bbox_y1": 118.0,
                "bbox_x2": 62.0,
                "bbox_y2": 122.0,
                "confidence": 0.85,
                "team": "neutral",
            },
        ]
        spec = ClipSpatialSpec("video_test", width=120, height=240, fps=10)
        calibration = build_calibration_from_tracks("video_test", rows, spec, min_field_confidence=0.5, min_field_coverage=0.2)

        rectified = rectify_track_rows("video_test", rows, spec, calibration, FieldModel())
        ball = [row for row in rectified if row["track_id"] == "ball_bt_01"][0]

        self.assertEqual(ball["clip_id"], "video_test")
        self.assertEqual(ball["source_track_id"], "ball_bt_01")
        self.assertEqual(ball["frame"], 10)
        self.assertAlmostEqual(ball["time_sec"], 1.0)
        self.assertAlmostEqual(ball["x_norm"], 0.5)
        self.assertAlmostEqual(ball["y_norm"], 0.5)
        self.assertEqual(ball["zone"], "middle_third")
        self.assertEqual(ball["calibration_status"], "rectified")
        self.assertEqual(ball["track_quality"], "usable")

    def test_calibration_fallback_when_field_bbox_is_missing(self) -> None:
        rows = [
            {
                "frame": 3,
                "track_id": "ball_bt_01",
                "class_name": "ball",
                "x": 20.0,
                "y": 80.0,
                "bbox_x1": 18.0,
                "bbox_y1": 78.0,
                "bbox_x2": 22.0,
                "bbox_y2": 82.0,
                "confidence": 0.8,
                "team": "neutral",
            }
        ]
        spec = ClipSpatialSpec("video_fallback", width=100, height=200, fps=10)
        calibration = build_calibration_from_tracks("video_fallback", rows, spec)

        rectified = rectify_track_rows("video_fallback", rows, spec, calibration)
        summary = summarize_rectified_tracks(rectified, {"video_fallback": calibration})[0]

        self.assertEqual(calibration.status, "fallback")
        self.assertEqual(rectified[0]["calibration_status"], "fallback_image_normalized")
        self.assertAlmostEqual(rectified[0]["x_norm"], 0.2)
        self.assertAlmostEqual(rectified[0]["y_norm"], 0.4)
        self.assertEqual(normalized_zone(0.2, 0.4), "middle_third")
        self.assertEqual(summary["fallback_rows"], 1)

    def test_manual_calibration_confidence_and_comparison(self) -> None:
        spec = ClipSpatialSpec("video_manual", width=200, height=300, fps=10)
        auto = build_calibration_from_tracks(
            "video_manual",
            [
                {
                    "frame": 1,
                    "track_id": "field",
                    "class_name": "green_soccer_field",
                    "x": 100.0,
                    "y": 150.0,
                    "bbox_x1": 20.0,
                    "bbox_y1": 30.0,
                    "bbox_x2": 180.0,
                    "bbox_y2": 270.0,
                    "confidence": 0.9,
                }
            ],
            spec,
            min_field_confidence=0.5,
            min_field_coverage=0.2,
        )
        manual = build_calibration_from_tracks(
            "video_manual",
            [
                {
                    "frame": 1,
                    "track_id": "field",
                    "class_name": "green_soccer_field",
                    "x": 100.0,
                    "y": 150.0,
                    "bbox_x1": 25.0,
                    "bbox_y1": 35.0,
                    "bbox_x2": 175.0,
                    "bbox_y2": 265.0,
                    "confidence": 0.9,
                }
            ],
            spec,
            min_field_confidence=0.5,
            min_field_coverage=0.2,
        )

        confidence = estimate_manual_calibration_confidence(manual.image_points, spec, min_field_coverage=0.2)
        comparison = compare_calibrations({"video_manual": auto}, {"video_manual": manual}, {"video_manual"})

        self.assertGreater(confidence, 0.7)
        self.assertEqual(comparison[0]["method_used"], "manual")
        self.assertGreater(float(comparison[0]["corner_mean_delta_px"]), 0.0)

    def test_spatial_model_can_rectify_direct_current_tracks(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config = root / "config.yaml"
            tracks = root / "tracks.csv"
            output = root / "spatial"
            config.write_text("level2_events:\n  zone_axis: y\n", encoding="utf-8")
            with tracks.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(
                    handle,
                    fieldnames=["frame", "track_id", "class_name", "x", "y", "bbox_x1", "bbox_y1", "bbox_x2", "bbox_y2", "confidence", "team"],
                    lineterminator="\n",
                )
                writer.writeheader()
                writer.writerows(
                    [
                        {"frame": 10, "track_id": "field_01", "class_name": "green_soccer_field", "x": 60, "y": 120, "bbox_x1": 10, "bbox_y1": 20, "bbox_x2": 110, "bbox_y2": 220, "confidence": 0.9, "team": "neutral"},
                        {"frame": 10, "track_id": "ball_01", "class_name": "ball", "x": 60, "y": 120, "bbox_x1": 58, "bbox_y1": 118, "bbox_x2": 62, "bbox_y2": 122, "confidence": 0.9, "team": "neutral"},
                        {"frame": 10, "track_id": "robot_01", "class_name": "small_robot", "x": 70, "y": 130, "bbox_x1": 65, "bbox_y1": 125, "bbox_x2": 75, "bbox_y2": 135, "confidence": 0.8, "team": "neutral"},
                    ]
                )

            validation = run_spatial_model_from_tracks(
                config,
                tracks,
                output,
                "video_current",
                fps=10.0,
                width=120,
                height=240,
                min_field_confidence=0.5,
                min_field_coverage=0.2,
            )

            rows = list(csv.DictReader((output / "level3_tracks.csv").open("r", newline="", encoding="utf-8")))
            calibration_exists = (output / "field_calibration.json").exists()

        self.assertEqual(validation[0]["clip_id"], "video_current")
        self.assertTrue(calibration_exists)
        self.assertTrue(any(row["track_id"] == "ball_01" and row["calibration_status"] == "rectified" for row in rows))


if __name__ == "__main__":
    unittest.main()
