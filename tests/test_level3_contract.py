from __future__ import annotations

import csv
import tempfile
import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from futbotmx.artifact_names import HIGHLIGHTS_CSV, SPATIAL_TRACKS_CSV
from futbotmx.level3 import (
    LEVEL3_HIGHLIGHTS_FIELDS,
    LEVEL3_TRACKS_FIELDS,
    read_csv_artifact,
    validate_required_fields,
    write_csv_artifact,
    write_schema_json,
    write_schema_manifest,
)


class Level3ContractTests(unittest.TestCase):
    def test_validate_required_fields_reports_missing_fields(self) -> None:
        row = {"clip_id": "video_595", "frame": 120}

        missing = validate_required_fields(row, LEVEL3_TRACKS_FIELDS)

        self.assertNotIn("clip_id", missing)
        self.assertNotIn("frame", missing)
        self.assertIn("x_norm", missing)
        self.assertIn("calibration_status", missing)

    def test_schema_writers_are_roundtrippable(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp)
            manifest_path = output_dir / "tactical_schema_manifest.csv"
            json_path = output_dir / "tactical_schema.json"

            write_schema_manifest(manifest_path)
            write_schema_json(json_path)

            with manifest_path.open("r", newline="", encoding="utf-8") as handle:
                rows = list(csv.DictReader(handle))
            payload = json_path.read_text(encoding="utf-8")

            self.assertGreaterEqual(len(rows), 7)
            self.assertIn(SPATIAL_TRACKS_CSV, {row["artifact_name"] for row in rows})
            self.assertIn("tactical_data_contract_v0.2", payload)

    def test_csv_artifact_writer_validates_and_roundtrips_level3_tracks(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / SPATIAL_TRACKS_CSV
            row = {
                field: ""
                for field in LEVEL3_TRACKS_FIELDS
            }
            row.update(
                {
                    "clip_id": "video_595",
                    "frame": 120,
                    "time_sec": 2.01,
                    "track_id": "ball_bt_01",
                    "source_track_id": "ball_bt_01",
                    "class_name": "ball",
                    "team": "neutral",
                    "x": 1003.4,
                    "y": 735.3,
                    "confidence": 0.81,
                    "calibration_status": "pending",
                    "track_quality": "provisional",
                }
            )

            write_csv_artifact(path, SPATIAL_TRACKS_CSV, [row])
            loaded = read_csv_artifact(path)

            self.assertEqual(loaded[0]["clip_id"], "video_595")
            self.assertEqual(loaded[0]["track_id"], "ball_bt_01")
            self.assertEqual(loaded[0]["calibration_status"], "pending")

    def test_csv_artifact_writer_roundtrips_level3_highlights(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / HIGHLIGHTS_CSV
            row = {field: "" for field in LEVEL3_HIGHLIGHTS_FIELDS}
            row.update(
                {
                    "clip_id": "video_595",
                    "highlight_id": "lvl3_evt_000001",
                    "rank": 1,
                    "score": 82.5,
                    "event_type": "advanced_highlight",
                    "frame_start": 122,
                    "frame_end": 123,
                    "time_start_sec": 2.043,
                    "time_end_sec": 2.06,
                    "primary_track_id": "small_robot_bt_01",
                    "secondary_track_ids": "ball_bt_01",
                    "zone": "defensive_third",
                    "confidence": 0.89,
                    "reliability": "provisional",
                    "reason": "velocidad_norm=0.272; respaldo_level2",
                }
            )

            write_csv_artifact(path, HIGHLIGHTS_CSV, [row])
            loaded = read_csv_artifact(path)

            self.assertEqual(loaded[0]["highlight_id"], "lvl3_evt_000001")
            self.assertEqual(loaded[0]["event_type"], "advanced_highlight")
            self.assertEqual(loaded[0]["reliability"], "provisional")


if __name__ == "__main__":
    unittest.main()
