from __future__ import annotations

import csv
import json
import tempfile
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from futbotmx.app_state import AppState
from futbotmx.local_app import (
    ClipOption,
    DEFAULT_EXPERIMENT_DIR,
    PipelineRequest,
    _build_pipeline_cmd,
    clip_options_from_config,
    pipeline_request_from_form,
    render_analyze,
    render_home,
    render_results,
    resolve_artifact_path,
    selected_clip,
)


def _make_clips() -> list[ClipOption]:
    return clip_options_from_config({
        "level2_closure": {
            "clips": [{
                "clip_id": "video_595",
                "role": "principal",
                "video": "data/local/video.mov",
                "start_frame": 120,
                "end_frame": 180,
                "stride": 1,
                "roi": [0, 615, 1344, 1792],
                "width": 1344,
                "height": 1792,
                "fps": 59.7,
            }]
        }
    })


def _make_multi_clips() -> list[ClipOption]:
    return clip_options_from_config({
        "level2_closure": {
            "clips": [
                {
                    "clip_id": "video_595",
                    "role": "principal",
                    "video": "data/local/video-595.mov",
                    "start_frame": 120,
                    "end_frame": 180,
                    "stride": 1,
                    "roi": [0, 615, 1344, 1792],
                    "width": 1344,
                    "height": 1792,
                    "fps": 59.7,
                },
                {
                    "clip_id": "video_667",
                    "role": "comparativo",
                    "video": "data/local/video-667.mov",
                    "start_frame": 90,
                    "end_frame": 150,
                    "stride": 2,
                    "roi": [0, 0, 1280, 720],
                    "width": 1280,
                    "height": 720,
                    "fps": 60.0,
                },
            ]
        }
    })


class ClipConfigTests(unittest.TestCase):
    def test_clip_options_use_level2_closure_defaults(self) -> None:
        clips = _make_clips()
        self.assertEqual(len(clips), 1)
        self.assertEqual(clips[0].clip_id, "video_595")
        self.assertEqual(clips[0].roi, (0, 615, 1344, 1792))
        self.assertEqual(clips[0].start_frame, 120)

    def test_selected_clip_returns_first_when_no_match(self) -> None:
        clips = _make_clips()
        clip = selected_clip(clips, "nonexistent")
        self.assertEqual(clip.clip_id, "video_595")

    def test_pipeline_request_from_form_clamps_frames_and_stride(self) -> None:
        clips = _make_clips()
        form = {
            "clip_id": ["video_595"],
            "video_path": ["custom.mov"],
            "start_frame": ["150"],
            "end_frame": ["140"],  # below start → clamped to start
            "stride": ["0"],       # below 1 → clamped to 1
        }
        req = pipeline_request_from_form(form, clips)
        self.assertEqual(req.start_frame, 150)
        self.assertEqual(req.end_frame, 150)
        self.assertEqual(req.stride, 1)
        self.assertEqual(req.video_path, "custom.mov")
        self.assertFalse(req.skip_segmentation)

    def test_pipeline_request_skip_segmentation_checkbox(self) -> None:
        clips = _make_clips()
        form = {
            "clip_id": ["video_595"],
            "video_path": ["v.mp4"],
            "start_frame": ["0"],
            "end_frame": ["60"],
            "stride": ["1"],
            "skip_segmentation": ["on"],
        }
        req = pipeline_request_from_form(form, clips)
        self.assertTrue(req.skip_segmentation)

    def test_build_pipeline_cmd_reuses_previous_detections_before_state_switch(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            previous = root / "experiments" / "run_prev"
            previous.mkdir(parents=True)
            (previous / "detections.json").write_text('{"frames":[]}\n', encoding="utf-8")
            state = AppState()
            state.start("/videos/old.mp4", "experiments/run_prev")
            request = PipelineRequest("/videos/new.mp4", "video_new", 0, 10, 1, skip_segmentation=True)

            cmd = _build_pipeline_cmd(root, request, "experiments/run_new", state, previous_experiment_dir="experiments/run_prev")

        self.assertIn("--detections", cmd)
        self.assertIn(str(previous / "detections.json"), cmd)

    def test_pipeline_request_generates_clip_id_for_manual_video_selection(self) -> None:
        clips = _make_clips()
        form = {
            "clip_id": ["nuevo"],
            "video_path": ["/videos/partido final 26.mov"],
            "start_frame": ["0"],
            "end_frame": ["60"],
            "stride": ["1"],
        }
        req = pipeline_request_from_form(form, clips)
        self.assertEqual(req.clip_id, "partido_final_26")
        self.assertEqual(req.video_path, "/videos/partido final 26.mov")


class HomeScreenTests(unittest.TestCase):
    def test_home_idle_state_shows_cta_and_nav(self) -> None:
        state = AppState()
        html = render_home(Path.cwd(), state)
        self.assertIn('data-ui-shell="futbotmx-ui-v1"', html)
        self.assertIn('data-product-flow="launcher"', html)
        self.assertIn("FutBotMX", html)
        self.assertIn('href="/analyze"', html)
        self.assertIn("Analizar video", html)
        self.assertIn("Grounded-SAM", html)
        self.assertIn("ByteTrack", html)

    def test_home_idle_shows_dashes_for_metrics(self) -> None:
        state = AppState()
        html = render_home(Path.cwd(), state)
        self.assertIn("—", html)
        self.assertIn("Sin análisis previo", html)

    def test_home_complete_enables_results_link(self) -> None:
        state = AppState()
        state.start("/video.mp4", "experiments/x")
        state.complete()
        html = render_home(Path.cwd(), state)
        self.assertIn('href="/results"', html)
        self.assertNotIn("disabled", html.split('href="/results"')[0].rsplit('<a', 1)[-1])

    def test_home_running_shows_running_note(self) -> None:
        state = AppState()
        state.start("/video.mp4", "experiments/x")
        html = render_home(Path.cwd(), state)
        self.assertIn("running", html)


class AnalyzeScreenTests(unittest.TestCase):
    def test_analyze_renders_form_with_video_browse(self) -> None:
        state = AppState()
        clips = _make_clips()
        html = render_analyze(Path.cwd(), clips, state)
        self.assertIn('data-ui-shell="futbotmx-ui-v1"', html)
        self.assertIn('data-product-flow="launcher"', html)
        self.assertIn('action="/start-analysis"', html)
        self.assertIn('name="video_path"', html)
        self.assertIn("fbOpen()", html)
        self.assertIn("📁 Explorar", html)
        self.assertIn("video-selected", html)
        self.assertIn("video_selected_name", html)
        self.assertIn('name="start_frame"', html)
        self.assertIn('name="end_frame"', html)
        self.assertIn('name="stride"', html)

    def test_analyze_renders_all_clip_options_with_video_names(self) -> None:
        state = AppState()
        html = render_analyze(Path.cwd(), _make_multi_clips(), state)
        self.assertIn("video_595 · video-595.mov", html)
        self.assertIn("video_667 · video-667.mov", html)
        self.assertIn("nuevo · seleccionar desde explorar", html)

    def test_analyze_pre_fills_clip_values(self) -> None:
        state = AppState()
        clips = _make_clips()
        html = render_analyze(Path.cwd(), clips, state)
        self.assertIn("video_595", html)
        self.assertIn("data/local/video.mov", html)
        self.assertIn("120", html)
        self.assertIn("180", html)

    def test_analyze_shows_skip_option_when_detections_exist(self) -> None:
        state = AppState()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            exp = root / "experiments" / "run_prev"
            exp.mkdir(parents=True)
            (exp / "detections.json").write_text("{}", encoding="utf-8")
            state.start("/v.mp4", "experiments/run_prev")
            state.complete()
            clips = _make_clips()
            html = render_analyze(root, clips, state)
        self.assertIn("skip_segmentation", html)
        self.assertIn("Reutilizar detecciones", html)

    def test_analyze_no_skip_option_without_detections(self) -> None:
        state = AppState()
        clips = _make_clips()
        html = render_analyze(Path.cwd(), clips, state)
        self.assertNotIn("skip_segmentation", html)

    def test_analyze_progress_panel_hidden_when_idle(self) -> None:
        state = AppState()
        clips = _make_clips()
        html = render_analyze(Path.cwd(), clips, state)
        self.assertIn('id="progress-panel"', html)
        self.assertIn('id="progress-panel" hidden', html)

    def test_analyze_disables_form_when_running(self) -> None:
        state = AppState()
        state.start("/v.mp4", "experiments/x")
        clips = _make_clips()
        html = render_analyze(Path.cwd(), clips, state)
        self.assertIn("disabled", html)
        self.assertIn("Pipeline en curso", html)

    def test_analyze_includes_sse_client_and_file_browser_js(self) -> None:
        state = AppState()
        clips = _make_clips()
        html = render_analyze(Path.cwd(), clips, state)
        self.assertIn("EventSource", html)
        self.assertIn("/analyze-progress", html)
        self.assertIn("/playback/browse", html)
        self.assertIn("/playback/video-info", html)
        self.assertIn("updateSelectedVideoName", html)
        self.assertIn("syncClipSelectWithPath", html)
        self.assertIn("fb-overlay", html)


class ResultsScreenTests(unittest.TestCase):
    def test_results_empty_state_shows_cta(self) -> None:
        state = AppState()
        html = render_results(Path.cwd(), state)
        self.assertIn("Analizar video", html)
        self.assertIn('href="/analyze"', html)
        self.assertNotIn("<iframe", html)

    def test_results_with_experiment_shows_playback_and_sections(self) -> None:
        state = AppState()
        state.start("/v.mp4", "experiments/x")
        state.complete()
        html = render_results(Path.cwd(), state)
        self.assertIn('data-ui-shell="futbotmx-ui-v1"', html)
        self.assertIn('data-product-flow="report"', html)
        self.assertIn("playback-frame", html)
        self.assertIn('/playback/', html)
        self.assertIn("Visualizaciones", html)
        self.assertIn("Highlights", html)

    def test_results_with_highlights_csv_renders_table(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            exp = root / "experiments" / "run_x"
            events_dir = exp / "level3_events"
            events_dir.mkdir(parents=True)
            csv_path = events_dir / "level3_highlights.csv"
            with csv_path.open("w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=["track_id", "score", "confidence", "frame_start", "event_label"])
                writer.writeheader()
                writer.writerow({"track_id": "robot_1", "score": "0.91", "confidence": "0.85", "frame_start": "42", "event_label": "possession"})
                writer.writerow({"track_id": "robot_2", "score": "0.78", "confidence": "0.70", "frame_start": "60", "event_label": "pass"})
            (events_dir / "level3_events.json").write_text("[]", encoding="utf-8")
            (exp / "level3_spatial").mkdir()
            (exp / "level3_spatial" / "level3_tracks.csv").write_text("frame,track_id\n1,robot_1\n", encoding="utf-8")

            state = AppState()
            state.start("/v.mp4", "experiments/run_x")
            state.complete()
            html = render_results(root, state)

        self.assertIn("0.910", html)
        self.assertIn("robot_1", html)
        self.assertIn("possession", html)

    def test_results_downloads_section_links_to_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            exp = root / "experiments" / "run_y"
            events_dir = exp / "level3_events"
            events_dir.mkdir(parents=True)
            csv_path = events_dir / "level3_highlights.csv"
            csv_path.write_text("track_id,score\n", encoding="utf-8")
            (events_dir / "level3_events.json").write_text("[]", encoding="utf-8")
            (exp / "level3_spatial").mkdir()
            (exp / "level3_spatial" / "level3_tracks.csv").write_text("frame,track_id\n", encoding="utf-8")

            state = AppState()
            state.start("/v.mp4", "experiments/run_y")
            state.complete()
            html = render_results(root, state)

        self.assertIn("/files/", html)
        self.assertIn("level3_highlights.csv", html)
        self.assertIn("level3_tracks.csv", html)


class SecurityTests(unittest.TestCase):
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
