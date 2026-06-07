from __future__ import annotations

from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from futbotmx.local_app import (
    DEFAULT_EXPERIMENT_DIR,
    analysis_request_from_form,
    clip_options_from_config,
    render_index,
    resolve_artifact_path,
)


class LocalAppTests(unittest.TestCase):
    def test_clip_options_use_level2_closure_defaults(self) -> None:
        config = {
            "level2_closure": {
                "clips": [
                    {
                        "clip_id": "video_595",
                        "role": "dense_candidate",
                        "video": "data/local/video.mov",
                        "start_frame": 120,
                        "end_frame": 180,
                        "stride": 1,
                        "roi": [0, 615, 1344, 1792],
                        "width": 1344,
                        "height": 1792,
                        "fps": 59.7,
                    }
                ]
            }
        }

        clips = clip_options_from_config(config)

        self.assertEqual(len(clips), 1)
        self.assertEqual(clips[0].clip_id, "video_595")
        self.assertEqual(clips[0].roi, (0, 615, 1344, 1792))
        self.assertEqual(clips[0].start_frame, 120)

    def test_form_request_clamps_frames_stride_and_custom_roi(self) -> None:
        clips = clip_options_from_config(
            {
                "level2_closure": {
                    "clips": [
                        {
                            "clip_id": "video_667",
                            "video": "data/local/video.mov",
                            "start_frame": 120,
                            "end_frame": 180,
                            "stride": 1,
                            "roi": [0, 620, 1360, 1808],
                            "width": 1360,
                            "height": 1808,
                        }
                    ]
                }
            }
        )
        form = {
            "clip_id": ["video_667"],
            "video_path": ["custom.mov"],
            "start_frame": ["150"],
            "end_frame": ["140"],
            "stride": ["0"],
            "roi_mode": ["custom"],
            "roi_x1": ["10"],
            "roi_y1": ["20"],
            "roi_x2": ["5000"],
            "roi_y2": ["6000"],
            "run_dashboard": ["on"],
        }

        request = analysis_request_from_form(form, clips)

        self.assertEqual(request.start_frame, 150)
        self.assertEqual(request.end_frame, 150)
        self.assertEqual(request.stride, 1)
        self.assertEqual(request.roi, (10, 20, 1360, 1808))
        self.assertTrue(request.run_dashboard)
        self.assertFalse(request.run_reel)

    def test_render_index_contains_form_and_clip_selector(self) -> None:
        clips = clip_options_from_config(
            {
                "level2_closure": {
                    "clips": [
                        {
                            "clip_id": "video_595",
                            "role": "principal",
                            "start_frame": 120,
                            "end_frame": 180,
                            "roi": [0, 615, 1344, 1792],
                            "width": 1344,
                            "height": 1792,
                        }
                    ]
                }
            }
        )

        html = render_index(Path.cwd(), Path("configs/default.yaml"), DEFAULT_EXPERIMENT_DIR, clips)

        self.assertIn('action="/run-analysis"', html)
        self.assertIn("video_595", html)
        self.assertIn("Ejecutar analisis", html)

    def test_resolve_artifact_path_blocks_traversal(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            artifact = root / "experiments" / "summary.md"
            artifact.parent.mkdir(parents=True)
            artifact.write_text("ok\n", encoding="utf-8")

            resolved = resolve_artifact_path(root, "experiments/summary.md")

            self.assertEqual(resolved, artifact.resolve())
            with self.assertRaises(ValueError):
                resolve_artifact_path(root, "../outside.md")


if __name__ == "__main__":
    unittest.main()
