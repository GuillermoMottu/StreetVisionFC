from __future__ import annotations

import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from futbotmx.live_playback_contract import (
    LIVE_HIGHLIGHT_FIELDS,
    LIVE_TRACK_FIELDS,
    build_minimap_payload,
    normalize_event,
    normalize_highlight_row,
    normalize_track_row,
    read_csv_rows,
    read_json_events,
    validate_live_event,
    validate_live_highlight_row,
    validate_live_track_row,
    validate_minimap_payload,
    write_live_events_json,
    write_live_highlights_csv,
    write_live_tracks_csv,
)


FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures" / "live_playback"


class LivePlaybackContractTests(unittest.TestCase):
    def test_fixture_tracks_events_highlights_and_minimap_are_valid(self) -> None:
        tracks = read_csv_rows(FIXTURE_DIR / "live_tracks.csv")
        events = read_json_events(FIXTURE_DIR / "live_events.json")
        highlights = read_csv_rows(FIXTURE_DIR / "live_highlights.csv")
        minimap = json.loads((FIXTURE_DIR / "minimap_frame_120.json").read_text(encoding="utf-8"))

        self.assertEqual([validate_live_track_row(row) for row in tracks], [[], [], []])
        self.assertEqual([validate_live_event(event) for event in events], [[]])
        self.assertEqual([validate_live_highlight_row(row) for row in highlights], [[]])
        self.assertEqual(validate_minimap_payload(minimap), [])

    def test_normalize_level3_track_row_maps_bbox_center_time_and_optional_fields(self) -> None:
        row = {
            "clip_id": "video_595",
            "frame": "120",
            "time_sec": "2.01",
            "track_id": "ball_bt_01",
            "class_name": "ball",
            "team": "neutral",
            "x": "1003.403717",
            "y": "735.351624",
            "bbox_x1": "981.469299",
            "bbox_y1": "714.308105",
            "bbox_x2": "1025.338135",
            "bbox_y2": "756.395142",
            "confidence": "0.8125",
            "x_norm": "0.74694",
            "y_norm": "0.191105",
            "zone": "defensive_third",
            "calibration_confidence": "0.824417",
        }

        normalized = normalize_track_row(row)

        self.assertEqual(normalized["timestamp_sec"], "2.01")
        self.assertEqual(normalized["class"], "ball")
        self.assertEqual(normalized["x"], "981.469299")
        self.assertEqual(normalized["y"], "714.308105")
        self.assertEqual(normalized["w"], "43.868836")
        self.assertEqual(normalized["h"], "42.087037")
        self.assertEqual(normalized["center_x"], "1003.403717")
        self.assertEqual(normalized["x_norm"], "0.74694")
        self.assertEqual(validate_live_track_row(normalized), [])

    def test_normalize_level2_track_row_can_derive_timestamp_from_fps(self) -> None:
        row = {
            "frame": "120",
            "track_id": "small_robot_bt_01",
            "class_name": "small_robot",
            "x": "682.882355",
            "y": "670.008118",
            "bbox_x1": "605.612427",
            "bbox_y1": "544.356445",
            "bbox_x2": "760.152283",
            "bbox_y2": "795.65979",
            "confidence": "0.882812",
            "team": "neutral",
        }

        normalized = normalize_track_row(row, clip_id="video_595", fps=60.0)

        self.assertEqual(normalized["clip_id"], "video_595")
        self.assertEqual(normalized["timestamp_sec"], "2")
        self.assertEqual(normalized["center_y"], "670.008118")
        self.assertEqual(validate_live_track_row(normalized), [])

    def test_normalize_level3_event_keeps_track_references_and_conservative_status(self) -> None:
        event = {
            "event_id": "lvl3_evt_000005",
            "event_type": "advanced_highlight",
            "clip_id": "video_595",
            "frame_start": 122,
            "frame_end": 123,
            "time_start_sec": 2.043,
            "time_end_sec": 2.06,
            "team": "unknown",
            "primary_object_id": "small_robot_bt_01",
            "secondary_object_ids": ["ball_bt_01"],
            "ball_id": "ball_bt_01",
            "zone": "defensive_third",
            "confidence": 0.893107,
            "reliability": "provisional",
            "source_event_ids": ["lvl2_evt_000001"],
            "spatial_context": {"reason": ["velocidad_norm=0.272", "posesion_candidata"]},
        }

        normalized = normalize_event(event)

        self.assertEqual(normalized["label"], "advanced_highlight")
        self.assertEqual(normalized["start_frame"], 122)
        self.assertEqual(normalized["status"], "provisional")
        self.assertEqual(normalized["track_ids"], ["small_robot_bt_01", "ball_bt_01"])
        self.assertIn("velocidad_norm", normalized["reason"])
        self.assertEqual(validate_live_event(normalized), [])

    def test_normalize_level3_highlight_row_maps_reliability_to_status(self) -> None:
        row = {
            "clip_id": "video_595",
            "highlight_id": "lvl3_evt_000005",
            "rank": "1",
            "score": "82.868076",
            "event_type": "advanced_highlight",
            "frame_start": "122",
            "frame_end": "123",
            "time_start_sec": "2.043",
            "time_end_sec": "2.06",
            "primary_track_id": "small_robot_bt_01",
            "secondary_track_ids": "ball_bt_01",
            "zone": "defensive_third",
            "confidence": "0.893107",
            "reliability": "provisional",
            "reason": "velocidad_norm=0.272; posesion_candidata",
            "source_event_ids": "lvl2_evt_000001|lvl2_evt_000002",
        }

        normalized = normalize_highlight_row(row)

        self.assertEqual(normalized["label"], "advanced_highlight")
        self.assertEqual(normalized["start_frame"], "122")
        self.assertEqual(normalized["status"], "provisional")
        self.assertEqual(normalized["secondary_track_ids"], "ball_bt_01")
        self.assertEqual(validate_live_highlight_row(normalized), [])

    def test_build_minimap_payload_filters_to_rectified_points_for_frame(self) -> None:
        rows = read_csv_rows(FIXTURE_DIR / "live_tracks.csv")

        payload = build_minimap_payload(rows, "video_fixture", 120, 2.0, calibration_status="rectified")

        self.assertEqual(payload["calibration_confidence"], "0.81")
        self.assertEqual([point["track_id"] for point in payload["points"]], ["ball_bt_01", "small_robot_bt_01"])
        self.assertEqual(validate_minimap_payload(payload), [])

    def test_writers_validate_before_serializing(self) -> None:
        tracks = read_csv_rows(FIXTURE_DIR / "live_tracks.csv")
        events = read_json_events(FIXTURE_DIR / "live_events.json")
        highlights = read_csv_rows(FIXTURE_DIR / "live_highlights.csv")

        with TemporaryDirectory() as tmp:
            output_dir = Path(tmp)
            write_live_tracks_csv(output_dir / "live_tracks.csv", tracks)
            write_live_events_json(output_dir / "live_events.json", events)
            write_live_highlights_csv(output_dir / "live_highlights.csv", highlights)

            self.assertEqual(read_csv_rows(output_dir / "live_tracks.csv")[0]["track_id"], "ball_bt_01")
            self.assertEqual(read_json_events(output_dir / "live_events.json")[0]["event_id"], "live_evt_0001")
            self.assertEqual(read_csv_rows(output_dir / "live_highlights.csv")[0]["highlight_id"], "live_hl_0001")

    def test_invalid_rows_report_missing_and_range_errors(self) -> None:
        row = {field: "" for field in LIVE_TRACK_FIELDS}
        row["confidence"] = "1.5"

        errors = validate_live_track_row(row)

        self.assertIn("missing:clip_id", errors)
        self.assertIn("missing:track_id", errors)
        self.assertIn("above_max:confidence", errors)

    def test_contract_field_lists_stay_stable_for_frontend(self) -> None:
        self.assertEqual(LIVE_TRACK_FIELDS[:5], ("clip_id", "frame", "timestamp_sec", "track_id", "class"))
        self.assertEqual(LIVE_HIGHLIGHT_FIELDS[:5], ("clip_id", "highlight_id", "rank", "score", "label"))


if __name__ == "__main__":
    unittest.main()
