from __future__ import annotations

from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from futbotmx.full_analysis import (
    FullAnalysisRequest,
    manifest_rows_for_paths,
    next_experiment_dir,
    stage_plan_template,
)


class FullAnalysisTests(unittest.TestCase):
    def test_next_experiment_dir_uses_next_number_and_clip_window(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "experiments" / "test_003_existing").mkdir(parents=True)
            (root / "experiments" / "test_014_other").mkdir()

            path = next_experiment_dir(root, "video_595", 120, 180)

            self.assertEqual(path.as_posix(), "experiments/test_015_full_analysis_video_595_120_180")

    def test_stage_plan_marks_sam3_as_gpu_when_detections_are_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            tracks = root / "experiments" / "test_017_level2_closure" / "video_595" / "tracks_level2.csv"
            tracks.parent.mkdir(parents=True)
            tracks.write_text("frame,track_id,class_name,x,y,bbox_x1,bbox_y1,bbox_x2,bbox_y2,confidence,team\n", encoding="utf-8")
            request = FullAnalysisRequest(
                video="video.mov",
                clip_id="video_595",
                start_frame=120,
                end_frame=180,
            )

            plan = {stage.stage_id: stage for stage in stage_plan_template(request, root)}

            self.assertEqual(plan["sam3_detections"].status, "requires_gpu")
            self.assertEqual(plan["sam3_detections"].kind, "requires_gpu")
            self.assertEqual(plan["tracking"].status, "pass")

    def test_manifest_rows_use_paths_relative_to_experiment(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            experiment = root / "experiments" / "test_034_full_analysis"
            dashboard = experiment / "dashboard" / "dashboard.html"
            dashboard.parent.mkdir(parents=True)
            dashboard.write_text("<html></html>\n", encoding="utf-8")
            summary = experiment / "summary.md"
            summary.write_text("# Summary\n", encoding="utf-8")

            rows = manifest_rows_for_paths(root, experiment, [dashboard, summary])
            by_path = {row["path"]: row for row in rows}

            self.assertEqual(by_path["dashboard/dashboard.html"]["role"], "local_demo")
            self.assertEqual(by_path["summary.md"]["role"], "summary")


if __name__ == "__main__":
    unittest.main()
