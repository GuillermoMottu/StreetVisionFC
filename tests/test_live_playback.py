from __future__ import annotations

import csv
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from futbotmx.live_playback import (
    LivePlaybackConfig,
    available_frame_numbers,
    build_live_playback_context,
    build_live_playback_package,
    client_payload,
    frame_from_timestamp,
    live_playback_config_from_project,
    playback_clips_from_config,
    render_playback_html,
    resolve_overlay_frame,
    selected_playback_clip,
    sync_summary_from_frames,
    timestamp_from_frame,
    video_metadata_from_config,
)


def write_csv(path: Path, rows: list[dict[str, object]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


class LivePlaybackTests(unittest.TestCase):
    def test_playback_clips_from_config_reads_level2_closure_video_metadata(self) -> None:
        config = project_config("video_595", "local/video.mov")

        clips = playback_clips_from_config(config)
        selected = selected_playback_clip(clips, "video_595")

        self.assertEqual(len(clips), 1)
        self.assertEqual(selected.clip_id, "video_595")
        self.assertEqual(selected.fps, 60.0)
        self.assertEqual(selected.width, 1280)
        self.assertEqual(selected.start_frame, 120)

    def test_live_playback_config_uses_first_existing_sources(self) -> None:
        with TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            create_source_artifacts(root)
            config = project_config("video_fixture", "video.mov")

            playback_config = live_playback_config_from_project(root, config, Path("experiments/out"), clip_id="video_fixture")

            self.assertEqual(playback_config.clip_id, "video_fixture")
            self.assertEqual(playback_config.tracks_csv, "experiments/test_034_full_analysis/level3_spatial/level3_tracks.csv")
            self.assertEqual(playback_config.events_json, "experiments/test_034_full_analysis/level3_events/level3_events.json")
            self.assertEqual(playback_config.highlights_csv, "experiments/test_034_full_analysis/level3_events/level3_highlights.csv")

    def test_context_normalizes_tracks_events_highlights_and_minimap(self) -> None:
        with TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            create_source_artifacts(root)
            playback_config = fixture_playback_config(root)

            context = build_live_playback_context(root, playback_config)

            self.assertEqual(context["summary"]["track_rows"], 2)
            self.assertEqual(context["summary"]["event_count"], 1)
            self.assertEqual(context["summary"]["highlight_count"], 1)
            self.assertEqual(context["summary"]["validation_errors"], 0)
            self.assertEqual(context["tracks"][0]["class"], "ball")
            self.assertEqual(context["events"][0]["status"], "provisional")
            self.assertEqual(context["highlights"][0]["status"], "provisional")
            self.assertEqual(len(context["minimap_sample"]["points"]), 2)
            self.assertEqual(context["video_metadata"].configured_frame_count, 4)
            self.assertEqual(context["sync"]["available_frame_count"], 1)

    def test_render_playback_html_contains_video_canvas_layers_and_readouts(self) -> None:
        with TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            create_source_artifacts(root)
            context = build_live_playback_context(root, fixture_playback_config(root))

            html = render_playback_html(context)

            self.assertIn("<video", html)
            self.assertIn('<canvas id="overlay"', html)
            self.assertIn("layerTracks", html)
            self.assertIn("layerHighlights", html)
            self.assertIn("frameReadout", html)
            self.assertIn("resolvedFrameReadout", html)
            self.assertIn("FUTBOT_PLAYBACK_DATA", html)
            self.assertIn("drawMinimap", html)
            self.assertIn("resolveOverlayFrame", html)
            self.assertIn("seeked", html)
            self.assertIn("ratechange", html)

    def test_build_live_playback_package_writes_activity_23_artifacts(self) -> None:
        with TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            create_source_artifacts(root)
            config_path = write_project_config(root)
            playback_config = fixture_playback_config(root)

            context = build_live_playback_package(root, config_path, playback_config)
            output_dir = root / playback_config.output_dir

            self.assertEqual(context["summary"]["validation_errors"], 0)
            self.assertTrue((output_dir / "playback.html").exists())
            self.assertTrue((output_dir / "config.yaml").exists())
            self.assertTrue((output_dir / "live_playback_manifest.csv").exists())
            self.assertTrue((output_dir / "summary.md").exists())
            self.assertTrue((output_dir / "live_tracks.csv").exists())
            self.assertTrue((output_dir / "live_events.json").exists())
            self.assertTrue((output_dir / "live_highlights.csv").exists())
            self.assertTrue((output_dir / "video_metadata.json").exists())
            summary = (output_dir / "summary.md").read_text(encoding="utf-8")
            self.assertIn("Playback Vivo Con Overlays Precomputados", summary)
            self.assertIn("Tracks normalizados: `2`", summary)
            self.assertIn("Conversion: `frame = round(currentTime * fps)`", summary)

    def test_client_payload_is_small_frontend_contract(self) -> None:
        with TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            create_source_artifacts(root)
            context = build_live_playback_context(root, fixture_playback_config(root))

            payload = client_payload(context)

            self.assertEqual(payload["config"]["clip_id"], "video_fixture")
            self.assertEqual(payload["config"]["trail_length"], 16)
            self.assertEqual(payload["summary"]["highlight_count"], 1)
            self.assertEqual(payload["tracks"][0]["track_id"], "ball_bt_01")
            self.assertEqual(payload["available_frames"], [120])
            self.assertEqual(payload["sync"]["max_frame_gap"], 0)
            self.assertEqual(payload["video_metadata"]["configured_frame_count"], 4)

    def test_frame_timestamp_conversion_and_resolution_prefers_previous_frame(self) -> None:
        self.assertEqual(frame_from_timestamp(2.01, 60.0), 121)
        self.assertEqual(frame_from_timestamp(0.1, 60.0, start_frame=120), 120)
        self.assertEqual(frame_from_timestamp(9.0, 60.0, end_frame=180), 180)
        self.assertAlmostEqual(timestamp_from_frame(120, 60.0), 2.0)

        frames = [120, 123, 126]

        self.assertEqual(resolve_overlay_frame(123, frames).status, "exact")
        fallback = resolve_overlay_frame(125, frames)
        self.assertEqual(fallback.resolved_frame, 123)
        self.assertEqual(fallback.status, "previous")
        missing = resolve_overlay_frame(130, frames, max_gap_frames=2)
        self.assertIsNone(missing.resolved_frame)
        self.assertEqual(missing.status, "missing")

    def test_video_metadata_and_sync_summary_are_lightweight(self) -> None:
        with TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            playback_config = fixture_playback_config(root)

            metadata = video_metadata_from_config(playback_config)
            sync = sync_summary_from_frames(playback_config, [120, 123, 126])

            self.assertTrue(metadata.video_exists)
            self.assertEqual(metadata.width, 1280)
            self.assertEqual(metadata.configured_frame_count, 4)
            self.assertEqual(metadata.configured_duration_sec, round(4 / 60.0, 6))
            self.assertEqual(sync["available_frame_count"], 3)
            self.assertEqual(sync["max_frame_gap"], 3)
            self.assertFalse(sync["interpolation_enabled"])

    def test_available_frame_numbers_deduplicates_and_sorts(self) -> None:
        frames = available_frame_numbers([{"frame": "123"}, {"frame": "120"}, {"frame": "123"}])

        self.assertEqual(frames, [120, 123])


def fixture_playback_config(root: Path) -> LivePlaybackConfig:
    video_path = root / "video.mov"
    video_path.write_bytes(b"tiny placeholder")
    return LivePlaybackConfig(
        clip_id="video_fixture",
        video_path=video_path.as_posix(),
        fps=60.0,
        width=1280,
        height=720,
        start_frame=120,
        end_frame=123,
        tracks_csv="experiments/test_034_full_analysis/level3_spatial/level3_tracks.csv",
        events_json="experiments/test_034_full_analysis/level3_events/level3_events.json",
        highlights_csv="experiments/test_034_full_analysis/level3_events/level3_highlights.csv",
        output_dir="experiments/test_039_live_playback",
    )


def project_config(clip_id: str, video_path: str) -> dict[str, object]:
    return {
        "level2_closure": {
            "clips": [
                {
                    "clip_id": clip_id,
                    "role": "dense_candidate",
                    "video": video_path,
                    "start_frame": 120,
                    "end_frame": 123,
                    "fps": 60.0,
                    "width": 1280,
                    "height": 720,
                }
            ]
        }
    }


def write_project_config(root: Path) -> Path:
    config_dir = root / "configs"
    config_dir.mkdir(parents=True)
    config_path = config_dir / "default.yaml"
    config_path.write_text(
        "\n".join(
            [
                "level2_closure:",
                "  clips:",
                "    - clip_id: video_fixture",
                "      role: dense_candidate",
                "      video: video.mov",
                "      start_frame: 120",
                "      end_frame: 123",
                "      fps: 60.0",
                "      width: 1280",
                "      height: 720",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    return Path("configs/default.yaml")


def create_source_artifacts(root: Path) -> None:
    tracks_path = root / "experiments/test_034_full_analysis/level3_spatial/level3_tracks.csv"
    events_path = root / "experiments/test_034_full_analysis/level3_events/level3_events.json"
    highlights_path = root / "experiments/test_034_full_analysis/level3_events/level3_highlights.csv"
    write_csv(
        tracks_path,
        [
            {
                "clip_id": "video_fixture",
                "frame": 120,
                "time_sec": 2.0,
                "track_id": "ball_bt_01",
                "source_track_id": "ball_bt_01",
                "class_name": "ball",
                "team": "neutral",
                "x": 100.0,
                "y": 80.0,
                "bbox_x1": 92.0,
                "bbox_y1": 72.0,
                "bbox_x2": 108.0,
                "bbox_y2": 88.0,
                "confidence": 0.88,
                "x_norm": 0.55,
                "y_norm": 0.42,
                "zone": "middle_third",
                "calibration_confidence": 0.8,
            },
            {
                "clip_id": "video_fixture",
                "frame": 120,
                "time_sec": 2.0,
                "track_id": "small_robot_bt_01",
                "source_track_id": "small_robot_bt_01",
                "class_name": "small_robot",
                "team": "blue",
                "x": 180.0,
                "y": 160.0,
                "bbox_x1": 150.0,
                "bbox_y1": 130.0,
                "bbox_x2": 210.0,
                "bbox_y2": 190.0,
                "confidence": 0.9,
                "x_norm": 0.44,
                "y_norm": 0.38,
                "zone": "middle_third",
                "calibration_confidence": 0.8,
            },
            {
                "clip_id": "other_clip",
                "frame": 120,
                "time_sec": 2.0,
                "track_id": "ignored",
                "source_track_id": "ignored",
                "class_name": "ball",
                "team": "neutral",
                "x": 1.0,
                "y": 1.0,
                "bbox_x1": 0.0,
                "bbox_y1": 0.0,
                "bbox_x2": 2.0,
                "bbox_y2": 2.0,
                "confidence": 0.1,
                "x_norm": 0.1,
                "y_norm": 0.1,
                "zone": "middle_third",
                "calibration_confidence": 0.8,
            },
        ],
        [
            "clip_id",
            "frame",
            "time_sec",
            "track_id",
            "source_track_id",
            "class_name",
            "team",
            "x",
            "y",
            "bbox_x1",
            "bbox_y1",
            "bbox_x2",
            "bbox_y2",
            "confidence",
            "x_norm",
            "y_norm",
            "zone",
            "calibration_confidence",
        ],
    )
    events_path.parent.mkdir(parents=True, exist_ok=True)
    events_path.write_text(
        json.dumps(
            [
                {
                    "event_id": "lvl3_evt_0001",
                    "event_type": "advanced_highlight",
                    "clip_id": "video_fixture",
                    "frame_start": 120,
                    "frame_end": 121,
                    "time_start_sec": 2.0,
                    "time_end_sec": 2.017,
                    "team": "blue",
                    "primary_object_id": "small_robot_bt_01",
                    "secondary_object_ids": ["ball_bt_01"],
                    "ball_id": "ball_bt_01",
                    "zone": "middle_third",
                    "confidence": 0.86,
                    "reliability": "provisional",
                    "source_event_ids": ["lvl2_evt_0001"],
                    "spatial_context": {"reason": ["posesion_candidata"]},
                }
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    write_csv(
        highlights_path,
        [
            {
                "clip_id": "video_fixture",
                "highlight_id": "lvl3_evt_0001",
                "rank": 1,
                "score": 80.0,
                "event_type": "advanced_highlight",
                "frame_start": 120,
                "frame_end": 121,
                "time_start_sec": 2.0,
                "time_end_sec": 2.017,
                "primary_track_id": "small_robot_bt_01",
                "secondary_track_ids": "ball_bt_01",
                "zone": "middle_third",
                "confidence": 0.86,
                "reliability": "provisional",
                "reason": "posesion_candidata",
                "source_event_ids": "lvl2_evt_0001",
            }
        ],
        [
            "clip_id",
            "highlight_id",
            "rank",
            "score",
            "event_type",
            "frame_start",
            "frame_end",
            "time_start_sec",
            "time_end_sec",
            "primary_track_id",
            "secondary_track_ids",
            "zone",
            "confidence",
            "reliability",
            "reason",
            "source_event_ids",
        ],
    )


if __name__ == "__main__":
    unittest.main()
