from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import unittest

from futbotmx.live_playback_minimap import (
    MINIMAP_CALIBRATION_MIN_CONFIDENCE,
    MINIMAP_QUALITY_FALLBACK,
    MINIMAP_QUALITY_RECTIFIED,
    MINIMAP_QUALITY_UNAVAILABLE,
    LiveMinimapConfig,
    LiveMinimapEngine,
    LiveMinimapFrame,
    MinimapCalibration,
    _TrailBuffer,
    _apply_homography,
    _norm_zone,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _identity_homography() -> tuple:
    return ((1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0))


def _scale_homography(sx: float, sy: float) -> tuple:
    return ((sx, 0.0, 0.0), (0.0, sy, 0.0), (0.0, 0.0, 1.0))


def _row(class_name: str, cx: float, cy: float, track_id: str, team: str = "unknown", state: str = "active", confidence: float = 0.9) -> dict:
    return {
        "class": class_name,
        "center_x": cx,
        "center_y": cy,
        "track_id": track_id,
        "team": team,
        "state": state,
        "confidence": confidence,
    }


def _ball(cx: float = 500.0, cy: float = 300.0) -> dict:
    return _row("ball", cx, cy, "ball_01", "neutral")


def _robot(track_id: str = "ally_01", cx: float = 200.0, cy: float = 300.0, team: str = "ally") -> dict:
    return _row("ally_robot", cx, cy, track_id, team)


def _precomputed_row(track_id: str, x_norm: float, y_norm: float, class_name: str = "ally_robot", team: str = "ally") -> dict:
    return {
        "class": class_name,
        "track_id": track_id,
        "team": team,
        "x_norm": str(x_norm),
        "y_norm": str(y_norm),
        "calibration_confidence": "0.81",
        "confidence": "0.9",
        "state": "active",
    }


def _calibration_with_scale(sx: float = 1.0 / 1920, sy: float = 1.0 / 1080, confidence: float = 0.85) -> MinimapCalibration:
    return MinimapCalibration.from_homography(
        homography=_scale_homography(sx, sy),
        image_width=1920.0,
        image_height=1080.0,
        confidence=confidence,
        source="test_homography",
    )


def _engine(**kwargs) -> LiveMinimapEngine:
    cfg = LiveMinimapConfig(session_id="test", fps=30.0, trail_length=5, possession_distance_px=100.0)
    cal = _calibration_with_scale()
    return LiveMinimapEngine(cal, cfg)


# ---------------------------------------------------------------------------
# Tarea 31.1 - Mini-mapa sincronizado
# ---------------------------------------------------------------------------

class TestMinimapCalibration(unittest.TestCase):
    def test_from_homography_sets_rectified_status(self) -> None:
        cal = _calibration_with_scale()
        self.assertEqual(cal.status, MINIMAP_QUALITY_RECTIFIED)
        self.assertTrue(cal.homography is not None)

    def test_from_image_extent_sets_fallback(self) -> None:
        cal = MinimapCalibration.from_image_extent(1920.0, 1080.0)
        self.assertEqual(cal.status, MINIMAP_QUALITY_FALLBACK)
        self.assertIsNone(cal.homography)

    def test_unavailable_returns_unavailable_status(self) -> None:
        cal = MinimapCalibration.unavailable()
        self.assertEqual(cal.status, MINIMAP_QUALITY_UNAVAILABLE)
        self.assertEqual(cal.confidence, 0.0)

    def test_transform_with_scale_homography(self) -> None:
        cal = _calibration_with_scale(sx=1.0 / 1920, sy=1.0 / 1080)
        x_norm, y_norm, quality = cal.transform(960.0, 540.0)
        self.assertAlmostEqual(x_norm, 0.5, places=4)
        self.assertAlmostEqual(y_norm, 0.5, places=4)
        self.assertEqual(quality, MINIMAP_QUALITY_RECTIFIED)

    def test_transform_clips_to_unit_range(self) -> None:
        cal = _calibration_with_scale(sx=1.0 / 1920, sy=1.0 / 1080)
        x_norm, y_norm, _ = cal.transform(5000.0, -100.0)
        self.assertLessEqual(x_norm, 1.0)
        self.assertGreaterEqual(x_norm, 0.0)
        self.assertLessEqual(y_norm, 1.0)
        self.assertGreaterEqual(y_norm, 0.0)

    def test_transform_fallback_normalizes_by_image(self) -> None:
        cal = MinimapCalibration.from_image_extent(1920.0, 1080.0)
        x_norm, y_norm, quality = cal.transform(192.0, 108.0)
        self.assertAlmostEqual(x_norm, 0.1, places=5)
        self.assertAlmostEqual(y_norm, 0.1, places=5)
        self.assertEqual(quality, MINIMAP_QUALITY_FALLBACK)

    def test_transform_unavailable_returns_center(self) -> None:
        cal = MinimapCalibration.unavailable()
        x_norm, y_norm, quality = cal.transform(100.0, 200.0)
        self.assertEqual(x_norm, 0.5)
        self.assertEqual(y_norm, 0.5)
        self.assertEqual(quality, MINIMAP_QUALITY_UNAVAILABLE)

    def test_reliable_above_confidence_threshold(self) -> None:
        cal = _calibration_with_scale(confidence=0.85)
        self.assertTrue(cal.reliable)

    def test_reliable_false_below_threshold(self) -> None:
        cal = _calibration_with_scale(confidence=0.10)
        self.assertFalse(cal.reliable)

    def test_reliable_false_for_fallback(self) -> None:
        cal = MinimapCalibration.from_image_extent(1920.0, 1080.0)
        self.assertFalse(cal.reliable)

    def test_from_clip_calibration_usable(self) -> None:
        class FakeCalibration:
            usable = True
            confidence = 0.80
            image_width = 1920
            image_height = 1080
            homography = _scale_homography(1.0 / 1920, 1.0 / 1080)
            calibration_id = "fake_cal"
        cal = MinimapCalibration.from_clip_calibration(FakeCalibration())
        self.assertEqual(cal.status, MINIMAP_QUALITY_RECTIFIED)
        self.assertAlmostEqual(cal.confidence, 0.80)

    def test_from_clip_calibration_unusable(self) -> None:
        class FakeCalibration:
            usable = False
            confidence = 0.10
            image_width = 1920
            image_height = 1080
            homography = None
            calibration_id = "fake_fallback"
        cal = MinimapCalibration.from_clip_calibration(FakeCalibration())
        self.assertEqual(cal.status, MINIMAP_QUALITY_FALLBACK)

    def test_as_dict_has_required_keys(self) -> None:
        cal = _calibration_with_scale()
        d = cal.as_dict()
        for key in ("status", "confidence", "has_homography", "source", "reliable"):
            self.assertIn(key, d)


class TestTrailBuffer(unittest.TestCase):
    def test_buffer_starts_empty(self) -> None:
        buf = _TrailBuffer(trail_length=5)
        self.assertEqual(buf.trail("ally_01"), [])
        self.assertEqual(buf.all_trails(), {})

    def test_push_adds_position(self) -> None:
        buf = _TrailBuffer(trail_length=5)
        buf.push("ally_01", 0.5, 0.3)
        self.assertEqual(buf.trail("ally_01"), [(0.5, 0.3)])

    def test_trail_respects_max_length(self) -> None:
        buf = _TrailBuffer(trail_length=3)
        for i in range(6):
            buf.push("ally_01", i * 0.1, 0.5)
        trail = buf.trail("ally_01")
        self.assertEqual(len(trail), 3)

    def test_different_tracks_independent(self) -> None:
        buf = _TrailBuffer(trail_length=5)
        buf.push("ally_01", 0.1, 0.2)
        buf.push("ally_02", 0.5, 0.6)
        self.assertEqual(len(buf.trail("ally_01")), 1)
        self.assertEqual(len(buf.trail("ally_02")), 1)
        self.assertNotEqual(buf.trail("ally_01"), buf.trail("ally_02"))

    def test_clear_removes_all_trails(self) -> None:
        buf = _TrailBuffer(trail_length=5)
        buf.push("ally_01", 0.5, 0.3)
        buf.clear()
        self.assertEqual(buf.all_trails(), {})

    def test_prune_removes_inactive_tracks(self) -> None:
        buf = _TrailBuffer(trail_length=5)
        buf.push("ally_01", 0.1, 0.2)
        buf.push("ally_02", 0.5, 0.6)
        buf.prune_to({"ally_01"})
        self.assertIn("ally_01", buf.all_trails())
        self.assertNotIn("ally_02", buf.all_trails())

    def test_all_trails_returns_copy(self) -> None:
        buf = _TrailBuffer(trail_length=5)
        buf.push("ally_01", 0.1, 0.2)
        trails = buf.all_trails()
        trails["ally_01"].append((99.0, 99.0))
        self.assertEqual(len(buf.trail("ally_01")), 1)


class TestApplyHomography(unittest.TestCase):
    def test_identity_homography(self) -> None:
        H = _identity_homography()
        x, y = _apply_homography(H, 100.0, 200.0)
        self.assertAlmostEqual(x, 100.0)
        self.assertAlmostEqual(y, 200.0)

    def test_scale_homography(self) -> None:
        H = _scale_homography(0.5, 0.25)
        x, y = _apply_homography(H, 100.0, 200.0)
        self.assertAlmostEqual(x, 50.0)
        self.assertAlmostEqual(y, 50.0)

    def test_raises_on_degenerate(self) -> None:
        H = ((0.0, 0.0, 0.0), (0.0, 0.0, 0.0), (0.0, 0.0, 0.0))
        with self.assertRaises(ValueError):
            _apply_homography(H, 1.0, 1.0)


class TestNormZone(unittest.TestCase):
    def test_defensive_third_y_axis(self) -> None:
        self.assertEqual(_norm_zone(0.5, 0.1, "y"), "defensive_third")

    def test_middle_third_y_axis(self) -> None:
        self.assertEqual(_norm_zone(0.5, 0.5, "y"), "middle_third")

    def test_attacking_third_y_axis(self) -> None:
        self.assertEqual(_norm_zone(0.5, 0.9, "y"), "attacking_third")

    def test_x_axis_zone(self) -> None:
        self.assertEqual(_norm_zone(0.1, 0.5, "x"), "defensive_third")
        self.assertEqual(_norm_zone(0.9, 0.5, "x"), "attacking_third")


class TestLiveMinimapEnginePoints(unittest.TestCase):
    def test_push_frame_returns_minimap_frame(self) -> None:
        eng = _engine()
        result = eng.push_frame(0, [_ball(), _robot()])
        self.assertIsInstance(result, LiveMinimapFrame)

    def test_push_frame_creates_points_for_all_rows(self) -> None:
        eng = _engine()
        result = eng.push_frame(0, [_ball(), _robot("ally_01"), _robot("ally_02", 300.0)])
        self.assertEqual(len(result.points), 3)

    def test_point_has_required_fields(self) -> None:
        eng = _engine()
        result = eng.push_frame(0, [_ball()])
        point = result.points[0]
        for key in ("track_id", "class", "team", "x_norm", "y_norm", "quality", "state", "confidence"):
            self.assertIn(key, point)

    def test_point_x_norm_y_norm_in_unit_range(self) -> None:
        eng = _engine()
        result = eng.push_frame(0, [_ball(960.0, 540.0)])
        point = result.points[0]
        self.assertGreaterEqual(float(point["x_norm"]), 0.0)
        self.assertLessEqual(float(point["x_norm"]), 1.0)
        self.assertGreaterEqual(float(point["y_norm"]), 0.0)
        self.assertLessEqual(float(point["y_norm"]), 1.0)

    def test_precomputed_x_norm_used_directly(self) -> None:
        eng = _engine()
        row = _precomputed_row("ally_01", 0.35, 0.72)
        result = eng.push_frame(0, [row])
        point = result.points[0]
        self.assertAlmostEqual(float(point["x_norm"]), 0.35, places=4)
        self.assertAlmostEqual(float(point["y_norm"]), 0.72, places=4)
        self.assertEqual(point["quality"], MINIMAP_QUALITY_RECTIFIED)

    def test_fallback_calibration_marks_quality(self) -> None:
        cal = MinimapCalibration.from_image_extent(1920.0, 1080.0)
        eng = LiveMinimapEngine(cal)
        result = eng.push_frame(0, [_ball(100.0, 200.0)])
        self.assertEqual(result.points[0]["quality"], MINIMAP_QUALITY_FALLBACK)

    def test_hide_unreliable_true_for_fallback_calibration(self) -> None:
        cal = MinimapCalibration.from_image_extent(1920.0, 1080.0)
        eng = LiveMinimapEngine(cal)
        result = eng.push_frame(0, [_ball()])
        self.assertTrue(result.hide_unreliable)

    def test_hide_unreliable_false_for_reliable_calibration(self) -> None:
        eng = _engine()
        result = eng.push_frame(0, [_ball()])
        self.assertFalse(result.hide_unreliable)

    def test_calibration_metadata_in_frame(self) -> None:
        eng = _engine()
        result = eng.push_frame(0, [_ball()])
        self.assertEqual(result.calibration_status, MINIMAP_QUALITY_RECTIFIED)
        self.assertGreater(result.calibration_confidence, 0.0)

    def test_empty_rows_returns_empty_points(self) -> None:
        eng = _engine()
        result = eng.push_frame(0, [])
        self.assertEqual(result.points, [])


class TestLiveMinimapTrails(unittest.TestCase):
    def test_trail_builds_across_frames(self) -> None:
        eng = _engine()
        for f in range(4):
            eng.push_frame(f, [_robot("ally_01", 100.0 + f * 10, 200.0)])
        last = eng.push_frame(4, [_robot("ally_01", 140.0, 200.0)])
        trail = last.trails.get("ally_01", [])
        self.assertGreater(len(trail), 1)

    def test_trail_respects_configured_length(self) -> None:
        cfg = LiveMinimapConfig(trail_length=3, fps=30.0)
        eng = LiveMinimapEngine(_calibration_with_scale(), cfg)
        for f in range(10):
            result = eng.push_frame(f, [_robot("ally_01", f * 10.0, 200.0)])
        trail = result.trails.get("ally_01", [])
        self.assertLessEqual(len(trail), 3)

    def test_trail_cleared_on_backward_seek(self) -> None:
        eng = _engine()
        for f in range(5):
            eng.push_frame(f, [_robot("ally_01", f * 10.0, 200.0)])
        eng.seek(0)
        result = eng.push_frame(0, [_robot("ally_01", 100.0, 200.0)])
        self.assertEqual(len(result.trails.get("ally_01", [])), 1)

    def test_seek_forward_preserves_trails(self) -> None:
        eng = _engine()
        for f in range(3):
            eng.push_frame(f, [_robot("ally_01", f * 10.0, 200.0)])
        eng.seek(10)
        result = eng.push_frame(10, [_robot("ally_01", 100.0, 200.0)])
        trail = result.trails.get("ally_01", [])
        self.assertGreater(len(trail), 1)

    def test_seek_backward_increments_reset_count(self) -> None:
        eng = _engine()
        eng.push_frame(10, [_robot()])
        eng.seek(0)
        self.assertEqual(eng.reset_count, 1)

    def test_seek_forward_does_not_reset(self) -> None:
        eng = _engine()
        eng.push_frame(0, [_robot()])
        reset = eng.seek(10)
        self.assertFalse(reset)
        self.assertEqual(eng.reset_count, 0)

    def test_inactive_tracks_pruned_from_trails(self) -> None:
        cfg = LiveMinimapConfig(trail_length=5, fps=30.0, prune_inactive_trails=True)
        eng = LiveMinimapEngine(_calibration_with_scale(), cfg)
        eng.push_frame(0, [_robot("ally_01")])
        result = eng.push_frame(1, [_robot("ally_02", 300.0)])
        self.assertNotIn("ally_01", result.trails)
        self.assertIn("ally_02", result.trails)

    def test_ball_trail_included(self) -> None:
        eng = _engine()
        for f in range(3):
            eng.push_frame(f, [_ball(100.0 + f * 5, 200.0)])
        result = eng.push_frame(3, [_ball(115.0, 200.0)])
        self.assertIn("ball_01", result.trails)


class TestLiveMinimapMetrics(unittest.TestCase):
    def test_possession_detected_when_ball_near_robot(self) -> None:
        cfg = LiveMinimapConfig(fps=30.0, possession_distance_px=150.0)
        eng = LiveMinimapEngine(_calibration_with_scale(), cfg)
        result = eng.push_frame(0, [_ball(200.0, 300.0), _robot("ally_01", 220.0, 300.0, team="ally")])
        self.assertEqual(result.metrics["possession_team"], "ally")
        self.assertEqual(result.metrics["possession_robot_id"], "ally_01")

    def test_no_possession_when_ball_far_from_robot(self) -> None:
        cfg = LiveMinimapConfig(fps=30.0, possession_distance_px=50.0)
        eng = LiveMinimapEngine(_calibration_with_scale(), cfg)
        result = eng.push_frame(0, [_ball(200.0, 300.0), _robot("ally_01", 800.0, 300.0)])
        self.assertEqual(result.metrics["possession_team"], "none")

    def test_no_possession_when_no_ball(self) -> None:
        eng = _engine()
        result = eng.push_frame(0, [_robot("ally_01")])
        self.assertEqual(result.metrics["possession_team"], "none")

    def test_active_zone_computed_from_ball_position(self) -> None:
        cal = _calibration_with_scale(sx=1.0 / 1920, sy=1.0 / 1080)
        eng = LiveMinimapEngine(cal)
        result = eng.push_frame(0, [_precomputed_row("ball_01", 0.5, 0.85, "ball", "neutral")])
        self.assertEqual(result.metrics["active_zone"], "attacking_third")

    def test_active_zone_defensive_third(self) -> None:
        cal = _calibration_with_scale(sx=1.0 / 1920, sy=1.0 / 1080)
        eng = LiveMinimapEngine(cal)
        result = eng.push_frame(0, [_precomputed_row("ball_01", 0.5, 0.1, "ball", "neutral")])
        self.assertEqual(result.metrics["active_zone"], "defensive_third")

    def test_ball_speed_computed_from_consecutive_frames(self) -> None:
        cal = _calibration_with_scale(sx=1.0 / 1920, sy=1.0 / 1080)
        eng = LiveMinimapEngine(cal, LiveMinimapConfig(fps=30.0))
        eng.push_frame(0, [_precomputed_row("ball_01", 0.0, 0.5, "ball")])
        result = eng.push_frame(1, [_precomputed_row("ball_01", 0.1, 0.5, "ball")])
        speed = result.metrics["ball_speed_norm_per_sec"]
        self.assertGreater(speed, 0.0)
        self.assertAlmostEqual(speed, 0.1 * 30.0, places=3)

    def test_ball_speed_zero_on_first_frame(self) -> None:
        eng = _engine()
        result = eng.push_frame(0, [_ball()])
        self.assertEqual(result.metrics["ball_speed_norm_per_sec"], 0.0)

    def test_tracking_confidence_is_average(self) -> None:
        eng = _engine()
        result = eng.push_frame(0, [
            _row("ally_robot", 100.0, 200.0, "ally_01", "ally", confidence=0.8),
            _row("ally_robot", 300.0, 200.0, "ally_02", "ally", confidence=0.6),
        ])
        tc = result.metrics["tracking_confidence"]
        self.assertAlmostEqual(tc, 0.7, places=4)

    def test_tracking_confidence_excludes_lost_tracks(self) -> None:
        eng = _engine()
        rows = [
            _row("ally_robot", 100.0, 200.0, "ally_01", "ally", state="active", confidence=1.0),
            _row("ally_robot", 300.0, 200.0, "ally_02", "ally", state="lost", confidence=0.5),
        ]
        result = eng.push_frame(0, rows)
        self.assertAlmostEqual(result.metrics["tracking_confidence"], 1.0, places=4)

    def test_calibration_metrics_in_output(self) -> None:
        eng = _engine()
        result = eng.push_frame(0, [_ball()])
        self.assertIn("calibration_confidence", result.metrics)
        self.assertIn("calibration_reliable", result.metrics)
        self.assertTrue(result.metrics["calibration_reliable"])

    def test_metrics_keys_present(self) -> None:
        eng = _engine()
        result = eng.push_frame(0, [_ball()])
        for key in ("possession_team", "active_zone", "ball_speed_norm_per_sec", "tracking_confidence", "calibration_confidence"):
            self.assertIn(key, result.metrics)


class TestLiveMinimapFrameOutput(unittest.TestCase):
    def test_as_dict_structure(self) -> None:
        eng = _engine()
        result = eng.push_frame(0, [_ball(), _robot()])
        d = result.as_dict()
        for key in ("frame", "timestamp_sec", "session_id", "calibration", "points", "trails", "metrics"):
            self.assertIn(key, d)

    def test_calibration_dict_in_as_dict(self) -> None:
        eng = _engine()
        result = eng.push_frame(0, [_ball()])
        cal_dict = result.as_dict()["calibration"]
        for key in ("status", "confidence", "source", "hide_unreliable"):
            self.assertIn(key, cal_dict)

    def test_timestamp_computed_from_fps(self) -> None:
        eng = _engine()
        result = eng.push_frame(30, [])
        self.assertAlmostEqual(result.timestamp_sec, 1.0, places=5)

    def test_trails_serializable(self) -> None:
        eng = _engine()
        for f in range(3):
            eng.push_frame(f, [_robot("ally_01")])
        result = eng.push_frame(3, [_robot("ally_01")])
        d = result.as_dict()
        trails = d["trails"]
        self.assertIsInstance(trails, dict)
        for v in trails.values():
            self.assertIsInstance(v, list)

    def test_update_calibration_at_runtime(self) -> None:
        cal_fallback = MinimapCalibration.from_image_extent(1920.0, 1080.0)
        eng = LiveMinimapEngine(cal_fallback)
        res1 = eng.push_frame(0, [_ball()])
        self.assertTrue(res1.hide_unreliable)
        eng.update_calibration(_calibration_with_scale())
        res2 = eng.push_frame(1, [_ball()])
        self.assertFalse(res2.hide_unreliable)

    def test_snapshot_has_required_keys(self) -> None:
        eng = _engine()
        snap = eng.snapshot()
        for key in ("session_id", "current_frame", "reset_count", "trail_count", "ball_history_length", "calibration"):
            self.assertIn(key, snap)


if __name__ == "__main__":
    unittest.main()
