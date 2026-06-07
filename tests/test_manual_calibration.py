from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from futbotmx.level3.manual_calibration import (
    CalibrationEditorClip,
    CalibrationEditorContext,
    render_calibration_editor_html,
    save_manual_calibration_payload,
)


class ManualCalibrationTests(unittest.TestCase):
    def test_editor_html_contains_clip_canvas_and_save_action(self) -> None:
        context = CalibrationEditorContext(
            rule_version="manual_field_calibration_v0.1",
            output_dir="experiments/test_manual",
            source_dir="experiments/source",
            field_model={},
            clips=[
                CalibrationEditorClip(
                    clip_id="video_test",
                    role="test",
                    width=200,
                    height=300,
                    fps=10.0,
                    overlay_path="experiments/source/video_test/overlay_frame_120.png",
                    overlay_static_path="../source/video_test/overlay_frame_120.png",
                    overlay_server_path="/artifact?path=experiments/source/video_test/overlay_frame_120.png",
                    overlay_frame=120,
                    image_points=((10.0, 20.0), (190.0, 20.0), (190.0, 280.0), (10.0, 280.0)),
                    confidence=0.9,
                    notes="test",
                )
            ],
            calibration_json="field_calibration.json",
            editor_html="calibration_editor.html",
            manifest_csv="calibration_editor_manifest.csv",
        )

        html = render_calibration_editor_html(context)

        self.assertIn("fieldCanvas", html)
        self.assertIn("video_test", html)
        self.assertIn("/save-calibration", html)

    def test_save_manual_calibration_payload_writes_valid_json(self) -> None:
        payload = {
            "clips": {
                "video_test": {
                    "image_size": {"width": 200, "height": 300},
                    "image_points": [
                        {"label": "top_left", "x": 10.0, "y": 20.0},
                        {"label": "top_right", "x": 190.0, "y": 20.0},
                        {"label": "bottom_right", "x": 190.0, "y": 280.0},
                        {"label": "bottom_left", "x": 10.0, "y": 280.0},
                    ],
                    "field_points": [
                        {"label": "top_left", "x_norm": 0.0, "y_norm": 0.0},
                        {"label": "top_right", "x_norm": 1.0, "y_norm": 0.0},
                        {"label": "bottom_right", "x_norm": 1.0, "y_norm": 1.0},
                        {"label": "bottom_left", "x_norm": 0.0, "y_norm": 1.0},
                    ],
                }
            }
        }
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "field_calibration.json"

            save_manual_calibration_payload(payload, output)
            saved = json.loads(output.read_text(encoding="utf-8"))

        self.assertEqual(saved["review_status"], "human_saved")
        self.assertEqual(saved["clips"]["video_test"]["method"], "manual_four_corner_homography")
        self.assertEqual(len(saved["clips"]["video_test"]["image_points"]), 4)
        self.assertIn("homography", saved["clips"]["video_test"])


if __name__ == "__main__":
    unittest.main()
