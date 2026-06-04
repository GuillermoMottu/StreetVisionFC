from __future__ import annotations

import csv
import tempfile
import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from futbotmx.level3 import (
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
            manifest_path = output_dir / "level3_schema_manifest.csv"
            json_path = output_dir / "level3_schema.json"

            write_schema_manifest(manifest_path)
            write_schema_json(json_path)

            with manifest_path.open("r", newline="", encoding="utf-8") as handle:
                rows = list(csv.DictReader(handle))
            payload = json_path.read_text(encoding="utf-8")

            self.assertGreaterEqual(len(rows), 7)
            self.assertIn("level3_tracks.csv", {row["artifact_name"] for row in rows})
            self.assertIn("level3_data_contract_v0.1", payload)

    def test_csv_artifact_writer_validates_and_roundtrips_level3_tracks(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "level3_tracks.csv"
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

            write_csv_artifact(path, "level3_tracks.csv", [row])
            loaded = read_csv_artifact(path)

            self.assertEqual(loaded[0]["clip_id"], "video_595")
            self.assertEqual(loaded[0]["track_id"], "ball_bt_01")
            self.assertEqual(loaded[0]["calibration_status"], "pending")


if __name__ == "__main__":
    unittest.main()
