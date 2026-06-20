from __future__ import annotations

import csv
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from futbotmx.level3 import HighlightReviewConfig, build_highlight_review_package, render_review_panel_html


def write_csv(path: Path, rows: list[dict[str, object]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


class HighlightReviewTests(unittest.TestCase):
    def test_review_package_writes_editable_csv_panel_and_validation(self) -> None:
        with TemporaryDirectory() as tmpdir:
            config = create_fixture(Path(tmpdir))

            context = build_highlight_review_package(config)

            output = Path(config.output_dir)
            review_rows = read_csv(output / "human_review.csv")
            validation_rows = read_csv(output / "human_review_validation.csv")
            html = (output / "human_review_panel.html").read_text(encoding="utf-8")

            self.assertIn('data-ui-shell="futbotmx-ui-v1"', html)
            self.assertIn('data-product-flow="review"', html)
            self.assertEqual(len(review_rows), 2)
            self.assertEqual(review_rows[0]["review_status"], "confiable")
            self.assertEqual(review_rows[1]["review_status"], "provisional")
            self.assertTrue(all(row["status"] == "pass" for row in validation_rows))
            self.assertIn("overlay_01.png", html)
            self.assertIn("minimap_01.png", html)
            self.assertIn("descartado", html)
            self.assertEqual(context["status_counts"]["confiable"], 1)

    def test_review_panel_contains_export_control(self) -> None:
        with TemporaryDirectory() as tmpdir:
            config = create_fixture(Path(tmpdir))
            context = build_highlight_review_package(config)

            html = render_review_panel_html(context)

            self.assertIn("Exportar CSV", html)
            self.assertIn("human_review.csv", html)


def create_fixture(root: Path) -> HighlightReviewConfig:
    events_dir = root / "events"
    visuals_dir = root / "visuals"
    output_dir = root / "review"
    highlights_csv = events_dir / "level3_highlights.csv"
    events_json = events_dir / "level3_events.json"
    overlay_csv = events_dir / "overlay_validation.csv"
    visualization_manifest = visuals_dir / "visualization_manifest.csv"
    storyboard_manifest = visuals_dir / "highlight_storyboard_manifest.csv"
    fields = [
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
    ]
    write_csv(highlights_csv, [highlight_row(1, "lvl3_evt_001", 0.9), highlight_row(2, "lvl3_evt_002", 0.75)], fields)
    events_json.write_text(
        json.dumps(
            [
                {"event_id": "lvl3_evt_001", "narrative": "Highlight sintetico uno."},
                {"event_id": "lvl3_evt_002", "narrative": "Highlight sintetico dos."},
            ],
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    write_csv(
        overlay_csv,
        [
            {"clip_id": "video_test", "highlight_id": "lvl3_evt_001", "rank": 1, "frame_start": 10, "frame_end": 11, "asset_path": "overlay_01.png", "confidence": 0.9, "status": "generated", "notes": "synthetic"},
            {"clip_id": "video_test", "highlight_id": "lvl3_evt_002", "rank": 2, "frame_start": 12, "frame_end": 13, "asset_path": "overlay_02.png", "confidence": 0.75, "status": "generated", "notes": "synthetic"},
        ],
        ["clip_id", "highlight_id", "rank", "frame_start", "frame_end", "asset_path", "confidence", "status", "notes"],
    )
    write_csv(
        visualization_manifest,
        [
            visual_row(1, "lvl3_evt_001"),
            visual_row(2, "lvl3_evt_002"),
        ],
        ["clip_id", "asset_id", "asset_type", "path", "source_artifact", "frame_start", "frame_end", "event_id", "is_versioned", "notes"],
    )
    write_csv(
        storyboard_manifest,
        [
            {"highlight_id": "lvl3_evt_001", "rank": 1, "clip_id": "video_test", "frame_start": 10, "frame_end": 11, "reference_frame_path": "", "minimap_path": "minimap_01.png", "notes": "synthetic"},
        ],
        ["highlight_id", "rank", "clip_id", "frame_start", "frame_end", "reference_frame_path", "minimap_path", "notes"],
    )
    return HighlightReviewConfig(
        highlights_csv=highlights_csv.as_posix(),
        events_json=events_json.as_posix(),
        overlay_validation_csv=overlay_csv.as_posix(),
        advanced_events_dir=events_dir.as_posix(),
        visualization_manifest_csv=visualization_manifest.as_posix(),
        storyboard_manifest_csv=storyboard_manifest.as_posix(),
        visualizations_dir=visuals_dir.as_posix(),
        output_dir=output_dir.as_posix(),
        reviewer="tester",
        reviewed_at="2026-06-07",
        top_highlights=2,
    )


def highlight_row(rank: int, highlight_id: str, confidence: float) -> dict[str, object]:
    frame = 8 + rank * 2
    return {
        "clip_id": "video_test",
        "highlight_id": highlight_id,
        "rank": rank,
        "score": 91.0 - rank,
        "event_type": "advanced_highlight",
        "frame_start": frame,
        "frame_end": frame + 1,
        "time_start_sec": frame / 10,
        "time_end_sec": (frame + 1) / 10,
        "primary_track_id": "robot_a",
        "secondary_track_ids": "ball_01",
        "zone": "middle_third",
        "confidence": confidence,
        "reliability": "provisional",
        "reason": "velocidad_norm=0.100; respaldo_level2",
        "source_event_ids": "lvl2_evt_test",
    }


def visual_row(rank: int, highlight_id: str) -> dict[str, object]:
    return {
        "clip_id": "video_test",
        "asset_id": f"minimap_highlight_{rank}",
        "asset_type": "png",
        "path": f"minimap_{rank:02d}.png",
        "source_artifact": "level3_highlights.csv",
        "frame_start": 10,
        "frame_end": 11,
        "event_id": highlight_id,
        "is_versioned": "true",
        "notes": "synthetic",
    }


if __name__ == "__main__":
    unittest.main()
