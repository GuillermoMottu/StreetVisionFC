"""Tests for live_validation — Activity 33."""

import unittest

from futbotmx.live_validation import (
    DEFAULT_EVENT_OVERLAP_ACCEPTABLE,
    DEFAULT_EVENT_OVERLAP_DEGRADED,
    DEFAULT_TRACK_MATCH_ACCEPTABLE,
    DEFAULT_TRACK_MATCH_DEGRADED,
    EVENT_COMPARISON_CSV_FIELDS,
    MANIFEST_CSV_FIELDS,
    RUNTIME_METRICS_CSV_FIELDS,
    TRACK_COMPARISON_CSV_FIELDS,
    VALIDATION_ACCEPTABLE,
    VALIDATION_DEGRADED,
    VALIDATION_FAILED,
    EventComparisonResult,
    LiveValidationConfig,
    RuntimeMetrics,
    RuntimeMetricsRecorder,
    TrackComparisonResult,
    _mean,
    _percentile,
    compare_events,
    compare_tracks,
    event_comparison_csv_text,
    manifest_csv_text,
    runtime_metrics_csv_text,
    summary_md_text,
    track_comparison_csv_text,
)


# ===========================================================================
# Helpers
# ===========================================================================


def _track(frame: int, cx: float, cy: float) -> dict:
    return {"frame": frame, "cx": cx, "cy": cy, "class": "robot"}


def _event(label: str, start: int, end: int) -> dict:
    return {"label": label, "start_frame": start, "end_frame": end}


# ===========================================================================
# TestLatencyStats
# ===========================================================================


class TestLatencyStats(unittest.TestCase):

    def test_percentile_empty_returns_zero(self):
        self.assertEqual(_percentile([], 95), 0.0)

    def test_percentile_single_element(self):
        self.assertEqual(_percentile([42.0], 95), 42.0)

    def test_percentile_p50_median(self):
        values = [10.0, 20.0, 30.0, 40.0, 50.0]
        self.assertAlmostEqual(_percentile(values, 50), 30.0, places=5)

    def test_percentile_p95_known_values(self):
        values = [float(i) for i in range(1, 21)]  # 1..20
        result = _percentile(values, 95)
        self.assertGreaterEqual(result, 19.0)
        self.assertLessEqual(result, 20.0)

    def test_percentile_p0_is_min(self):
        values = [5.0, 3.0, 8.0]
        self.assertAlmostEqual(_percentile(values, 0), 3.0, places=5)

    def test_percentile_p100_is_max(self):
        values = [5.0, 3.0, 8.0]
        self.assertAlmostEqual(_percentile(values, 100), 8.0, places=5)

    def test_mean_empty_returns_zero(self):
        self.assertEqual(_mean([]), 0.0)

    def test_mean_single_value(self):
        self.assertEqual(_mean([7.0]), 7.0)

    def test_mean_known_values(self):
        self.assertAlmostEqual(_mean([10.0, 20.0, 30.0]), 20.0, places=5)


# ===========================================================================
# TestRuntimeMetricsRecorder
# ===========================================================================


class TestRuntimeMetricsRecorder(unittest.TestCase):

    def _rec(self, **kw) -> RuntimeMetricsRecorder:
        return RuntimeMetricsRecorder(
            session_id="test_session",
            clip_id="video_595",
            fps=30.0,
            **kw,
        )

    def test_initial_snapshot_has_zeros(self):
        rec = self._rec()
        snap = rec.snapshot()
        self.assertEqual(snap["total_video_frames"], 0)
        self.assertEqual(snap["total_analysis_frames"], 0)
        self.assertEqual(snap["skipped_frames"], 0)

    def test_record_video_frame_increments_count(self):
        rec = self._rec()
        rec.record_video_frame(0, 0.0)
        rec.record_video_frame(1, 33.3)
        self.assertEqual(rec.snapshot()["total_video_frames"], 2)

    def test_record_analysis_frame_increments_count(self):
        rec = self._rec()
        rec.record_analysis_frame(0, 20.0, 0.0)
        rec.record_analysis_frame(1, 25.0, 33.3)
        self.assertEqual(rec.snapshot()["total_analysis_frames"], 2)

    def test_record_skip_increments_count(self):
        rec = self._rec()
        rec.record_skip(5)
        rec.record_skip(6)
        self.assertEqual(rec.snapshot()["skipped_frames"], 2)

    def test_record_event_emitted_accumulates(self):
        rec = self._rec()
        rec.record_event_emitted(3)
        rec.record_event_emitted(2)
        self.assertEqual(rec.snapshot()["events_emitted"], 5)

    def test_record_event_updated_accumulates(self):
        rec = self._rec()
        rec.record_event_updated()
        rec.record_event_updated()
        self.assertEqual(rec.snapshot()["events_updated"], 2)

    def test_compute_with_no_data_returns_zero_metrics(self):
        rec = self._rec()
        m = rec.compute()
        self.assertEqual(m.video_fps, 0.0)
        self.assertEqual(m.analysis_fps, 0.0)
        self.assertEqual(m.mean_latency_ms, 0.0)
        self.assertEqual(m.p95_latency_ms, 0.0)
        self.assertEqual(m.skipped_frames, 0)

    def test_compute_with_single_video_frame_uses_configured_fps(self):
        rec = self._rec()
        rec.record_video_frame(0, 0.0)
        m = rec.compute()
        self.assertEqual(m.video_fps, 30.0)
        self.assertEqual(m.total_video_frames, 1)

    def test_compute_video_fps_from_timestamp_span(self):
        rec = self._rec()
        # 30 frames over 1000 ms → ~29 fps (n-1 / duration)
        for i in range(30):
            rec.record_video_frame(i, float(i) * (1000.0 / 29))
        m = rec.compute()
        self.assertAlmostEqual(m.video_fps, 29.0, places=0)

    def test_compute_analysis_fps_from_timestamp_span(self):
        rec = self._rec()
        for i in range(10):
            rec.record_video_frame(i, float(i) * 100.0)
        for i in range(10):
            rec.record_analysis_frame(i, 20.0, float(i) * 111.0)
        m = rec.compute()
        self.assertGreater(m.analysis_fps, 0.0)

    def test_compute_mean_latency(self):
        rec = self._rec()
        rec.record_video_frame(0, 0.0)
        rec.record_video_frame(1, 33.3)
        rec.record_analysis_frame(0, 10.0, 0.0)
        rec.record_analysis_frame(1, 30.0, 33.3)
        m = rec.compute()
        self.assertAlmostEqual(m.mean_latency_ms, 20.0, places=2)

    def test_compute_p95_latency(self):
        rec = self._rec()
        for i in range(20):
            rec.record_video_frame(i, float(i) * 33.3)
            rec.record_analysis_frame(i, float(i + 1) * 1.0, float(i) * 33.3)
        m = rec.compute()
        self.assertGreaterEqual(m.p95_latency_ms, 19.0)

    def test_compute_skipped_frames_count(self):
        rec = self._rec()
        rec.record_skip(3)
        rec.record_skip(4)
        m = rec.compute()
        self.assertEqual(m.skipped_frames, 2)

    def test_compute_events_reflected(self):
        rec = self._rec()
        rec.record_event_emitted(4)
        rec.record_event_updated(2)
        m = rec.compute()
        self.assertEqual(m.events_emitted, 4)
        self.assertEqual(m.events_updated, 2)

    def test_compute_classification_acceptable_when_low_latency(self):
        rec = self._rec(acceptable_latency_ms=33.3)
        rec.record_video_frame(0, 0.0)
        rec.record_analysis_frame(0, 20.0, 0.0)
        m = rec.compute()
        self.assertEqual(m.classification, VALIDATION_ACCEPTABLE)

    def test_compute_classification_degraded_for_medium_latency(self):
        rec = self._rec(acceptable_latency_ms=33.3, degraded_latency_ms=100.0)
        rec.record_video_frame(0, 0.0)
        rec.record_analysis_frame(0, 60.0, 0.0)
        m = rec.compute()
        self.assertEqual(m.classification, VALIDATION_DEGRADED)

    def test_compute_classification_failed_for_high_latency(self):
        rec = self._rec(acceptable_latency_ms=33.3, degraded_latency_ms=100.0)
        rec.record_video_frame(0, 0.0)
        rec.record_analysis_frame(0, 150.0, 0.0)
        m = rec.compute()
        self.assertEqual(m.classification, VALIDATION_FAILED)

    def test_reset_clears_all_data(self):
        rec = self._rec()
        rec.record_video_frame(0, 0.0)
        rec.record_analysis_frame(0, 20.0, 0.0)
        rec.record_skip(1)
        rec.record_event_emitted(3)
        rec.reset()
        snap = rec.snapshot()
        self.assertEqual(snap["total_video_frames"], 0)
        self.assertEqual(snap["total_analysis_frames"], 0)
        self.assertEqual(snap["skipped_frames"], 0)
        self.assertEqual(snap["events_emitted"], 0)

    def test_snapshot_contains_expected_keys(self):
        rec = self._rec()
        for key in ("session_id", "clip_id", "total_video_frames",
                    "total_analysis_frames", "skipped_frames",
                    "events_emitted", "events_updated"):
            self.assertIn(key, rec.snapshot())

    def test_compute_clip_id_in_metrics(self):
        rec = self._rec()
        self.assertEqual(rec.compute().clip_id, "video_595")

    def test_compute_session_id_in_metrics(self):
        rec = self._rec()
        self.assertEqual(rec.compute().session_id, "test_session")


# ===========================================================================
# TestTrackComparison
# ===========================================================================


class TestTrackComparison(unittest.TestCase):

    def test_both_empty_returns_failed(self):
        r = compare_tracks([], [], clip_id="c")
        self.assertEqual(r.classification, VALIDATION_FAILED)
        self.assertEqual(r.match_rate, 0.0)

    def test_no_streaming_returns_failed(self):
        r = compare_tracks([], [_track(0, 100, 200)], clip_id="c")
        self.assertEqual(r.classification, VALIDATION_FAILED)
        self.assertEqual(r.total_streaming_rows, 0)

    def test_no_batch_returns_failed(self):
        r = compare_tracks([_track(0, 100, 200)], [], clip_id="c")
        self.assertEqual(r.classification, VALIDATION_FAILED)

    def test_identical_tracks_full_match(self):
        rows = [_track(f, 100.0, 200.0) for f in range(5)]
        r = compare_tracks(rows, rows, clip_id="c")
        self.assertEqual(r.match_rate, 1.0)
        self.assertEqual(r.matched_rows, 5)

    def test_tracks_within_distance_match(self):
        s = [_track(0, 100.0, 200.0)]
        b = [_track(0, 140.0, 200.0)]  # dist=40 < default 50
        r = compare_tracks(s, b, match_distance_px=50.0, clip_id="c")
        self.assertEqual(r.match_rate, 1.0)

    def test_tracks_beyond_distance_no_match(self):
        s = [_track(0, 100.0, 200.0)]
        b = [_track(0, 200.0, 200.0)]  # dist=100 > 50
        r = compare_tracks(s, b, match_distance_px=50.0, clip_id="c")
        self.assertEqual(r.match_rate, 0.0)
        self.assertEqual(r.classification, VALIDATION_FAILED)

    def test_tracks_different_frames_no_match(self):
        s = [_track(0, 100.0, 200.0)]
        b = [_track(1, 100.0, 200.0)]
        r = compare_tracks(s, b, clip_id="c")
        self.assertEqual(r.match_rate, 0.0)

    def test_classification_acceptable(self):
        rows = [_track(f, float(f * 10), 100.0) for f in range(10)]
        r = compare_tracks(rows, rows, acceptable_rate=0.85)
        self.assertEqual(r.classification, VALIDATION_ACCEPTABLE)

    def test_classification_degraded(self):
        s = [_track(f, float(f * 10), 100.0) for f in range(10)]
        b = [_track(f, float(f * 10), 100.0) for f in range(7)]  # 7/10 = 0.7
        r = compare_tracks(s, b, acceptable_rate=0.85, degraded_rate=0.60)
        self.assertEqual(r.classification, VALIDATION_DEGRADED)

    def test_classification_failed(self):
        s = [_track(f, float(f * 10), 100.0) for f in range(10)]
        b = [_track(f, float(f * 10), 100.0) for f in range(4)]  # 4/10 = 0.4
        r = compare_tracks(s, b, acceptable_rate=0.85, degraded_rate=0.60)
        self.assertEqual(r.classification, VALIDATION_FAILED)

    def test_clip_id_in_result(self):
        self.assertEqual(compare_tracks([], [], clip_id="video_595").clip_id, "video_595")

    def test_total_counts_correct(self):
        s = [_track(0, 10.0, 10.0), _track(1, 20.0, 20.0)]
        b = [_track(0, 10.0, 10.0), _track(1, 20.0, 20.0), _track(2, 30.0, 30.0)]
        r = compare_tracks(s, b)
        self.assertEqual(r.total_streaming_rows, 2)
        self.assertEqual(r.total_batch_rows, 3)

    def test_batch_coverage_computed(self):
        s = [_track(0, 10.0, 10.0)]
        b = [_track(0, 10.0, 10.0), _track(1, 50.0, 50.0)]
        r = compare_tracks(s, b)
        # Only frame 0 matched → coverage = 1/2
        self.assertAlmostEqual(r.batch_coverage, 0.5, places=3)

    def test_as_dict_contains_all_csv_fields(self):
        r = compare_tracks([], [])
        d = r.as_dict()
        for f in TRACK_COMPARISON_CSV_FIELDS:
            self.assertIn(f, d)


# ===========================================================================
# TestEventComparison
# ===========================================================================


class TestEventComparison(unittest.TestCase):

    def test_both_empty_returns_failed(self):
        r = compare_events([], [], clip_id="c")
        self.assertEqual(r.classification, VALIDATION_FAILED)
        self.assertEqual(r.overlap_rate, 0.0)

    def test_identical_events_full_overlap(self):
        evs = [_event("possession_candidate", 0, 10)]
        r = compare_events(evs, evs, clip_id="c")
        self.assertEqual(r.overlap_rate, 1.0)
        self.assertEqual(r.matched_events, 1)

    def test_same_label_overlapping_frames_match(self):
        s = [_event("shot_approximate", 5, 15)]
        b = [_event("shot_approximate", 10, 20)]
        r = compare_events(s, b)
        self.assertEqual(r.matched_events, 1)

    def test_same_label_non_overlapping_frames_no_match(self):
        s = [_event("shot_approximate", 0, 5)]
        b = [_event("shot_approximate", 10, 15)]
        r = compare_events(s, b)
        self.assertEqual(r.matched_events, 0)

    def test_different_labels_no_match(self):
        s = [_event("possession_candidate", 0, 10)]
        b = [_event("shot_approximate", 0, 10)]
        r = compare_events(s, b)
        self.assertEqual(r.matched_events, 0)

    def test_overlap_rate_denominator_is_max(self):
        s = [_event("possession_candidate", 0, 10)]
        b = [
            _event("possession_candidate", 0, 10),
            _event("shot_approximate", 20, 30),
        ]
        r = compare_events(s, b)
        # matched=1, denom=max(1,2)=2
        self.assertAlmostEqual(r.overlap_rate, 0.5, places=4)

    def test_classification_acceptable(self):
        evs = [_event("possession_candidate", 0, 10)]
        r = compare_events(evs, evs, acceptable_rate=0.70)
        self.assertEqual(r.classification, VALIDATION_ACCEPTABLE)

    def test_classification_degraded(self):
        s = [_event("possession_candidate", 0, 10), _event("shot_approximate", 20, 30)]
        b = [
            _event("possession_candidate", 0, 10),
            _event("shot_approximate", 20, 30),
            _event("pass_simple", 40, 50),
        ]
        r = compare_events(s, b, acceptable_rate=0.70, degraded_rate=0.40)
        # matched=2, denom=3 → rate=0.667 → degraded
        self.assertEqual(r.classification, VALIDATION_DEGRADED)

    def test_classification_failed(self):
        s = [_event("possession_candidate", 0, 10)]
        b = [
            _event("shot_approximate", 5, 15),
            _event("pass_simple", 20, 30),
            _event("collision_dispute", 40, 50),
        ]
        r = compare_events(s, b, acceptable_rate=0.70, degraded_rate=0.40)
        self.assertEqual(r.classification, VALIDATION_FAILED)

    def test_each_batch_event_consumed_once(self):
        # Two streaming events match the same batch event — only one match counted
        s = [
            _event("possession_candidate", 0, 10),
            _event("possession_candidate", 5, 15),
        ]
        b = [_event("possession_candidate", 8, 12)]
        r = compare_events(s, b)
        self.assertEqual(r.matched_events, 1)

    def test_event_counts_in_result(self):
        s = [_event("possession_candidate", 0, 5)]
        b = [_event("shot_approximate", 10, 15), _event("pass_simple", 20, 25)]
        r = compare_events(s, b, clip_id="video_667")
        self.assertEqual(r.streaming_event_count, 1)
        self.assertEqual(r.batch_event_count, 2)
        self.assertEqual(r.clip_id, "video_667")

    def test_as_dict_contains_all_csv_fields(self):
        r = compare_events([], [])
        d = r.as_dict()
        for f in EVENT_COMPARISON_CSV_FIELDS:
            self.assertIn(f, d)


# ===========================================================================
# TestLiveValidationConfig
# ===========================================================================


class TestLiveValidationConfig(unittest.TestCase):

    def test_defaults(self):
        cfg = LiveValidationConfig(clip_id="video_595")
        self.assertEqual(cfg.inference_mode, "precomputed")
        self.assertEqual(cfg.fps, 30.0)
        self.assertEqual(cfg.start_frame, 0)
        self.assertEqual(cfg.end_frame, -1)

    def test_as_dict_has_all_fields(self):
        cfg = LiveValidationConfig(clip_id="video_595")
        d = cfg.as_dict()
        for key in ("clip_id", "video_path", "tracks_csv", "events_json",
                    "fps", "start_frame", "end_frame", "inference_mode", "budget_ms", "notes"):
            self.assertIn(key, d)

    def test_clip_id_in_dict(self):
        cfg = LiveValidationConfig(clip_id="video_480")
        self.assertEqual(cfg.as_dict()["clip_id"], "video_480")


# ===========================================================================
# TestRuntimeMetrics
# ===========================================================================


class TestRuntimeMetrics(unittest.TestCase):

    def _m(self, **kw) -> RuntimeMetrics:
        defaults = dict(
            clip_id="video_595",
            session_id="s1",
            video_fps=29.5,
            analysis_fps=28.1,
            mean_latency_ms=25.0,
            p95_latency_ms=40.0,
            skipped_frames=3,
            total_video_frames=300,
            total_analysis_frames=295,
            events_emitted=12,
            events_updated=5,
            classification=VALIDATION_ACCEPTABLE,
        )
        defaults.update(kw)
        return RuntimeMetrics(**defaults)

    def test_as_dict_contains_all_csv_fields(self):
        d = self._m().as_dict()
        for f in RUNTIME_METRICS_CSV_FIELDS:
            self.assertIn(f, d)

    def test_as_dict_field_count_matches_csv_fields(self):
        d = self._m().as_dict()
        self.assertEqual(len(d), len(RUNTIME_METRICS_CSV_FIELDS))

    def test_is_frozen(self):
        m = self._m()
        with self.assertRaises(Exception):
            m.video_fps = 99.0  # type: ignore[misc]


# ===========================================================================
# TestCSVOutput
# ===========================================================================


class TestCSVOutput(unittest.TestCase):

    def _metrics(self, clip_id="video_595") -> RuntimeMetrics:
        return RuntimeMetrics(
            clip_id=clip_id, session_id="s1",
            video_fps=29.5, analysis_fps=28.1,
            mean_latency_ms=25.0, p95_latency_ms=40.0,
            skipped_frames=0, total_video_frames=100,
            total_analysis_frames=98,
            events_emitted=5, events_updated=2,
            classification=VALIDATION_ACCEPTABLE,
        )

    def test_runtime_metrics_csv_has_header(self):
        text = runtime_metrics_csv_text([self._metrics()])
        first_line = text.splitlines()[0]
        self.assertIn("clip_id", first_line)
        self.assertIn("video_fps", first_line)

    def test_runtime_metrics_csv_has_data_row(self):
        text = runtime_metrics_csv_text([self._metrics()])
        lines = text.strip().splitlines()
        self.assertEqual(len(lines), 2)  # header + 1 row

    def test_runtime_metrics_csv_empty_list_has_only_header(self):
        text = runtime_metrics_csv_text([])
        lines = text.strip().splitlines()
        self.assertEqual(len(lines), 1)

    def test_track_comparison_csv_has_header(self):
        r = compare_tracks([], [])
        text = track_comparison_csv_text([r])
        self.assertIn("match_rate", text.splitlines()[0])

    def test_event_comparison_csv_has_header(self):
        r = compare_events([], [])
        text = event_comparison_csv_text([r])
        self.assertIn("overlap_rate", text.splitlines()[0])

    def test_manifest_csv_has_header(self):
        text = manifest_csv_text([
            {"asset_id": "config", "asset_type": "configuration",
             "path": "config.yaml", "is_versioned": "true",
             "role": "clip_config", "notes": ""}
        ])
        first = text.splitlines()[0]
        for f in MANIFEST_CSV_FIELDS:
            self.assertIn(f, first)

    def test_summary_md_contains_objective(self):
        text = summary_md_text([], [], [])
        self.assertIn("Objetivo", text)

    def test_summary_md_contains_metrics_header(self):
        text = summary_md_text([self._metrics()], [], [])
        self.assertIn("Metricas de Runtime", text)
        self.assertIn("video_595", text)

    def test_summary_md_contains_track_section(self):
        r = compare_tracks([], [])
        text = summary_md_text([], [r], [])
        self.assertIn("Tracks", text)

    def test_summary_md_contains_event_section(self):
        r = compare_events([], [])
        text = summary_md_text([], [], [r])
        self.assertIn("Eventos", text)


if __name__ == "__main__":
    unittest.main()
