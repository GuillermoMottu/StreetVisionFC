from __future__ import annotations

from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from futbotmx.level3 import (
    ClipSpatialSpec,
    FieldModel,
    apply_homography_point,
    build_calibration_from_tracks,
    normalized_zone,
    rectify_track_rows,
    solve_homography,
    summarize_rectified_tracks,
)


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


if __name__ == "__main__":
    unittest.main()
