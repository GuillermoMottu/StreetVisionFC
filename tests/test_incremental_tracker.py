from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import unittest

from futbotmx.io.detections import Detection
from futbotmx.tracking.incremental_tracker import (
    INCREMENTAL_JSONL_FIELDS,
    LIVE_TRACK_STATE_ACTIVE,
    LIVE_TRACK_STATE_LOST,
    IncrementalTrackerSession,
    LiveTrackRow,
    detections_from_precomputed_rows,
)


def _det(class_name: str, cx: float, cy: float, confidence: float = 0.9) -> Detection:
    return Detection(
        class_name=class_name,
        bbox=(cx - 20, cy - 30, cx + 20, cy + 30),
        centroid=(cx, cy),
        confidence=confidence,
    )


def _session(session_id: str = "test_session", **kwargs: object) -> IncrementalTrackerSession:
    return IncrementalTrackerSession(session_id=session_id, fps=30.0, **kwargs)


class TestIncrementalTrackerInit(unittest.TestCase):
    def test_session_starts_empty(self) -> None:
        tracker = _session()
        snap = tracker.snapshot()
        self.assertEqual(snap["active_count"], 0)
        self.assertEqual(snap["lost_count"], 0)
        self.assertIsNone(snap["current_frame"])
        self.assertEqual(snap["total_emitted_rows"], 0)

    def test_session_id_stored(self) -> None:
        tracker = _session("my_session")
        self.assertEqual(tracker.session_id, "my_session")
        self.assertEqual(tracker.snapshot()["session_id"], "my_session")


class TestIncrementalTrackerUpdate(unittest.TestCase):
    def test_update_empty_detections_returns_no_rows(self) -> None:
        tracker = _session()
        rows = tracker.update(0, [])
        self.assertEqual(rows, [])

    def test_update_single_detection_creates_track(self) -> None:
        tracker = _session()
        rows = tracker.update(10, [_det("ally", 100, 200)])
        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertEqual(row.class_name, "ally")
        self.assertEqual(row.state, LIVE_TRACK_STATE_ACTIVE)
        self.assertEqual(row.frame, 10)
        self.assertAlmostEqual(row.timestamp_sec, 10 / 30.0, places=5)

    def test_update_sets_bbox_dimensions(self) -> None:
        tracker = _session()
        rows = tracker.update(0, [_det("ally", 100, 200)])
        row = rows[0]
        self.assertAlmostEqual(row.x, 80.0)
        self.assertAlmostEqual(row.y, 170.0)
        self.assertAlmostEqual(row.w, 40.0)
        self.assertAlmostEqual(row.h, 60.0)
        self.assertAlmostEqual(row.center_x, 100.0)
        self.assertAlmostEqual(row.center_y, 200.0)

    def test_update_track_id_assigned_per_class(self) -> None:
        tracker = _session()
        rows = tracker.update(0, [_det("ally", 100, 200), _det("ally", 400, 200)])
        ids = {row.track_id for row in rows}
        self.assertEqual(len(ids), 2)
        for track_id in ids:
            self.assertTrue(track_id.startswith("ally_"))

    def test_update_track_id_stable_across_frames(self) -> None:
        tracker = _session()
        rows0 = tracker.update(0, [_det("ally", 100, 200)])
        first_id = rows0[0].track_id
        rows1 = tracker.update(1, [_det("ally", 102, 201)])
        self.assertEqual(rows1[0].track_id, first_id)

    def test_update_team_assigned_from_class(self) -> None:
        tracker = _session()
        rows = tracker.update(0, [_det("ally_robot", 100, 200), _det("opponent_robot", 300, 200)])
        teams = {row.class_name: row.team for row in rows}
        self.assertEqual(teams["ally_robot"], "ally")
        self.assertEqual(teams["opponent_robot"], "opponent")

    def test_update_current_frame_advances(self) -> None:
        tracker = _session()
        tracker.update(5, [_det("ally", 100, 200)])
        self.assertEqual(tracker.current_frame, 5)
        tracker.update(10, [_det("ally", 102, 200)])
        self.assertEqual(tracker.current_frame, 10)

    def test_update_accumulates_emitted_rows(self) -> None:
        tracker = _session()
        tracker.update(0, [_det("ally", 100, 200)])
        tracker.update(1, [_det("ally", 102, 200)])
        self.assertEqual(tracker.snapshot()["total_emitted_rows"], 2)

    def test_update_multiple_classes_independent_counters(self) -> None:
        tracker = _session()
        rows = tracker.update(0, [_det("ally", 100, 200), _det("ball", 200, 200)])
        ids = {row.track_id for row in rows}
        self.assertIn("ally_01", ids)
        self.assertIn("ball_01", ids)


class TestIncrementalTrackerLostTracks(unittest.TestCase):
    def test_missing_detection_marks_track_lost(self) -> None:
        tracker = _session(max_lost_frames=5)
        tracker.update(0, [_det("ally", 100, 200)])
        rows = tracker.update(1, [])
        lost = [r for r in rows if r.state == LIVE_TRACK_STATE_LOST]
        self.assertEqual(len(lost), 1)
        self.assertEqual(lost[0].lost_count, 1)

    def test_lost_track_removed_after_window(self) -> None:
        tracker = _session(max_lost_frames=2)
        tracker.update(0, [_det("ally", 100, 200)])
        tracker.update(1, [])
        tracker.update(2, [])
        rows = tracker.update(3, [])
        lost = [r for r in rows if r.state == LIVE_TRACK_STATE_LOST]
        self.assertEqual(len(lost), 0)

    def test_lost_track_recovers_when_redetected(self) -> None:
        tracker = _session(max_lost_frames=5)
        rows0 = tracker.update(0, [_det("ally", 100, 200)])
        original_id = rows0[0].track_id
        tracker.update(1, [])
        rows2 = tracker.update(2, [_det("ally", 103, 201)])
        active = [r for r in rows2 if r.state == LIVE_TRACK_STATE_ACTIVE]
        self.assertEqual(len(active), 1)
        self.assertEqual(active[0].track_id, original_id)
        self.assertEqual(active[0].lost_count, 0)

    def test_snapshot_counts_lost_separately(self) -> None:
        tracker = _session(max_lost_frames=5)
        tracker.update(0, [_det("ally", 100, 200)])
        tracker.update(1, [_det("ball", 300, 300)])
        snap = tracker.snapshot()
        self.assertEqual(snap["active_count"], 1)
        self.assertEqual(snap["lost_count"], 1)


class TestIncrementalTrackerSeek(unittest.TestCase):
    def test_seek_forward_does_not_reset(self) -> None:
        tracker = _session()
        tracker.update(0, [_det("ally", 100, 200)])
        reset = tracker.seek(10)
        self.assertFalse(reset)
        self.assertEqual(tracker.reset_count, 0)
        self.assertEqual(tracker.snapshot()["active_count"], 1)

    def test_seek_backward_resets_state(self) -> None:
        tracker = _session()
        tracker.update(10, [_det("ally", 100, 200)])
        reset = tracker.seek(5)
        self.assertTrue(reset)
        self.assertEqual(tracker.reset_count, 1)
        snap = tracker.snapshot()
        self.assertEqual(snap["active_count"], 0)
        self.assertIsNone(snap["current_frame"])
        self.assertEqual(snap["total_emitted_rows"], 0)

    def test_seek_same_frame_does_not_reset(self) -> None:
        tracker = _session()
        tracker.update(10, [_det("ally", 100, 200)])
        reset = tracker.seek(10)
        self.assertFalse(reset)
        self.assertEqual(tracker.reset_count, 0)

    def test_multiple_seeks_accumulate_reset_count(self) -> None:
        tracker = _session()
        tracker.update(10, [_det("ally", 100, 200)])
        tracker.seek(0)
        tracker.update(10, [_det("ally", 100, 200)])
        tracker.seek(0)
        self.assertEqual(tracker.reset_count, 2)

    def test_seek_resets_track_id_counters(self) -> None:
        tracker = _session()
        rows0 = tracker.update(0, [_det("ally", 100, 200)])
        id_before = rows0[0].track_id
        tracker.seek(0)
        rows1 = tracker.update(0, [_det("ally", 100, 200)])
        id_after = rows1[0].track_id
        self.assertEqual(id_before, id_after)


class TestRebuildFromPrecomputed(unittest.TestCase):
    def _tracks_by_frame(self) -> dict[int, list[dict]]:
        return {
            0: [{"class": "ally", "x": 80.0, "y": 170.0, "w": 40.0, "h": 60.0, "center_x": 100.0, "center_y": 200.0, "confidence": "0.9"}],
            1: [{"class": "ally", "x": 82.0, "y": 171.0, "w": 40.0, "h": 60.0, "center_x": 102.0, "center_y": 201.0, "confidence": "0.9"}],
            2: [{"class": "ally", "x": 84.0, "y": 172.0, "w": 40.0, "h": 60.0, "center_x": 104.0, "center_y": 202.0, "confidence": "0.9"}],
        }

    def test_rebuild_processes_frames_in_order(self) -> None:
        tracker = _session()
        rows = tracker.rebuild_from_precomputed(self._tracks_by_frame(), up_to_frame=2)
        frames = [r.frame for r in rows if r.state == LIVE_TRACK_STATE_ACTIVE]
        self.assertEqual(frames, [0, 1, 2])

    def test_rebuild_assigns_stable_ids(self) -> None:
        tracker = _session()
        rows = tracker.rebuild_from_precomputed(self._tracks_by_frame(), up_to_frame=2)
        active = [r for r in rows if r.state == LIVE_TRACK_STATE_ACTIVE]
        ids = {r.track_id for r in active}
        self.assertEqual(len(ids), 1)

    def test_rebuild_stops_at_up_to_frame(self) -> None:
        tracker = _session()
        rows = tracker.rebuild_from_precomputed(self._tracks_by_frame(), up_to_frame=1)
        frames = {r.frame for r in rows}
        self.assertNotIn(2, frames)
        self.assertIn(0, frames)
        self.assertIn(1, frames)

    def test_rebuild_resets_existing_state_first(self) -> None:
        tracker = _session()
        tracker.update(100, [_det("ally", 500, 500)])
        tracker.rebuild_from_precomputed(self._tracks_by_frame(), up_to_frame=2)
        snap = tracker.snapshot()
        self.assertEqual(snap["current_frame"], 2)

    def test_rebuild_from_bbox_format(self) -> None:
        tracks_by_frame = {
            0: [{"class_name": "ally", "bbox_x1": 80.0, "bbox_y1": 170.0, "bbox_x2": 120.0, "bbox_y2": 230.0, "x": 100.0, "y": 200.0, "confidence": "0.85"}],
        }
        tracker = _session()
        rows = tracker.rebuild_from_precomputed(tracks_by_frame, up_to_frame=0)
        active = [r for r in rows if r.state == LIVE_TRACK_STATE_ACTIVE]
        self.assertEqual(len(active), 1)
        self.assertEqual(active[0].class_name, "ally")


class TestIncrementalTrackerSnapshot(unittest.TestCase):
    def test_snapshot_contains_required_keys(self) -> None:
        tracker = _session()
        snap = tracker.snapshot()
        required = {"session_id", "current_frame", "reset_count", "active_count", "lost_count", "total_emitted_rows", "tracks"}
        self.assertTrue(required.issubset(snap.keys()))

    def test_snapshot_tracks_list_has_required_fields(self) -> None:
        tracker = _session()
        tracker.update(0, [_det("ally", 100, 200)])
        snap = tracker.snapshot()
        track = snap["tracks"][0]
        required = {"track_id", "class_name", "team", "state", "lost_count", "first_frame", "last_frame", "centroid", "confidence"}
        self.assertTrue(required.issubset(track.keys()))

    def test_snapshot_centroid_is_list(self) -> None:
        tracker = _session()
        tracker.update(0, [_det("ally", 100, 200)])
        snap = tracker.snapshot()
        self.assertIsInstance(snap["tracks"][0]["centroid"], list)


class TestIncrementalTrackerOutput(unittest.TestCase):
    def test_emit_jsonl_produces_valid_json_lines(self) -> None:
        tracker = _session()
        tracker.update(0, [_det("ally", 100, 200)])
        tracker.update(1, [_det("ally", 102, 201)])
        jsonl = tracker.emit_jsonl()
        lines = [line for line in jsonl.strip().splitlines() if line]
        self.assertEqual(len(lines), 2)
        for line in lines:
            parsed = json.loads(line)
            self.assertIn("track_id", parsed)
            self.assertIn("frame", parsed)
            self.assertIn("state", parsed)

    def test_emit_jsonl_uses_class_key_not_class_name(self) -> None:
        tracker = _session()
        tracker.update(0, [_det("ally", 100, 200)])
        jsonl = tracker.emit_jsonl()
        parsed = json.loads(jsonl.strip().splitlines()[0])
        self.assertIn("class", parsed)
        self.assertNotIn("class_name", parsed)

    def test_emit_jsonl_empty_session_returns_empty(self) -> None:
        tracker = _session()
        self.assertEqual(tracker.emit_jsonl(), "")

    def test_export_csv_rows_returns_dicts(self) -> None:
        tracker = _session()
        tracker.update(0, [_det("ally", 100, 200)])
        rows = tracker.export_csv_rows()
        self.assertEqual(len(rows), 1)
        self.assertIsInstance(rows[0], dict)

    def test_export_csv_text_has_header(self) -> None:
        tracker = _session()
        tracker.update(0, [_det("ally", 100, 200)])
        csv_text = tracker.export_csv_text()
        first_line = csv_text.splitlines()[0]
        for field in INCREMENTAL_JSONL_FIELDS:
            self.assertIn(field, first_line)

    def test_export_csv_text_empty_session_returns_empty(self) -> None:
        tracker = _session()
        self.assertEqual(tracker.export_csv_text(), "")

    def test_live_track_row_as_dict_fields(self) -> None:
        tracker = _session()
        rows = tracker.update(0, [_det("ally", 100, 200, confidence=0.85)])
        d = rows[0].as_dict()
        self.assertEqual(d["session_id"], "test_session")
        self.assertEqual(d["frame"], 0)
        self.assertEqual(d["class"], "ally")
        self.assertAlmostEqual(d["confidence"], 0.85, places=5)
        self.assertIn("state", d)
        self.assertIn("lost_count", d)


class TestIncrementalTrackerCompareWithBatch(unittest.TestCase):
    def _batch_tracks(self, frame: int, cx: float, cy: float) -> list[dict]:
        return [{"frame": frame, "class": "ally", "center_x": cx, "center_y": cy}]

    def test_compare_with_empty_batch(self) -> None:
        tracker = _session()
        tracker.update(0, [_det("ally", 100, 200)])
        result = tracker.compare_with_batch([])
        self.assertEqual(result["total_batch_rows"], 0)
        self.assertEqual(result["matched_detections"], 0)

    def test_compare_finds_close_match(self) -> None:
        tracker = _session()
        tracker.update(0, [_det("ally", 100, 200)])
        result = tracker.compare_with_batch(self._batch_tracks(0, 102.0, 200.0))
        self.assertEqual(result["matched_detections"], 1)
        self.assertEqual(result["match_rate"], 1.0)

    def test_compare_rejects_far_detections(self) -> None:
        tracker = _session()
        tracker.update(0, [_det("ally", 100, 200)])
        result = tracker.compare_with_batch(self._batch_tracks(0, 500.0, 500.0))
        self.assertEqual(result["matched_detections"], 0)

    def test_compare_class_mismatch_not_matched(self) -> None:
        tracker = _session()
        tracker.update(0, [_det("ally", 100, 200)])
        batch = [{"frame": 0, "class": "ball", "center_x": 100.0, "center_y": 200.0}]
        result = tracker.compare_with_batch(batch)
        self.assertEqual(result["matched_detections"], 0)

    def test_compare_result_has_required_keys(self) -> None:
        tracker = _session()
        result = tracker.compare_with_batch([])
        required = {
            "session_id", "emitted_frames", "batch_frames", "common_frames",
            "total_emitted_active_rows", "total_batch_rows", "matched_detections",
            "match_rate", "batch_coverage", "notes",
        }
        self.assertTrue(required.issubset(result.keys()))

    def test_compare_excludes_lost_rows_from_match(self) -> None:
        tracker = _session(max_lost_frames=5)
        tracker.update(0, [_det("ally", 100, 200)])
        tracker.update(1, [])
        result = tracker.compare_with_batch([{"frame": 1, "class": "ally", "center_x": 100.0, "center_y": 200.0}])
        self.assertEqual(result["matched_detections"], 0)


class TestDetectionsFromPrecomputedRows(unittest.TestCase):
    def test_converts_live_tracks_format(self) -> None:
        rows = [{"class": "ally", "x": "80", "y": "170", "w": "40", "h": "60", "center_x": "100", "center_y": "200", "confidence": "0.9"}]
        detections = detections_from_precomputed_rows(rows)
        self.assertEqual(len(detections), 1)
        self.assertEqual(detections[0].class_name, "ally")
        self.assertAlmostEqual(detections[0].centroid[0], 100.0)
        self.assertAlmostEqual(detections[0].centroid[1], 200.0)

    def test_converts_bbox_format(self) -> None:
        rows = [{"class_name": "ball", "bbox_x1": "80", "bbox_y1": "170", "bbox_x2": "120", "bbox_y2": "230", "confidence": "0.7"}]
        detections = detections_from_precomputed_rows(rows)
        self.assertEqual(len(detections), 1)
        self.assertEqual(detections[0].class_name, "ball")
        self.assertAlmostEqual(detections[0].centroid[0], 100.0)
        self.assertAlmostEqual(detections[0].centroid[1], 200.0)

    def test_skips_rows_without_class(self) -> None:
        rows = [{"x": "80", "y": "170", "w": "40", "h": "60"}]
        detections = detections_from_precomputed_rows(rows)
        self.assertEqual(len(detections), 0)

    def test_skips_rows_without_known_format(self) -> None:
        rows = [{"class": "ally", "some_other_key": "value"}]
        detections = detections_from_precomputed_rows(rows)
        self.assertEqual(len(detections), 0)

    def test_confidence_defaults_to_one(self) -> None:
        rows = [{"class": "ally", "x": "80", "y": "170", "w": "40", "h": "60"}]
        detections = detections_from_precomputed_rows(rows)
        self.assertAlmostEqual(detections[0].confidence, 1.0)


if __name__ == "__main__":
    unittest.main()
