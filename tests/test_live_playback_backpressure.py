"""Tests for live_playback_backpressure — Activity 32."""

import unittest

from futbotmx.live_playback_backpressure import (
    BACKPRESSURE_JSONL_FIELDS,
    DEGRADATION_ANALYSIS_PAUSED,
    DEGRADATION_DELAYED,
    DEGRADATION_LIVE,
    DEGRADATION_REPLAYING_CACHE,
    DEGRADATION_STATES,
    OVERLAY_SOURCE_EXACT,
    OVERLAY_SOURCE_FALLBACK,
    OVERLAY_SOURCE_NONE,
    BackpressureConfig,
    BackpressurePolicy,
    BackpressureStatus,
    DegradationMonitor,
    FrameQueue,
    FrameQueueEntry,
    PlaybackBackpressureEngine,
)


# ===========================================================================
# FrameQueue
# ===========================================================================


class TestFrameQueue(unittest.TestCase):

    def _q(self, max_size: int = 4) -> FrameQueue:
        return FrameQueue(max_size=max_size)

    # Construction -------------------------------------------------------

    def test_invalid_max_size_raises(self):
        with self.assertRaises(ValueError):
            FrameQueue(max_size=0)

    def test_initial_state(self):
        q = self._q()
        self.assertEqual(q.size, 0)
        self.assertEqual(q.dropped_count, 0)
        self.assertEqual(q.max_size, 4)

    # push / get ---------------------------------------------------------

    def test_push_and_get_exact(self):
        q = self._q()
        q.push(10, "data10")
        entry = q.get(10)
        self.assertIsNotNone(entry)
        self.assertEqual(entry.frame, 10)
        self.assertEqual(entry.data, "data10")

    def test_get_missing_returns_none(self):
        q = self._q()
        self.assertIsNone(q.get(99))

    def test_push_replaces_existing_frame(self):
        q = self._q()
        q.push(5, "old")
        q.push(5, "new")
        self.assertEqual(q.get(5).data, "new")
        self.assertEqual(q.size, 1)
        self.assertEqual(q.dropped_count, 0)

    def test_push_returns_zero_on_success(self):
        q = self._q()
        result = q.push(1, "x")
        self.assertEqual(result, 0)

    # Eviction -----------------------------------------------------------

    def test_evicts_oldest_when_full(self):
        q = self._q(max_size=2)
        q.push(1, "a")
        q.push(2, "b")
        q.push(3, "c")  # should evict frame 1
        self.assertIsNone(q.get(1))
        self.assertIsNotNone(q.get(2))
        self.assertIsNotNone(q.get(3))
        self.assertEqual(q.size, 2)

    def test_eviction_increments_dropped_count(self):
        q = self._q(max_size=2)
        q.push(1, "a")
        q.push(2, "b")
        q.push(3, "c")
        self.assertEqual(q.dropped_count, 1)

    def test_stale_frame_is_discarded(self):
        q = self._q(max_size=2)
        q.push(10, "a")
        q.push(20, "b")
        # push frame 5 — older than oldest queued (10) → discarded
        result = q.push(5, "stale")
        self.assertEqual(result, 0)  # push returns 0 (stale case)
        self.assertEqual(q.dropped_count, 1)
        self.assertIsNone(q.get(5))
        self.assertEqual(q.size, 2)

    def test_stale_does_not_change_size(self):
        q = self._q(max_size=2)
        q.push(10, "a")
        q.push(20, "b")
        q.push(3, "stale")
        self.assertEqual(q.size, 2)

    # get_best_for -------------------------------------------------------

    def test_get_best_for_exact_match(self):
        q = self._q()
        q.push(5, "five")
        frame, entry = q.get_best_for(5)
        self.assertEqual(frame, 5)
        self.assertEqual(entry.data, "five")

    def test_get_best_for_falls_back_to_earlier(self):
        q = self._q()
        q.push(3, "three")
        q.push(7, "seven")
        frame, entry = q.get_best_for(5)
        self.assertEqual(frame, 3)
        self.assertEqual(entry.data, "three")

    def test_get_best_for_returns_none_when_empty(self):
        q = self._q()
        frame, entry = q.get_best_for(10)
        self.assertIsNone(frame)
        self.assertIsNone(entry)

    def test_get_best_for_returns_none_when_all_frames_ahead(self):
        q = self._q()
        q.push(20, "ahead")
        frame, _ = q.get_best_for(10)
        self.assertIsNone(frame)

    def test_get_best_for_picks_highest_below_video_frame(self):
        q = self._q()
        q.push(1, "one")
        q.push(3, "three")
        q.push(5, "five")
        frame, _ = q.get_best_for(4)
        self.assertEqual(frame, 3)

    # discard_older_than -------------------------------------------------

    def test_discard_older_than_removes_correct_entries(self):
        q = self._q(max_size=8)
        for f in [1, 2, 3, 4, 5]:
            q.push(f, f)
        removed = q.discard_older_than(3)
        self.assertEqual(removed, 2)
        self.assertIsNone(q.get(1))
        self.assertIsNone(q.get(2))
        self.assertIsNotNone(q.get(3))

    def test_discard_older_than_returns_zero_when_nothing_removed(self):
        q = self._q()
        q.push(10, "x")
        self.assertEqual(q.discard_older_than(5), 0)

    # available_frames ---------------------------------------------------

    def test_available_frames_sorted(self):
        q = self._q(max_size=8)
        q.push(7, "g")
        q.push(3, "c")
        q.push(5, "e")
        self.assertEqual(q.available_frames(), [3, 5, 7])

    def test_available_frames_empty(self):
        self.assertEqual(self._q().available_frames(), [])

    # clear --------------------------------------------------------------

    def test_clear_empties_queue(self):
        q = self._q()
        q.push(1, "a")
        q.push(2, "b")
        q.clear()
        self.assertEqual(q.size, 0)
        self.assertEqual(q.available_frames(), [])

    def test_snapshot_contains_expected_keys(self):
        q = self._q()
        snap = q.snapshot()
        self.assertIn("size", snap)
        self.assertIn("max_size", snap)
        self.assertIn("dropped_count", snap)
        self.assertIn("available_frames", snap)


# ===========================================================================
# DegradationMonitor
# ===========================================================================


class TestDegradationMonitor(unittest.TestCase):

    def _m(self, delayed=3, paused=30) -> DegradationMonitor:
        return DegradationMonitor(
            delayed_threshold_frames=delayed,
            paused_threshold_frames=paused,
        )

    def test_initial_state_is_live(self):
        m = self._m()
        # No tick yet — lag=0, frames_since=0
        self.assertEqual(m.lag_frames, 0)
        self.assertIsNone(m.analysis_frame)

    def test_advance_with_immediate_analysis_stays_live(self):
        m = self._m()
        m.notify_analysis(0)
        state = m.advance(0)
        self.assertEqual(state, DEGRADATION_LIVE)

    def test_advance_without_analysis_becomes_delayed(self):
        m = self._m(delayed=3)
        m.notify_analysis(0)
        for f in range(1, 4):
            state = m.advance(f)
        self.assertEqual(state, DEGRADATION_DELAYED)

    def test_lag_equals_video_minus_analysis_frame(self):
        m = self._m()
        m.notify_analysis(5)
        m.advance(10)
        self.assertEqual(m.lag_frames, 5)

    def test_lag_is_zero_when_analysis_equals_video(self):
        m = self._m()
        m.notify_analysis(7)
        m.advance(7)
        self.assertEqual(m.lag_frames, 0)

    def test_lag_is_zero_when_analysis_ahead_of_video(self):
        # Analysis for future frame — lag cannot be negative
        m = self._m()
        m.notify_analysis(20)
        m.advance(10)
        self.assertEqual(m.lag_frames, 0)

    def test_state_transitions_to_replaying_cache(self):
        m = self._m(paused=10)
        m.notify_analysis(0)
        for f in range(1, 12):
            m.advance(f)
        # lag=11 > paused_threshold=10, but frames_since_analysis=11 >= 10 too
        # analysis_paused takes priority in that scenario — let's test pure cache:
        # Reset, give recent analysis but lag > paused_threshold via notify then big advance
        m2 = self._m(delayed=3, paused=10)
        m2.notify_analysis(0)
        # advance one step at a time, notifying occasionally to keep frames_since low
        for f in range(1, 6):
            m2.advance(f)
            m2.notify_analysis(0)  # always notify so frames_since=0
        # Now advance without notifying but lag > 10
        # video=6, analysis=0, lag=6 — not > 10 yet, but delayed
        m3 = self._m(delayed=3, paused=10)
        m3.notify_analysis(0)
        # Advance video to frame 11, constantly notifying to keep frames_since=0
        # but with analysis stuck at frame 0 (notify only frame 0, then nothing)
        # We need lag > 10 but frames_since < 10
        # Use notify_analysis(frame) for each step so frames_since resets but lag grows
        for f in range(1, 12):
            m3.notify_analysis(0)  # keep frames_since=0, analysis stuck at 0
            state = m3.advance(f)
        # lag = 11 - 0 = 11 > 10, frames_since=0 < 10 → replaying_cache
        self.assertEqual(state, DEGRADATION_REPLAYING_CACHE)

    def test_state_transitions_to_analysis_paused(self):
        m = self._m(paused=5)
        m.notify_analysis(0)
        for f in range(1, 7):
            state = m.advance(f)
        self.assertEqual(state, DEGRADATION_ANALYSIS_PAUSED)

    def test_explicit_pause_overrides_state(self):
        m = self._m()
        m.notify_analysis(0)
        m.advance(0)
        m.set_paused(True)
        state = m.advance(1)
        self.assertEqual(state, DEGRADATION_ANALYSIS_PAUSED)

    def test_resume_clears_explicit_pause(self):
        m = self._m()
        m.notify_analysis(0)
        m.set_paused(True)
        m.set_paused(False)
        state = m.advance(0)
        self.assertEqual(state, DEGRADATION_LIVE)

    def test_notify_analysis_resets_frames_since_analysis(self):
        m = self._m()
        for f in range(1, 5):
            m.advance(f)
        self.assertGreater(m.frames_since_analysis, 0)
        m.notify_analysis(4)
        m.advance(5)
        self.assertEqual(m.frames_since_analysis, 0)

    def test_reset_clears_all_state(self):
        m = self._m()
        m.notify_analysis(50)
        m.advance(100)
        m.reset(0)
        self.assertEqual(m.video_frame, 0)
        self.assertIsNone(m.analysis_frame)
        self.assertEqual(m.frames_since_analysis, 0)
        self.assertEqual(m.lag_frames, 0)

    def test_advance_same_frame_does_not_accumulate_lag(self):
        m = self._m()
        # Advance without analysis so frames_since_analysis grows.
        for f in range(1, 6):
            m.advance(f)
        after_first = m.frames_since_analysis
        m.advance(5)  # same frame again — should not increment further
        self.assertEqual(m.frames_since_analysis, after_first)

    def test_snapshot_has_required_keys(self):
        m = self._m()
        snap = m.snapshot()
        for key in ("video_frame", "analysis_frame", "lag_frames", "frames_since_analysis", "state"):
            self.assertIn(key, snap)


# ===========================================================================
# BackpressurePolicy
# ===========================================================================


class TestBackpressurePolicy(unittest.TestCase):

    def _policy(self, **kw) -> BackpressurePolicy:
        defaults = dict(
            budget_ms=33.3,
            skip_inference_at_lag=5,
            reduce_layers_at_lag=8,
            precomputed_consecutive_threshold=10,
            reducible_layers=("trails", "debug"),
        )
        defaults.update(kw)
        return BackpressurePolicy(**defaults)

    # skip_inference -------------------------------------------------

    def test_no_skip_when_live(self):
        p = self._policy()
        self.assertFalse(p.should_skip_inference(DEGRADATION_LIVE, 0))

    def test_no_skip_when_delayed_below_threshold(self):
        p = self._policy()
        self.assertFalse(p.should_skip_inference(DEGRADATION_DELAYED, 4))

    def test_skip_when_delayed_at_threshold(self):
        p = self._policy()
        self.assertTrue(p.should_skip_inference(DEGRADATION_DELAYED, 5))

    def test_skip_when_replaying_cache(self):
        p = self._policy()
        self.assertTrue(p.should_skip_inference(DEGRADATION_REPLAYING_CACHE, 0))

    def test_skip_when_analysis_paused(self):
        p = self._policy()
        self.assertTrue(p.should_skip_inference(DEGRADATION_ANALYSIS_PAUSED, 0))

    # layers_to_reduce -----------------------------------------------

    def test_no_layers_when_live(self):
        p = self._policy()
        self.assertEqual(p.layers_to_reduce(DEGRADATION_LIVE, 0), [])

    def test_no_layers_when_delayed_below_reduce_threshold(self):
        p = self._policy()
        self.assertEqual(p.layers_to_reduce(DEGRADATION_DELAYED, 7), [])

    def test_first_layer_only_when_delayed_at_threshold(self):
        p = self._policy()
        layers = p.layers_to_reduce(DEGRADATION_DELAYED, 8)
        self.assertEqual(layers, ["trails"])

    def test_all_layers_when_replaying_cache(self):
        p = self._policy()
        layers = p.layers_to_reduce(DEGRADATION_REPLAYING_CACHE, 0)
        self.assertEqual(layers, ["trails", "debug"])

    def test_all_layers_when_analysis_paused(self):
        p = self._policy()
        layers = p.layers_to_reduce(DEGRADATION_ANALYSIS_PAUSED, 0)
        self.assertEqual(layers, ["trails", "debug"])

    # precomputed recommendation -------------------------------------

    def test_no_precomputed_below_threshold(self):
        p = self._policy()
        self.assertFalse(p.should_switch_to_precomputed(9))

    def test_recommend_precomputed_at_threshold(self):
        p = self._policy()
        self.assertTrue(p.should_switch_to_precomputed(10))

    # select_fallback_frame ------------------------------------------

    def test_select_fallback_returns_best_frame(self):
        p = self._policy()
        result = p.select_fallback_frame([1, 3, 5, 7], 6)
        self.assertEqual(result, 5)

    def test_select_fallback_exact_match(self):
        p = self._policy()
        self.assertEqual(p.select_fallback_frame([3, 5, 7], 5), 5)

    def test_select_fallback_returns_none_when_empty(self):
        p = self._policy()
        self.assertIsNone(p.select_fallback_frame([], 10))

    def test_select_fallback_returns_none_when_all_ahead(self):
        p = self._policy()
        self.assertIsNone(p.select_fallback_frame([10, 20], 5))


# ===========================================================================
# PlaybackBackpressureEngine
# ===========================================================================


class TestPlaybackBackpressureEngine(unittest.TestCase):

    def _engine(self, **kw) -> PlaybackBackpressureEngine:
        defaults = dict(
            max_queue_size=8,
            delayed_threshold_frames=3,
            paused_threshold_frames=30,
            skip_inference_at_lag=5,
            reduce_layers_at_lag=8,
            precomputed_consecutive_threshold=10,
            budget_ms=33.3,
            reducible_layers=("trails", "debug"),
        )
        defaults.update(kw)
        return PlaybackBackpressureEngine(BackpressureConfig(**defaults))

    # Basic tick ---------------------------------------------------------

    def test_tick_returns_backpressure_status(self):
        e = self._engine()
        status = e.tick(0)
        self.assertIsInstance(status, BackpressureStatus)

    def test_initial_tick_is_live(self):
        e = self._engine()
        e.push_analysis_result(0, {})
        status = e.tick(0)
        self.assertEqual(status.degradation_state, DEGRADATION_LIVE)

    def test_tick_video_frame_matches(self):
        e = self._engine()
        status = e.tick(42)
        self.assertEqual(status.video_frame, 42)

    def test_tick_records_history(self):
        e = self._engine()
        e.tick(0)
        e.tick(1)
        snap = e.snapshot()
        self.assertEqual(snap["status_history_count"], 2)

    # Overlay source -----------------------------------------------------

    def test_overlay_exact_when_frame_matches(self):
        e = self._engine()
        e.push_analysis_result(5, "data")
        status = e.tick(5)
        self.assertEqual(status.overlay_source, OVERLAY_SOURCE_EXACT)
        self.assertEqual(status.overlay_frame, 5)

    def test_overlay_fallback_when_older_frame_available(self):
        e = self._engine()
        e.push_analysis_result(3, "data3")
        status = e.tick(7)
        self.assertEqual(status.overlay_source, OVERLAY_SOURCE_FALLBACK)
        self.assertEqual(status.overlay_frame, 3)

    def test_overlay_none_when_queue_empty(self):
        e = self._engine()
        status = e.tick(5)
        self.assertEqual(status.overlay_source, OVERLAY_SOURCE_NONE)
        self.assertIsNone(status.overlay_frame)

    # skip_inference flag ------------------------------------------------

    def test_no_skip_when_live_and_low_lag(self):
        e = self._engine()
        e.push_analysis_result(0, {})
        status = e.tick(0)
        self.assertFalse(status.skip_inference)

    def test_skip_when_delayed_and_high_lag(self):
        e = self._engine()
        e.push_analysis_result(0, {})
        # advance video without new analysis results
        for f in range(1, 6):
            e.tick(f)
        status = e.tick(6)
        # lag=6 >= skip_inference_at_lag=5 with state delayed → skip
        self.assertTrue(status.skip_inference)

    # reduce_layers flag -------------------------------------------------

    def test_no_layers_reduced_when_live(self):
        e = self._engine()
        e.push_analysis_result(0, {})
        status = e.tick(0)
        self.assertFalse(status.reduce_layers)
        self.assertEqual(status.reduced_layers, ())

    def test_layers_reduced_when_very_delayed(self):
        e = self._engine()
        e.push_analysis_result(0, {})
        for f in range(1, 10):
            e.tick(f)
        status = e.tick(10)
        self.assertTrue(status.reduce_layers)
        self.assertGreater(len(status.reduced_layers), 0)

    # consecutive_late_frames --------------------------------------------

    def test_consecutive_late_increments_for_late_results(self):
        e = self._engine()
        e.tick(10)
        e.push_analysis_result(5, {})  # 5 < 10 → late
        e.push_analysis_result(6, {})  # 6 < 10 → late
        status = e.tick(11)
        self.assertEqual(status.consecutive_late_frames, 2)

    def test_consecutive_late_resets_on_on_time_result(self):
        e = self._engine()
        e.tick(10)
        e.push_analysis_result(5, {})
        e.push_analysis_result(10, {})  # on-time → reset
        status = e.tick(11)
        self.assertEqual(status.consecutive_late_frames, 0)

    def test_recommend_precomputed_after_sustained_latency(self):
        e = self._engine(precomputed_consecutive_threshold=3)
        e.tick(20)
        e.push_analysis_result(10, {})
        e.push_analysis_result(11, {})
        e.push_analysis_result(12, {})
        status = e.tick(21)
        self.assertTrue(status.recommend_precomputed)

    # get_data -----------------------------------------------------------

    def test_get_data_returns_correct_data(self):
        e = self._engine()
        e.push_analysis_result(7, {"score": 42})
        data = e.get_data(7)
        self.assertEqual(data["score"], 42)

    def test_get_data_returns_none_for_missing_frame(self):
        e = self._engine()
        self.assertIsNone(e.get_data(99))

    def test_get_data_returns_none_for_none_frame(self):
        e = self._engine()
        self.assertIsNone(e.get_data(None))

    # seek ---------------------------------------------------------------

    def test_seek_clears_queue_and_history(self):
        e = self._engine()
        e.push_analysis_result(5, "d")
        e.tick(5)
        e.seek(0)
        snap = e.snapshot()
        self.assertEqual(snap["queue"]["size"], 0)
        self.assertEqual(snap["status_history_count"], 0)

    def test_seek_resets_consecutive_late(self):
        e = self._engine()
        e.tick(10)
        e.push_analysis_result(5, {})
        e.seek(0)
        status = e.tick(0)
        self.assertEqual(status.consecutive_late_frames, 0)

    # pause / resume -----------------------------------------------------

    def test_pause_transitions_to_analysis_paused(self):
        e = self._engine()
        e.push_analysis_result(0, {})
        e.tick(0)
        e.pause_analysis()
        status = e.tick(1)
        self.assertEqual(status.degradation_state, DEGRADATION_ANALYSIS_PAUSED)

    def test_resume_allows_live_state(self):
        e = self._engine()
        e.pause_analysis()
        e.resume_analysis()
        e.push_analysis_result(0, {})
        status = e.tick(0)
        self.assertEqual(status.degradation_state, DEGRADATION_LIVE)

    # emit_jsonl ---------------------------------------------------------

    def test_emit_jsonl_produces_valid_json_lines(self):
        e = self._engine()
        e.push_analysis_result(0, {})
        e.tick(0)
        e.tick(1)
        jsonl = e.emit_jsonl()
        lines = jsonl.strip().split("\n")
        self.assertEqual(len(lines), 2)
        for line in lines:
            import json
            obj = json.loads(line)
            self.assertIn("video_frame", obj)

    def test_emit_jsonl_empty_before_any_tick(self):
        e = self._engine()
        self.assertEqual(e.emit_jsonl(), "")

    # snapshot -----------------------------------------------------------

    def test_snapshot_has_required_keys(self):
        e = self._engine()
        snap = e.snapshot()
        for key in ("session_id", "config", "monitor", "queue", "consecutive_late_frames", "status_history_count"):
            self.assertIn(key, snap)

    def test_snapshot_config_reflects_settings(self):
        e = self._engine()
        self.assertEqual(e.snapshot()["config"]["max_queue_size"], 8)
        self.assertEqual(e.snapshot()["config"]["budget_ms"], 33.3)


# ===========================================================================
# BackpressureStatus
# ===========================================================================


class TestBackpressureStatus(unittest.TestCase):

    def _status(self, **kw) -> BackpressureStatus:
        defaults = dict(
            video_frame=10,
            analysis_frame=9,
            degradation_state=DEGRADATION_LIVE,
            lag_frames=1,
            frames_since_analysis=0,
            skip_inference=False,
            reduce_layers=False,
            reduced_layers=(),
            recommend_precomputed=False,
            overlay_frame=9,
            overlay_source=OVERLAY_SOURCE_FALLBACK,
            queue_size=1,
            dropped_frame_count=0,
            consecutive_late_frames=0,
            budget_ms=33.3,
        )
        defaults.update(kw)
        return BackpressureStatus(**defaults)

    def test_as_dict_contains_all_jsonl_fields(self):
        status = self._status()
        d = status.as_dict()
        for field_name in BACKPRESSURE_JSONL_FIELDS:
            self.assertIn(field_name, d, msg=f"Missing field: {field_name}")

    def test_as_dict_reduced_layers_is_list(self):
        status = self._status(reduced_layers=("trails",))
        self.assertIsInstance(status.as_dict()["reduced_layers"], list)

    def test_as_dict_values_match_fields(self):
        status = self._status(video_frame=42, degradation_state=DEGRADATION_DELAYED)
        d = status.as_dict()
        self.assertEqual(d["video_frame"], 42)
        self.assertEqual(d["degradation_state"], DEGRADATION_DELAYED)

    def test_status_is_frozen(self):
        status = self._status()
        with self.assertRaises(Exception):
            status.video_frame = 99  # type: ignore[misc]

    def test_degradation_states_constant_has_all_states(self):
        self.assertIn(DEGRADATION_LIVE, DEGRADATION_STATES)
        self.assertIn(DEGRADATION_DELAYED, DEGRADATION_STATES)
        self.assertIn(DEGRADATION_REPLAYING_CACHE, DEGRADATION_STATES)
        self.assertIn(DEGRADATION_ANALYSIS_PAUSED, DEGRADATION_STATES)

    def test_jsonl_fields_count(self):
        # Ensure no fields were accidentally added or removed
        status = self._status()
        d = status.as_dict()
        self.assertEqual(len(d), len(BACKPRESSURE_JSONL_FIELDS))


if __name__ == "__main__":
    unittest.main()
