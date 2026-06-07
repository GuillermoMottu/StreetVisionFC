from __future__ import annotations

from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from futbotmx.full_analysis import (
    FullAnalysisRequest,
    StageResult,
    _restore_cached_stage,
    _store_stage_cache,
    cache_key_for_stage,
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

    def test_cache_key_changes_when_input_content_changes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            tracks = root / "tracks.csv"
            tracks.write_text("frame,track_id,x,y\n1,ball,10,20\n", encoding="utf-8")
            request = FullAnalysisRequest(video="video.mov", clip_id="video_595", start_frame=120, end_frame=180)

            first_key = cache_key_for_stage(root, request, "tracking", {"tracks": tracks})
            tracks.write_text("frame,track_id,x,y\n1,ball,30,40\n", encoding="utf-8")
            second_key = cache_key_for_stage(root, request, "tracking", {"tracks": tracks})

            self.assertNotEqual(first_key, second_key)

    def test_cache_key_reuses_same_file_content_across_experiment_paths(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            first_tracks = root / "experiments" / "test_001" / "tracking" / "tracks.csv"
            second_tracks = root / "experiments" / "test_002" / "tracking" / "tracks.csv"
            first_tracks.parent.mkdir(parents=True)
            second_tracks.parent.mkdir(parents=True)
            content = "frame,track_id,x,y\n1,ball,10,20\n"
            first_tracks.write_text(content, encoding="utf-8")
            second_tracks.write_text(content, encoding="utf-8")
            request = FullAnalysisRequest(video="video.mov", clip_id="video_595", start_frame=120, end_frame=180)

            first_key = cache_key_for_stage(root, request, "level1_events", {"tracks": first_tracks})
            second_key = cache_key_for_stage(root, request, "level1_events", {"tracks": second_tracks})

            self.assertEqual(first_key, second_key)

    def test_stage_cache_can_store_and_restore_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            request = FullAnalysisRequest(
                video="video.mov",
                clip_id="video_595",
                start_frame=120,
                end_frame=180,
                cache_dir=".cache_test/full_analysis",
            )
            stage_dir = root / "experiments" / "test_001" / "tracking"
            stage_dir.mkdir(parents=True)
            tracks = stage_dir / "tracks.csv"
            tracks.write_text("frame,track_id,x,y\n1,ball,10,20\n", encoding="utf-8")
            result = StageResult(
                "tracking",
                "Tracking",
                "lightweight_or_reused",
                "provided_tracks",
                "pass",
                "experiments/test_001/tracking",
                outputs=["experiments/test_001/tracking/tracks.csv"],
                notes="Provided tracks copied.",
            )
            cache_key = cache_key_for_stage(root, request, "tracking", {"tracks": tracks})

            stored = _store_stage_cache(root, request, result, stage_dir, cache_key)
            restored_dir = root / "experiments" / "test_002" / "tracking"
            restored = _restore_cached_stage(
                root,
                request,
                "tracking",
                "Tracking",
                "lightweight_or_reused",
                "provided_tracks",
                restored_dir,
                cache_key,
            )

            self.assertEqual(stored.cache_status, "stored")
            self.assertIsNotNone(restored)
            self.assertEqual(restored.cache_status, "hit")  # type: ignore[union-attr]
            self.assertEqual((restored_dir / "tracks.csv").read_text(encoding="utf-8"), tracks.read_text(encoding="utf-8"))
            self.assertTrue((restored_dir / "cache_hit.json").exists())

    def test_force_bypasses_stage_cache_restore(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            request = FullAnalysisRequest(
                video="video.mov",
                clip_id="video_595",
                start_frame=120,
                end_frame=180,
                cache_dir=".cache_test/full_analysis",
            )
            stage_dir = root / "experiments" / "test_001" / "tracking"
            stage_dir.mkdir(parents=True)
            tracks = stage_dir / "tracks.csv"
            tracks.write_text("frame,track_id,x,y\n1,ball,10,20\n", encoding="utf-8")
            result = StageResult("tracking", "Tracking", "lightweight_or_reused", "provided_tracks", "pass", "experiments/test_001/tracking")
            cache_key = cache_key_for_stage(root, request, "tracking", {"tracks": tracks})
            _store_stage_cache(root, request, result, stage_dir, cache_key)
            force_request = FullAnalysisRequest(
                video="video.mov",
                clip_id="video_595",
                start_frame=120,
                end_frame=180,
                cache_dir=".cache_test/full_analysis",
                force=True,
            )

            restored = _restore_cached_stage(
                root,
                force_request,
                "tracking",
                "Tracking",
                "lightweight_or_reused",
                "provided_tracks",
                root / "experiments" / "test_002" / "tracking",
                cache_key,
            )

            self.assertIsNone(restored)


if __name__ == "__main__":
    unittest.main()
