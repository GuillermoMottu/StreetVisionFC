from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import unittest

from futbotmx.events.stream_detector import (
    STREAM_EVENT_JSONL_FIELDS,
    STREAM_EVENT_LABELS,
    STREAM_EVENT_STATUS_CANDIDATE,
    STREAM_EVENT_STATUS_CONFIRMED,
    STREAM_EVENT_STATUS_DISCARDED,
    STREAM_EVENT_STATUS_PROVISIONAL,
    StreamDetectorConfig,
    StreamEventCandidate,
    StreamEventDetector,
    _FrameBuffer,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _row(class_name: str, cx: float, cy: float, track_id: str, team: str = "unknown") -> dict:
    return {
        "class": class_name,
        "center_x": cx,
        "center_y": cy,
        "x": cx - 20,
        "y": cy - 30,
        "w": 40,
        "h": 60,
        "track_id": track_id,
        "team": team,
    }


def _ball(cx: float = 500.0, cy: float = 300.0) -> dict:
    return _row("ball", cx, cy, "ball_01")


def _robot(track_id: str = "ally_01", cx: float = 100.0, cy: float = 200.0, team: str = "ally") -> dict:
    return _row("ally_robot", cx, cy, track_id, team)


def _cfg(**kwargs) -> StreamDetectorConfig:
    defaults = dict(
        session_id="test",
        clip_id="clip_001",
        fps=30.0,
        window_frames=30,
        possession_distance_px=80.0,
        possession_min_frames=3,
        possession_confirm_frames=8,
        max_pass_gap_frames=10,
        collision_distance_px=50.0,
        collision_min_frames=3,
        shot_min_speed_px_per_sec=300.0,
        highlight_speed_threshold_px_per_sec=600.0,
        field_width=1920.0,
        field_height=1080.0,
    )
    defaults.update(kwargs)
    return StreamDetectorConfig(**defaults)


def _detector(**kwargs) -> StreamEventDetector:
    return StreamEventDetector(_cfg(**kwargs))


# ---------------------------------------------------------------------------
# Tarea 30.1 - Buffers temporales
# ---------------------------------------------------------------------------

class TestFrameBuffer(unittest.TestCase):
    def test_buffer_starts_empty(self) -> None:
        buf = _FrameBuffer(window_frames=10)
        self.assertEqual(buf.ball_history(), [])
        self.assertEqual(buf.robot_history(), [])

    def test_push_adds_frame(self) -> None:
        buf = _FrameBuffer(window_frames=10)
        buf.push(0, [_ball()])
        self.assertEqual(len(buf.ball_history()), 1)

    def test_buffer_evicts_old_frames(self) -> None:
        buf = _FrameBuffer(window_frames=5)
        for f in range(10):
            buf.push(f, [_ball(f * 10.0)])
        history = buf.ball_history()
        frames = [f for f, _ in history]
        self.assertTrue(min(frames) >= 5)

    def test_ball_history_returns_only_ball_rows(self) -> None:
        buf = _FrameBuffer(window_frames=10)
        buf.push(0, [_ball(), _robot()])
        history = buf.ball_history()
        self.assertEqual(len(history), 1)
        self.assertEqual(history[0][1]["class"], "ball")

    def test_robot_history_returns_only_robot_rows(self) -> None:
        buf = _FrameBuffer(window_frames=10)
        buf.push(0, [_ball(), _robot("ally_01"), _robot("ally_02", 200.0)])
        history = buf.robot_history()
        self.assertEqual(len(history), 2)

    def test_possession_history_detects_possession(self) -> None:
        buf = _FrameBuffer(window_frames=10)
        buf.push(0, [_ball(100.0, 200.0), _robot("ally_01", 110.0, 200.0)])
        history = buf.possession_history(possession_distance_px=80.0)
        self.assertEqual(len(history), 1)
        frame, robot_id, team, dist = history[0]
        self.assertEqual(robot_id, "ally_01")
        self.assertAlmostEqual(dist, 10.0, places=1)

    def test_possession_history_excludes_far_robots(self) -> None:
        buf = _FrameBuffer(window_frames=10)
        buf.push(0, [_ball(100.0, 200.0), _robot("ally_01", 300.0, 400.0)])
        history = buf.possession_history(possession_distance_px=80.0)
        self.assertEqual(len(history), 0)

    def test_proximity_pairs_detects_close_robots(self) -> None:
        buf = _FrameBuffer(window_frames=10)
        buf.push(0, [
            _robot("ally_01", 100.0, 200.0),
            _robot("ally_02", 130.0, 200.0),
        ])
        pairs = buf.proximity_pairs(collision_distance_px=50.0)
        self.assertEqual(len(pairs), 1)
        _, ta, tb, dist = pairs[0]
        self.assertIn("ally_01", (ta, tb))
        self.assertIn("ally_02", (ta, tb))
        self.assertAlmostEqual(dist, 30.0, places=1)

    def test_proximity_pairs_excludes_far_robots(self) -> None:
        buf = _FrameBuffer(window_frames=10)
        buf.push(0, [
            _robot("ally_01", 100.0, 200.0),
            _robot("ally_02", 500.0, 200.0),
        ])
        pairs = buf.proximity_pairs(collision_distance_px=50.0)
        self.assertEqual(len(pairs), 0)

    def test_possession_history_accumulates_across_frames(self) -> None:
        buf = _FrameBuffer(window_frames=10)
        for f in range(5):
            buf.push(f, [_ball(100.0, 200.0), _robot("ally_01", 110.0, 200.0)])
        history = buf.possession_history(possession_distance_px=80.0)
        self.assertEqual(len(history), 5)


# ---------------------------------------------------------------------------
# Tarea 30.2 - Eventos candidatos: posesion
# ---------------------------------------------------------------------------

class TestPossessionDetection(unittest.TestCase):
    def test_single_frame_creates_candidate(self) -> None:
        det = _detector()
        det.push_frame(0, [_ball(100.0, 200.0), _robot("ally_01", 110.0, 200.0)])
        events = det.visible_events(0)
        possession = [e for e in events if e.label == "possession_candidate"]
        self.assertEqual(len(possession), 1)
        self.assertEqual(possession[0].status, STREAM_EVENT_STATUS_CANDIDATE)

    def test_sustained_possession_becomes_provisional(self) -> None:
        det = _detector(possession_min_frames=3)
        for f in range(4):
            det.push_frame(f, [_ball(100.0, 200.0), _robot("ally_01", 110.0, 200.0)])
        events = det.visible_events(3)
        possession = [e for e in events if e.label == "possession_candidate"]
        self.assertTrue(any(e.status in (STREAM_EVENT_STATUS_PROVISIONAL, STREAM_EVENT_STATUS_CONFIRMED) for e in possession))

    def test_long_possession_becomes_confirmed(self) -> None:
        det = _detector(possession_min_frames=2, possession_confirm_frames=5)
        for f in range(10):
            det.push_frame(f, [_ball(100.0, 200.0), _robot("ally_01", 110.0, 200.0)])
        events = det.visible_events(9)
        possession = [e for e in events if e.label == "possession_candidate"]
        self.assertTrue(any(e.status == STREAM_EVENT_STATUS_CONFIRMED for e in possession))

    def test_possession_assigns_correct_team(self) -> None:
        det = _detector()
        det.push_frame(0, [_ball(100.0, 200.0), _robot("ally_01", 110.0, 200.0, team="ally")])
        events = det.visible_events(0)
        possession = [e for e in events if e.label == "possession_candidate"]
        self.assertEqual(possession[0].team, "ally")

    def test_possession_assigns_correct_track_id(self) -> None:
        det = _detector()
        det.push_frame(0, [_ball(100.0, 200.0), _robot("ally_01", 110.0, 200.0)])
        events = det.visible_events(0)
        possession = [e for e in events if e.label == "possession_candidate"]
        self.assertEqual(possession[0].primary_track_id, "ally_01")

    def test_no_ball_produces_no_possession(self) -> None:
        det = _detector()
        det.push_frame(0, [_robot("ally_01", 100.0, 200.0)])
        events = [e for e in det.visible_events(0) if e.label == "possession_candidate"]
        self.assertEqual(len(events), 0)

    def test_ball_far_from_robot_produces_no_possession(self) -> None:
        det = _detector(possession_distance_px=50.0)
        det.push_frame(0, [_ball(100.0, 200.0), _robot("ally_01", 500.0, 200.0)])
        events = [e for e in det.visible_events(0) if e.label == "possession_candidate"]
        self.assertEqual(len(events), 0)

    def test_short_possession_is_discarded_on_loss(self) -> None:
        det = _detector(possession_min_frames=5)
        det.push_frame(0, [_ball(100.0, 200.0), _robot("ally_01", 110.0, 200.0)])
        det.push_frame(1, [])
        all_ev = det.all_events()
        discarded = [e for e in all_ev if e.status == STREAM_EVENT_STATUS_DISCARDED and e.label == "possession_candidate"]
        self.assertEqual(len(discarded), 1)


# ---------------------------------------------------------------------------
# Tarea 30.2 - Pass / interaccion
# ---------------------------------------------------------------------------

class TestPassDetection(unittest.TestCase):
    def _push_possession(self, det: StreamEventDetector, frames: range, robot_id: str, ball_cx: float, team: str) -> None:
        for f in frames:
            det.push_frame(f, [_ball(ball_cx, 300.0), _robot(robot_id, ball_cx + 10, 300.0, team=team)])

    def test_pass_detected_when_possession_transfers_same_team(self) -> None:
        det = _detector(possession_min_frames=2, possession_confirm_frames=10, max_pass_gap_frames=5)
        self._push_possession(det, range(0, 5), "ally_01", 200.0, "ally")
        det.push_frame(5, [_ball(300.0, 300.0), _robot("ally_02", 310.0, 300.0, team="ally")])
        all_ev = det.all_events()
        passes = [e for e in all_ev if e.label == "pass_simple"]
        self.assertGreater(len(passes), 0)

    def test_pass_not_detected_for_different_teams(self) -> None:
        det = _detector(possession_min_frames=2, possession_confirm_frames=10, max_pass_gap_frames=5)
        self._push_possession(det, range(0, 5), "ally_01", 200.0, "ally")
        det.push_frame(5, [_ball(300.0, 300.0), _row("ally_robot", 310.0, 300.0, "opp_01", "opponent")])
        all_ev = det.all_events()
        passes = [e for e in all_ev if e.label == "pass_simple"]
        self.assertEqual(len(passes), 0)

    def test_pass_not_detected_if_gap_too_large(self) -> None:
        det = _detector(possession_min_frames=2, possession_confirm_frames=10, max_pass_gap_frames=3)
        self._push_possession(det, range(0, 3), "ally_01", 200.0, "ally")
        for f in range(3, 10):
            det.push_frame(f, [])
        det.push_frame(10, [_ball(300.0, 300.0), _robot("ally_02", 310.0, 300.0, team="ally")])
        all_ev = det.all_events()
        passes = [e for e in all_ev if e.label == "pass_simple"]
        self.assertEqual(len(passes), 0)


# ---------------------------------------------------------------------------
# Tarea 30.2 - Colision / disputa
# ---------------------------------------------------------------------------

class TestCollisionDetection(unittest.TestCase):
    def _two_close_robots(self) -> list[dict]:
        return [
            _robot("ally_01", 100.0, 200.0),
            _robot("ally_02", 130.0, 200.0),
        ]

    def test_single_frame_creates_collision_candidate(self) -> None:
        det = _detector(collision_distance_px=50.0)
        det.push_frame(0, self._two_close_robots())
        events = [e for e in det.visible_events(0) if e.label == "collision_dispute"]
        self.assertGreater(len(events), 0)
        self.assertEqual(events[0].status, STREAM_EVENT_STATUS_CANDIDATE)

    def test_sustained_collision_becomes_provisional(self) -> None:
        det = _detector(collision_distance_px=50.0, collision_min_frames=3)
        for f in range(4):
            det.push_frame(f, self._two_close_robots())
        events = [e for e in det.visible_events(3) if e.label == "collision_dispute" and e.primary_track_id == "ally_01"]
        self.assertTrue(any(e.status in (STREAM_EVENT_STATUS_PROVISIONAL, STREAM_EVENT_STATUS_CONFIRMED) for e in events))

    def test_brief_collision_is_discarded(self) -> None:
        det = _detector(collision_distance_px=50.0, collision_min_frames=5)
        det.push_frame(0, self._two_close_robots())
        det.push_frame(1, [_robot("ally_01", 100.0, 200.0), _robot("ally_02", 300.0, 200.0)])
        all_ev = det.all_events()
        discarded = [e for e in all_ev if e.status == STREAM_EVENT_STATUS_DISCARDED and e.label == "collision_dispute"]
        self.assertGreater(len(discarded), 0)

    def test_collision_far_robots_not_detected(self) -> None:
        det = _detector(collision_distance_px=50.0)
        det.push_frame(0, [_robot("ally_01", 100.0, 200.0), _robot("ally_02", 500.0, 200.0)])
        events = [e for e in det.visible_events(0) if e.label == "collision_dispute"]
        self.assertEqual(len(events), 0)

    def test_collision_assigns_both_track_ids(self) -> None:
        det = _detector(collision_distance_px=50.0)
        det.push_frame(0, self._two_close_robots())
        events = [e for e in det.visible_events(0) if e.label == "collision_dispute" and e.primary_track_id == "ally_01"]
        self.assertGreater(len(events), 0)
        evt = events[0]
        self.assertIn("ally_01", evt.primary_track_id)
        self.assertIn("ally_02", evt.secondary_track_ids)


# ---------------------------------------------------------------------------
# Tarea 30.2 - Tiro aproximado + highlight
# ---------------------------------------------------------------------------

class TestShotDetection(unittest.TestCase):
    def _fast_ball_frames(self, det: StreamEventDetector, speed_px_per_sec: float, frame_gap: int = 1) -> None:
        fps = det._cfg.fps
        dist_per_frame = speed_px_per_sec / fps * frame_gap
        det.push_frame(0, [_ball(100.0, 300.0)])
        det.push_frame(frame_gap, [_ball(100.0 + dist_per_frame, 300.0)])

    def test_fast_ball_creates_shot_candidate(self) -> None:
        det = _detector(shot_min_speed_px_per_sec=300.0)
        self._fast_ball_frames(det, speed_px_per_sec=400.0)
        all_ev = det.all_events()
        shots = [e for e in all_ev if e.label == "shot_approximate"]
        self.assertGreater(len(shots), 0)

    def test_slow_ball_does_not_create_shot(self) -> None:
        det = _detector(shot_min_speed_px_per_sec=300.0)
        self._fast_ball_frames(det, speed_px_per_sec=50.0)
        all_ev = det.all_events()
        shots = [e for e in all_ev if e.label == "shot_approximate"]
        self.assertEqual(len(shots), 0)

    def test_very_fast_ball_creates_highlight(self) -> None:
        det = _detector(shot_min_speed_px_per_sec=300.0, highlight_speed_threshold_px_per_sec=400.0)
        self._fast_ball_frames(det, speed_px_per_sec=500.0)
        all_ev = det.all_events()
        highlights = [e for e in all_ev if e.label == "highlight_provisional"]
        self.assertGreater(len(highlights), 0)

    def test_shot_uses_ball_track_id(self) -> None:
        det = _detector(shot_min_speed_px_per_sec=200.0)
        self._fast_ball_frames(det, speed_px_per_sec=350.0)
        shots = [e for e in det.all_events() if e.label == "shot_approximate"]
        self.assertGreater(len(shots), 0)
        self.assertEqual(shots[0].primary_track_id, "ball_01")


# ---------------------------------------------------------------------------
# Tarea 30.3 - Ciclo de vida del evento
# ---------------------------------------------------------------------------

class TestEventLifecycle(unittest.TestCase):
    def test_candidate_starts_as_candidate(self) -> None:
        det = _detector(possession_min_frames=10)
        det.push_frame(0, [_ball(100.0, 200.0), _robot("ally_01", 110.0, 200.0)])
        events = det.visible_events(0)
        self.assertTrue(any(e.status == STREAM_EVENT_STATUS_CANDIDATE for e in events))

    def test_event_id_is_unique_per_event(self) -> None:
        det = _detector(possession_min_frames=2, collision_distance_px=50.0)
        det.push_frame(0, [_ball(100.0, 200.0), _robot("ally_01", 110.0, 200.0), _robot("ally_02", 130.0, 200.0)])
        all_ids = [e.event_id for e in det.all_events()]
        self.assertEqual(len(all_ids), len(set(all_ids)))

    def test_event_end_frame_updates_with_each_frame(self) -> None:
        det = _detector(possession_min_frames=10)
        for f in range(5):
            det.push_frame(f, [_ball(100.0, 200.0), _robot("ally_01", 110.0, 200.0)])
        events = det.visible_events(4)
        possession = [e for e in events if e.label == "possession_candidate"]
        self.assertGreater(len(possession), 0)
        self.assertEqual(possession[0].end_frame, 4)

    def test_discarded_event_not_in_visible_events(self) -> None:
        det = _detector(possession_min_frames=10)
        det.push_frame(0, [_ball(100.0, 200.0), _robot("ally_01", 110.0, 200.0)])
        det.push_frame(1, [])
        visible = det.visible_events(1)
        self.assertEqual(len([e for e in visible if e.status == STREAM_EVENT_STATUS_DISCARDED]), 0)

    def test_confirmed_event_remains_visible(self) -> None:
        det = _detector(possession_min_frames=2, possession_confirm_frames=5)
        for f in range(8):
            det.push_frame(f, [_ball(100.0, 200.0), _robot("ally_01", 110.0, 200.0)])
        det.push_frame(8, [])
        all_ev = det.all_events()
        confirmed = [e for e in all_ev if e.status == STREAM_EVENT_STATUS_CONFIRMED and e.label == "possession_candidate"]
        self.assertGreater(len(confirmed), 0)

    def test_event_candidate_promote_to_provisional(self) -> None:
        evt = StreamEventCandidate(
            event_id="test_001", label="possession_candidate", start_frame=0, end_frame=5,
            clip_id="", team="ally", primary_track_id="ally_01", secondary_track_ids=[],
            zone="middle_third", confidence=0.5, status=STREAM_EVENT_STATUS_CANDIDATE,
            reason="test", session_id="test", fps=30.0, last_updated_frame=5,
        )
        evt.promote()
        self.assertEqual(evt.status, STREAM_EVENT_STATUS_PROVISIONAL)
        evt.promote()
        self.assertEqual(evt.status, STREAM_EVENT_STATUS_CONFIRMED)

    def test_event_discard_sets_status(self) -> None:
        det = _detector(possession_min_frames=10)
        det.push_frame(0, [_ball(100.0, 200.0), _robot("ally_01", 110.0, 200.0)])
        det.push_frame(1, [])
        discarded = [e for e in det.all_events() if e.status == STREAM_EVENT_STATUS_DISCARDED]
        self.assertGreater(len(discarded), 0)

    def test_source_event_ids_linked_in_pass(self) -> None:
        det = _detector(possession_min_frames=2, possession_confirm_frames=10, max_pass_gap_frames=5)
        for f in range(4):
            det.push_frame(f, [_ball(200.0, 300.0), _robot("ally_01", 210.0, 300.0, team="ally")])
        det.push_frame(4, [_ball(300.0, 300.0), _robot("ally_02", 310.0, 300.0, team="ally")])
        all_ev = det.all_events()
        passes = [e for e in all_ev if e.label == "pass_simple"]
        if passes:
            self.assertGreater(len(passes[0].source_event_ids), 0)


# ---------------------------------------------------------------------------
# Tarea 30.3 - Salida incremental (emit_jsonl, export)
# ---------------------------------------------------------------------------

class TestStreamEventOutput(unittest.TestCase):
    def test_emit_jsonl_produces_valid_lines(self) -> None:
        det = _detector(possession_min_frames=2, possession_confirm_frames=5)
        for f in range(6):
            det.push_frame(f, [_ball(100.0, 200.0), _robot("ally_01", 110.0, 200.0)])
        jsonl = det.emit_jsonl()
        for line in jsonl.strip().splitlines():
            parsed = json.loads(line)
            self.assertIn("event_id", parsed)
            self.assertIn("status", parsed)
            self.assertIn("label", parsed)

    def test_emit_jsonl_excludes_discarded(self) -> None:
        det = _detector(possession_min_frames=5)
        det.push_frame(0, [_ball(100.0, 200.0), _robot("ally_01", 110.0, 200.0)])
        det.push_frame(1, [])
        jsonl = det.emit_jsonl()
        statuses = []
        for line in jsonl.strip().splitlines():
            if line:
                statuses.append(json.loads(line).get("status", ""))
        self.assertNotIn(STREAM_EVENT_STATUS_DISCARDED, statuses)

    def test_emit_jsonl_empty_when_no_events(self) -> None:
        det = _detector()
        self.assertEqual(det.emit_jsonl(), "")

    def test_export_events_returns_dicts(self) -> None:
        det = _detector(possession_min_frames=2, possession_confirm_frames=5)
        for f in range(6):
            det.push_frame(f, [_ball(100.0, 200.0), _robot("ally_01", 110.0, 200.0)])
        rows = det.export_events()
        self.assertIsInstance(rows, list)
        if rows:
            self.assertIsInstance(rows[0], dict)

    def test_export_csv_text_has_header(self) -> None:
        det = _detector(possession_min_frames=2, possession_confirm_frames=5)
        for f in range(6):
            det.push_frame(f, [_ball(100.0, 200.0), _robot("ally_01", 110.0, 200.0)])
        csv_text = det.export_csv_text()
        first_line = csv_text.splitlines()[0] if csv_text else ""
        for field in STREAM_EVENT_JSONL_FIELDS:
            self.assertIn(field, first_line)

    def test_export_csv_text_empty_when_no_events(self) -> None:
        det = _detector()
        self.assertEqual(det.export_csv_text(), "")

    def test_as_dict_has_required_fields(self) -> None:
        det = _detector(possession_min_frames=2, possession_confirm_frames=5)
        for f in range(6):
            det.push_frame(f, [_ball(100.0, 200.0), _robot("ally_01", 110.0, 200.0)])
        evts = det.all_events()
        for evt in evts:
            d = evt.as_dict()
            required = {"event_id", "label", "start_frame", "end_frame", "start_time_sec", "end_time_sec", "confidence", "status", "clip_id", "track_ids", "team", "zone", "reason"}
            self.assertTrue(required.issubset(d.keys()), msg=f"Missing keys in {d.keys()}")

    def test_track_ids_is_list(self) -> None:
        det = _detector(possession_min_frames=2)
        det.push_frame(0, [_ball(100.0, 200.0), _robot("ally_01", 110.0, 200.0)])
        evts = [e for e in det.all_events() if e.label == "possession_candidate"]
        if evts:
            self.assertIsInstance(evts[0].as_dict()["track_ids"], list)


# ---------------------------------------------------------------------------
# Snapshot y configuracion
# ---------------------------------------------------------------------------

class TestSnapshotAndConfig(unittest.TestCase):
    def test_snapshot_has_required_keys(self) -> None:
        det = _detector()
        snap = det.snapshot()
        self.assertIn("session_id", snap)
        self.assertIn("open_event_count", snap)
        self.assertIn("closed_event_count", snap)
        self.assertIn("total_events", snap)
        self.assertIn("by_status", snap)

    def test_snapshot_counts_match_events(self) -> None:
        det = _detector(possession_min_frames=10)
        det.push_frame(0, [_ball(100.0, 200.0), _robot("ally_01", 110.0, 200.0)])
        snap = det.snapshot()
        self.assertEqual(snap["open_event_count"], len(det._open))

    def test_detector_config_defaults(self) -> None:
        cfg = StreamDetectorConfig()
        self.assertEqual(cfg.fps, 30.0)
        self.assertGreater(cfg.possession_distance_px, 0)
        self.assertGreater(cfg.window_frames, 0)

    def test_stream_event_labels_constant_defined(self) -> None:
        for label in STREAM_EVENT_LABELS:
            self.assertIsInstance(label, str)

    def test_duration_frames_property(self) -> None:
        evt = StreamEventCandidate(
            event_id="t", label="possession_candidate", start_frame=10, end_frame=25,
            clip_id="", team="ally", primary_track_id="r1", secondary_track_ids=[],
            zone="middle_third", confidence=0.5, status=STREAM_EVENT_STATUS_CANDIDATE,
            reason="test", session_id="s", fps=30.0, last_updated_frame=25,
        )
        self.assertEqual(evt.duration_frames, 16)

    def test_time_properties_use_fps(self) -> None:
        evt = StreamEventCandidate(
            event_id="t", label="possession_candidate", start_frame=30, end_frame=60,
            clip_id="", team="ally", primary_track_id="r1", secondary_track_ids=[],
            zone="middle_third", confidence=0.5, status=STREAM_EVENT_STATUS_CANDIDATE,
            reason="test", session_id="s", fps=30.0, last_updated_frame=60,
        )
        self.assertAlmostEqual(evt.start_time_sec, 1.0, places=4)
        self.assertAlmostEqual(evt.end_time_sec, 2.0, places=4)


if __name__ == "__main__":
    unittest.main()
