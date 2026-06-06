from __future__ import annotations

import csv
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest

import matplotlib

matplotlib.use("Agg")

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from futbotmx.level3 import (
    Level3VisualizationConfig,
    draw_minimap_highlight,
    draw_voronoi_minimap,
    find_level2_overlay,
    write_visualization_manifest,
)


def track(frame: int, track_id: str, class_name: str, x_norm: float, y_norm: float) -> dict[str, object]:
    return {
        "clip_id": "video_test",
        "frame": frame,
        "time_sec": frame / 10,
        "track_id": track_id,
        "source_track_id": track_id,
        "class_name": class_name,
        "team": "neutral",
        "confidence": 0.9,
        "x_norm": x_norm,
        "y_norm": y_norm,
        "zone": "middle_third",
        "calibration_status": "rectified",
        "calibration_confidence": 0.8,
        "track_quality": "usable",
    }


class Level3VisualizationTests(unittest.TestCase):
    def test_find_level2_overlay_prefers_exact_then_nearest_lightweight_frame(self) -> None:
        with TemporaryDirectory() as tmpdir:
            clip_dir = Path(tmpdir) / "video_test"
            clip_dir.mkdir()
            exact = clip_dir / "overlay_evt_a_frame_120.png"
            near = clip_dir / "overlay_evt_b_frame_127.png"
            far = clip_dir / "overlay_evt_c_frame_180.png"
            for path in (exact, near, far):
                path.touch()

            self.assertEqual(find_level2_overlay(tmpdir, "video_test", 120), exact)
            self.assertEqual(find_level2_overlay(tmpdir, "video_test", 125), near)
            self.assertIsNone(find_level2_overlay(tmpdir, "video_test", 160))

    def test_draw_voronoi_minimap_creates_png_from_rectified_tracks(self) -> None:
        rows = [
            track(10, "robot_left", "small_robot", 0.1, 0.5),
            track(10, "robot_right", "small_robot", 0.9, 0.5),
            track(10, "ball_01", "ball", 0.48, 0.5),
        ]
        config = Level3VisualizationConfig(grid_x=2, grid_y=1)
        with TemporaryDirectory() as tmpdir:
            output = Path(tmpdir) / "voronoi.png"

            result = draw_voronoi_minimap(output, rows, "video_test", 10, config, event_label="synthetic")

            self.assertTrue(output.exists())
            self.assertGreater(output.stat().st_size, 0)
            self.assertEqual(result["robots"], 2)
            self.assertEqual(result["balls"], 1)

    def test_draw_minimap_highlight_and_manifest_are_versionable_artifacts(self) -> None:
        rows = [
            track(10, "robot_owner", "small_robot", 0.45, 0.5),
            track(11, "robot_owner", "small_robot", 0.5, 0.48),
            track(12, "robot_owner", "small_robot", 0.55, 0.46),
            track(10, "ball_01", "ball", 0.46, 0.5),
            track(11, "ball_01", "ball", 0.52, 0.47),
            track(12, "ball_01", "ball", 0.58, 0.45),
        ]
        highlight = {
            "highlight_id": "lvl3_evt_test",
            "rank": "1",
            "clip_id": "video_test",
            "frame_start": "10",
            "frame_end": "12",
            "score": "88.5",
            "confidence": "0.82",
        }
        with TemporaryDirectory() as tmpdir:
            output = Path(tmpdir) / "minimap.png"
            manifest = Path(tmpdir) / "visualization_manifest.csv"

            result = draw_minimap_highlight(output, rows, highlight)
            write_visualization_manifest(
                manifest,
                [
                    {
                        "clip_id": "video_test",
                        "asset_id": "minimap_highlight_1",
                        "asset_type": "png",
                        "path": result["path"],
                        "source_artifact": "synthetic_highlights.csv",
                        "frame_start": result["frame_start"],
                        "frame_end": result["frame_end"],
                        "event_id": "lvl3_evt_test",
                        "is_versioned": "true",
                        "notes": "synthetic versionable artifact",
                    }
                ],
            )

            with manifest.open("r", newline="", encoding="utf-8") as handle:
                rows_from_manifest = list(csv.DictReader(handle))

            self.assertTrue(output.exists())
            self.assertGreater(output.stat().st_size, 0)
            self.assertEqual(rows_from_manifest[0]["asset_type"], "png")
            self.assertEqual(rows_from_manifest[0]["is_versioned"], "true")


if __name__ == "__main__":
    unittest.main()
