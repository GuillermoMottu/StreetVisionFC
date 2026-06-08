from __future__ import annotations

import csv
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from futbotmx.live_playback import (
    FrameLoopControl,
    LivePlaybackConfig,
    OnlineFrameLoopConfig,
    STREAM_MESSAGE_TYPES,
    available_frame_numbers,
    backend_endpoint_manifest,
    build_online_frame_loop,
    build_stream_messages,
    build_live_playback_context,
    build_live_playback_package,
    calibration_payload,
    client_payload,
    csv_response_text,
    debug_panel_summary,
    frame_loop_metrics_csv,
    frame_from_timestamp,
    inference_mode_catalog,
    inference_mode_profiles,
    live_tracks_jsonl,
    live_playback_config_from_project,
    online_frame_loop_config_from_playback,
    minimap_payload_for_frame,
    playback_clips_from_config,
    render_playback_html,
    resolve_requested_video,
    resolve_overlay_frame,
    run_smoke_test,
    selected_playback_clip,
    sse_format_message,
    sse_stream_text,
    stream_latency_metrics_csv,
    stream_events_jsonl,
    stream_messages_jsonl,
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


def clone_context_with_frames(context: dict[str, object], frames: list[int]) -> dict[str, object]:
    playback_config = context["config"]
    tracks: list[dict[str, object]] = []
    for frame in frames:
        for row in context["tracks"]:
            clone = dict(row)
            clone["frame"] = frame
            clone["timestamp_sec"] = timestamp_from_frame(frame, playback_config.fps)
            clone["x"] = float(clone["x"]) + (frame - frames[0])
            clone["center_x"] = float(clone["center_x"]) + (frame - frames[0])
            tracks.append(clone)
    cloned = dict(context)
    cloned["tracks"] = tracks
    cloned["available_frames"] = available_frame_numbers(tracks)
    cloned["sync"] = sync_summary_from_frames(playback_config, cloned["available_frames"])
    cloned["summary"] = dict(context["summary"])
    cloned["summary"]["track_rows"] = len(tracks)
    cloned["summary"]["available_frame_count"] = len(cloned["available_frames"])
    return cloned


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
            config["live_playback"] = {
                "inference": {
                    "mode": "lightweight_detector",
                    "sam3_stride": 7,
                    "lightweight_stride": 3,
                }
            }

            playback_config = live_playback_config_from_project(root, config, Path("experiments/out"), clip_id="video_fixture")

            self.assertEqual(playback_config.clip_id, "video_fixture")
            self.assertEqual(playback_config.tracks_csv, "experiments/test_034_full_analysis/level3_spatial/level3_tracks.csv")
            self.assertEqual(playback_config.events_json, "experiments/test_034_full_analysis/level3_events/level3_events.json")
            self.assertEqual(playback_config.highlights_csv, "experiments/test_034_full_analysis/level3_events/level3_highlights.csv")
            self.assertEqual(playback_config.inference_mode, "lightweight_detector")
            self.assertEqual(playback_config.sam3_stride, 7)
            self.assertEqual(playback_config.lightweight_stride, 3)

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
            self.assertIn("streamReadout", html)
            self.assertIn("engineReadout", html)
            self.assertIn("inferenceReadout", html)
            self.assertIn("debugPanel", html)
            self.assertIn("debugFrameReadout", html)
            self.assertIn("debugQueueReadout", html)
            self.assertIn("downloadSessionLog", html)
            self.assertIn("/live_tracks.jsonl", html)
            self.assertIn("/stream_events.jsonl", html)
            self.assertIn("EventSource", html)
            self.assertIn("connectEventStream", html)
            self.assertIn("updateDebugPanel", html)

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
            self.assertTrue((output_dir / "live_tracks.jsonl").exists())
            self.assertTrue((output_dir / "video_metadata.json").exists())
            self.assertTrue((output_dir / "endpoint_manifest.json").exists())
            self.assertTrue((output_dir / "stream_messages.jsonl").exists())
            self.assertTrue((output_dir / "stream_events.jsonl").exists())
            self.assertTrue((output_dir / "stream_latency_metrics.csv").exists())
            self.assertTrue((output_dir / "stream_summary.json").exists())
            self.assertTrue((output_dir / "frame_loop_summary.json").exists())
            self.assertTrue((output_dir / "frame_loop_metrics.csv").exists())
            self.assertTrue((output_dir / "inference_modes.json").exists())
            self.assertTrue((output_dir / "debug_panel_summary.json").exists())
            summary = (output_dir / "summary.md").read_text(encoding="utf-8")
            self.assertIn("Playback Vivo Con Overlays Precomputados", summary)
            self.assertIn("Tracks normalizados: `2`", summary)
            self.assertIn("Conversion: `frame = round(currentTime * fps)`", summary)
            self.assertIn("Canal SSE", summary)
            self.assertIn("Modos De Inferencia", summary)
            self.assertIn("Panel De Depuracion", summary)
            endpoint_manifest = json.loads((output_dir / "endpoint_manifest.json").read_text(encoding="utf-8"))
            self.assertTrue(any(endpoint["path"] == "/tracks.csv" for endpoint in endpoint_manifest["endpoints"]))
            stream_summary = json.loads((output_dir / "stream_summary.json").read_text(encoding="utf-8"))
            self.assertEqual(stream_summary["transport"], "sse")
            self.assertEqual(stream_summary["frame_result_count"], 1)
            frame_loop_summary = json.loads((output_dir / "frame_loop_summary.json").read_text(encoding="utf-8"))
            self.assertEqual(frame_loop_summary["mode"], "precomputed_online_loop")
            self.assertEqual(frame_loop_summary["processed_frame_count"], 1)
            inference_modes = json.loads((output_dir / "inference_modes.json").read_text(encoding="utf-8"))
            self.assertEqual(inference_modes["selected_mode"], "precomputed")
            self.assertEqual(inference_modes["recommended_mode"], "precomputed")
            debug_summary = json.loads((output_dir / "debug_panel_summary.json").read_text(encoding="utf-8"))
            self.assertTrue(debug_summary["diagnostic_coverage"]["latency"])
            self.assertEqual(debug_summary["download_artifacts"]["live_tracks_jsonl"], "live_tracks.jsonl")
            self.assertIn("frame_result", (output_dir / "stream_messages.jsonl").read_text(encoding="utf-8"))
            self.assertIn("live_track", (output_dir / "live_tracks.jsonl").read_text(encoding="utf-8"))
            self.assertIn("event_update", (output_dir / "stream_events.jsonl").read_text(encoding="utf-8"))

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
            self.assertEqual(payload["endpoints"]["manifest"], "/manifest.json")
            self.assertEqual(payload["endpoints"]["stream"], "/stream")
            self.assertEqual(payload["endpoints"]["session_log"], "/stream-messages.jsonl")
            self.assertEqual(payload["endpoints"]["live_tracks_jsonl"], "/live_tracks.jsonl")
            self.assertEqual(payload["endpoints"]["stream_events_jsonl"], "/stream_events.jsonl")
            self.assertEqual(payload["endpoints"]["frame_loop_summary"], "/frame-loop-summary.json")
            self.assertEqual(payload["endpoints"]["inference_modes"], "/inference-modes.json")
            self.assertEqual(payload["endpoints"]["debug_panel"], "/debug-panel.json")
            self.assertEqual(payload["stream_summary"]["transport"], "sse")
            self.assertEqual(payload["frame_loop"]["mode"], "precomputed_online_loop")
            self.assertEqual(payload["inference_modes"]["selected_mode"], "precomputed")
            self.assertIn("active_event", payload["debug_panel"]["visible_indicators"])

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

    def test_inference_mode_catalog_selects_configured_mode_and_documents_limits(self) -> None:
        with TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            playback_config = fixture_playback_config(root)
            sam3_config = LivePlaybackConfig(
                clip_id=playback_config.clip_id,
                video_path=playback_config.video_path,
                fps=playback_config.fps,
                width=playback_config.width,
                height=playback_config.height,
                start_frame=playback_config.start_frame,
                end_frame=playback_config.end_frame,
                tracks_csv=playback_config.tracks_csv,
                events_json=playback_config.events_json,
                highlights_csv=playback_config.highlights_csv,
                output_dir=playback_config.output_dir,
                inference_mode="sam3_sampling",
                sam3_stride=5,
                allow_gpu=False,
            )
            context = {"config": sam3_config}

            profiles = inference_mode_profiles(sam3_config)
            catalog = inference_mode_catalog(context)
            selected = catalog["selected_profile"]
            precomputed = next(profile for profile in profiles if profile.mode_id == "precomputed")
            lightweight = next(profile for profile in profiles if profile.mode_id == "lightweight_detector")

            self.assertEqual({profile.mode_id for profile in profiles}, {"precomputed", "sam3_sampling", "lightweight_detector"})
            self.assertTrue(precomputed.recommended)
            self.assertEqual(catalog["selected_mode"], "sam3_sampling")
            self.assertEqual(selected["stride_frames"], 5)
            self.assertEqual(selected["hardware_profile"], "msi_gpu_only")
            self.assertEqual(selected["gpu_memory_metric"], "unavailable_without_gpu_probe")
            self.assertIn("calidad inferior", lightweight.quality_note)

    def test_backend_endpoint_manifest_documents_fixed_routes_and_video_policy(self) -> None:
        with TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            create_source_artifacts(root)
            context = build_live_playback_context(root, fixture_playback_config(root))

            manifest = backend_endpoint_manifest(context)
            endpoint_paths = {endpoint["path"] for endpoint in manifest["endpoints"]}

            self.assertIn("/manifest.json", endpoint_paths)
            self.assertIn("/stream", endpoint_paths)
            self.assertIn("/stream-summary.json", endpoint_paths)
            self.assertIn("/stream-messages.jsonl", endpoint_paths)
            self.assertIn("/live_tracks.jsonl", endpoint_paths)
            self.assertIn("/stream_events.jsonl", endpoint_paths)
            self.assertIn("/stream-latency.csv", endpoint_paths)
            self.assertIn("/frame-loop-summary.json", endpoint_paths)
            self.assertIn("/frame-loop-metrics.csv", endpoint_paths)
            self.assertIn("/inference-modes.json", endpoint_paths)
            self.assertIn("/debug-panel.json", endpoint_paths)
            self.assertIn("/tracks.csv", endpoint_paths)
            self.assertIn("/events.json", endpoint_paths)
            self.assertIn("/highlights.csv", endpoint_paths)
            self.assertIn("/minimap.json?frame=120", endpoint_paths)
            self.assertIn("/calibration.json", endpoint_paths)
            self.assertIn("/video-metadata.json", endpoint_paths)
            self.assertIn("/video?clip_id=video_fixture", endpoint_paths)
            self.assertEqual(manifest["channel"]["selected"], "sse")
            self.assertEqual(manifest["channel"]["producer"], "online_frame_loop")
            self.assertEqual(manifest["channel"]["inference_mode"], "precomputed")
            self.assertEqual(manifest["channel"]["websocket_status"], "deferred_until_bidirectional_commands")
            self.assertEqual(manifest["path_policy"]["artifacts"], "fixed endpoint names only; no arbitrary filesystem path endpoint")
            self.assertFalse(manifest["video"]["is_versioned"])

    def test_stream_messages_define_sse_contract_and_frame_results(self) -> None:
        with TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            create_source_artifacts(root)
            context = build_live_playback_context(root, fixture_playback_config(root))

            messages = build_stream_messages(context)
            message_types = {message["type"] for message in messages}
            frame_results = [message for message in messages if message["type"] == "frame_result"]
            latency_csv = stream_latency_metrics_csv(messages)
            jsonl = stream_messages_jsonl(messages)
            sse_message = sse_format_message(frame_results[0])
            sse_stream = sse_stream_text(messages)
            missing_config = LivePlaybackConfig(
                clip_id="video_fixture",
                video_path=(root / "missing.mov").as_posix(),
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
            missing_messages = build_stream_messages(build_live_playback_context(root, missing_config))
            missing_message_types = {message["type"] for message in missing_messages}

            self.assertTrue({"session_status", "frame_result", "event_update", "latency_metrics"}.issubset(message_types))
            self.assertEqual(set(STREAM_MESSAGE_TYPES), {"session_status", "frame_result", "event_update", "latency_metrics", "warning"})
            self.assertIn("warning", missing_message_types)
            self.assertEqual(frame_results[0]["frame"], 120)
            self.assertEqual(frame_results[0]["track_count"], 2)
            self.assertEqual(frame_results[0]["event_count"], 1)
            self.assertIn("event: frame_result\n", sse_message)
            self.assertIn("data: {", sse_message)
            self.assertTrue(sse_stream.startswith("retry: 3000\n\n"))
            self.assertIn('"type":"latency_metrics"', jsonl)
            self.assertTrue(latency_csv.startswith("sequence,message_id,clip_id,frame"))

    def test_debug_panel_exports_downloadable_logs_and_coverage(self) -> None:
        with TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            create_source_artifacts(root)
            context = build_live_playback_context(root, fixture_playback_config(root))

            tracks_jsonl = live_tracks_jsonl(context["tracks"])
            events_jsonl = stream_events_jsonl(context["stream_messages"])
            summary = debug_panel_summary(context)

            self.assertIn('"record_type":"live_track"', tracks_jsonl)
            self.assertIn('"type":"event_update"', events_jsonl)
            self.assertEqual(summary["panel_id"], "debugPanel")
            self.assertIn("queue_depth", summary["visible_indicators"])
            self.assertEqual(summary["download_endpoints"]["session_log"], "/stream-messages.jsonl")
            self.assertTrue(summary["diagnostic_coverage"]["downloads"])

    def test_online_frame_loop_emits_partial_results_and_stage_metrics(self) -> None:
        with TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            create_source_artifacts(root)
            playback_config = fixture_playback_config(root)
            context = build_live_playback_context(root, playback_config)

            loop = build_online_frame_loop(context)
            frame_results = [message for message in loop["messages"] if message["type"] == "frame_result"]
            metrics_csv = frame_loop_metrics_csv(loop)
            loop_config = online_frame_loop_config_from_playback(playback_config)

            self.assertEqual(loop["summary"]["mode"], "precomputed_online_loop")
            self.assertTrue(loop["summary"]["emits_partial_results"])
            self.assertFalse(loop["summary"]["requires_final_csv"])
            self.assertEqual(loop["summary"]["processed_frame_count"], 1)
            self.assertEqual(frame_results[0]["detection_source"], playback_config.tracks_csv)
            self.assertEqual(frame_results[0]["inference_mode"], "precomputed")
            self.assertEqual(frame_results[0]["tracker_state"], "updated_incremental_snapshot")
            self.assertTrue(frame_results[0]["overlay_ready"])
            self.assertIn("frame_read_ms", metrics_csv)
            self.assertIn("total_to_overlay_ms", metrics_csv)
            self.assertGreater(loop_config.processing_budget_ms, 0)

    def test_online_frame_loop_supports_controls_and_backpressure_skip(self) -> None:
        with TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            create_source_artifacts(root)
            context = clone_context_with_frames(build_live_playback_context(root, fixture_playback_config(root)), [120, 121, 122, 123])

            controlled = build_online_frame_loop(
                context,
                controls=[
                    FrameLoopControl("pause", at_frame=120),
                    FrameLoopControl("resume", at_frame=121),
                    FrameLoopControl("seek", at_frame=121, seek_frame=120),
                    FrameLoopControl("stop", at_frame=123),
                ],
            )
            statuses = [message.get("status") for message in controlled["messages"] if message["type"] == "session_status"]
            frame_results = [message for message in controlled["messages"] if message["type"] == "frame_result"]

            self.assertIn("paused", statuses)
            self.assertIn("running", statuses)
            self.assertIn("seeked", statuses)
            self.assertIn("stopped", statuses)
            self.assertEqual(controlled["summary"]["state_reset_count"], 1)
            self.assertEqual(frame_results[0]["requested_frame"], 120)

            tight_budget = OnlineFrameLoopConfig(
                mode="precomputed_online_loop",
                target_fps=60.0,
                inference_enabled=False,
                inference_mode="precomputed",
                inference_profile="Precomputed SAM 3 detections",
                inference_status="recommended_for_demo",
                inference_stride=1,
                detection_source="experiments/test_034_full_analysis/level3_spatial/level3_tracks.csv",
                tracker_mode="incremental_precomputed_snapshot",
                event_window_frames=12,
                processing_budget_ms=0.2,
                max_skip_frames=2,
                backpressure_policy="skip_next_available_frames",
            )
            backpressured = build_online_frame_loop(context, loop_config=tight_budget)
            skip_statuses = [message for message in backpressured["messages"] if message.get("status") == "skipping_frames"]

            self.assertGreater(backpressured["summary"]["skipped_frame_count"], 0)
            self.assertTrue(skip_statuses)

    def test_csv_response_and_minimap_endpoint_payloads_are_reproducible(self) -> None:
        with TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            create_source_artifacts(root)
            context = build_live_playback_context(root, fixture_playback_config(root))

            tracks_csv = csv_response_text(context["tracks"], ("clip_id", "frame", "track_id"))
            minimap = minimap_payload_for_frame(context, frame=120)
            calibration = calibration_payload(context)

            self.assertTrue(tracks_csv.startswith("clip_id,frame,track_id\n"))
            self.assertIn("ball_bt_01", tracks_csv)
            self.assertEqual(minimap["frame"], 120)
            self.assertEqual(len(minimap["points"]), 2)
            self.assertEqual(calibration["status"], "rectified")
            self.assertEqual(calibration["confidence"], 0.8)

    def test_video_request_only_serves_configured_clip_and_blocks_path_query(self) -> None:
        with TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            playback_config = fixture_playback_config(root)

            resolved = resolve_requested_video(playback_config, {"clip_id": ["video_fixture"]})

            self.assertEqual(resolved, Path(playback_config.video_path))
            with self.assertRaises(PermissionError):
                resolve_requested_video(playback_config, {"clip_id": ["video_fixture"], "path": ["../../secret.mov"]})
            with self.assertRaises(FileNotFoundError):
                resolve_requested_video(playback_config, {"clip_id": ["other_clip"]})

    def test_smoke_test_accepts_video_override_and_documents_missing_video(self) -> None:
        with TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            create_source_artifacts(root)
            config_path = write_project_config(root)
            missing_video = root / "missing.mov"

            context = run_smoke_test(
                root,
                config_path,
                Path("experiments/test_039_live_playback"),
                clip_id="video_fixture",
                video_path=missing_video.as_posix(),
            )

            manifest = backend_endpoint_manifest(context)

            self.assertFalse(context["video_metadata"].video_exists)
            self.assertIn("Video local no disponible", manifest["video"]["missing_note"])


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
