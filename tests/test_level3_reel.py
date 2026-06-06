from __future__ import annotations

import csv
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest

import matplotlib

matplotlib.use("Agg")

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from futbotmx.level3 import Level3ReelConfig, build_reel_context, build_reel_package, select_reel_segments


def write_csv(path: Path, rows: list[dict[str, object]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


class Level3ReelTests(unittest.TestCase):
    def test_select_reel_segments_prefers_ranked_highlights_with_visual_evidence(self) -> None:
        with TemporaryDirectory() as tmpdir:
            config = create_fixture(Path(tmpdir), segment_count=3)
            context = build_reel_context(config)

            self.assertEqual(len(context["segments"]), 3)
            self.assertEqual(context["segments"][0]["highlight_id"], "lvl3_evt_001")
            self.assertIn("overlay_evento", context["segments"][0]["selection_reason"])
            self.assertIn("minimap", context["segments"][0]["selection_reason"])
            self.assertEqual(context["summary"]["duration_sec"], 9.0)

    def test_select_reel_segments_deduplicates_fallback_candidates(self) -> None:
        config = Level3ReelConfig(segment_count=3)
        highlights = [highlight_row(1, "lvl3_evt_001"), highlight_row(2, "lvl3_evt_002"), highlight_row(3, "lvl3_evt_003")]
        overlays = [{"highlight_id": "lvl3_evt_001", "asset_path": "overlay.png"}]
        visualizations = [{"asset_id": "minimap_highlight_1", "event_id": "lvl3_evt_001", "path": "minimap.png"}]

        segments = select_reel_segments(highlights, {}, overlays, visualizations, [], config)

        self.assertEqual([segment["highlight_id"] for segment in segments], ["lvl3_evt_001", "lvl3_evt_002", "lvl3_evt_003"])

    def test_build_reel_package_writes_lightweight_demo_and_manifest(self) -> None:
        with TemporaryDirectory() as tmpdir:
            config = create_fixture(Path(tmpdir), segment_count=3)

            context = build_reel_package(config)

            output_dir = Path(config.output_dir)
            self.assertTrue((output_dir / "reel_segments.csv").exists())
            self.assertTrue((output_dir / "reel_manifest.csv").exists())
            self.assertTrue((output_dir / "reel_demo.html").exists())
            self.assertTrue((output_dir / "reel_thumb_rank_01_video_test_frame_10.png").exists())
            self.assertTrue((output_dir / "reel_contact_sheet.png").exists())
            self.assertFalse((Path(config.local_reel_path)).exists())
            self.assertTrue(any(row["asset_id"] == "local_reel_mp4" and row["is_versioned"] == "false" for row in context["manifest"]))


def create_fixture(root: Path, segment_count: int) -> Level3ReelConfig:
    events_dir = root / "events"
    visuals_dir = root / "visuals"
    dashboard_html = root / "dashboard" / "dashboard.html"
    output_dir = root / "reel"
    highlights_csv = events_dir / "level3_highlights.csv"
    events_json = events_dir / "level3_events.json"
    overlay_csv = events_dir / "overlay_validation.csv"
    visualization_manifest = visuals_dir / "visualization_manifest.csv"
    storyboard_manifest = visuals_dir / "highlight_storyboard_manifest.csv"

    write_csv(
        highlights_csv,
        [highlight_row(1, "lvl3_evt_001"), highlight_row(2, "lvl3_evt_002"), highlight_row(3, "lvl3_evt_003")],
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
    events_json.write_text(
        json.dumps(
            [
                {"event_id": "lvl3_evt_001", "narrative": "Highlight provisional sintetico uno."},
                {"event_id": "lvl3_evt_002", "narrative": "Highlight provisional sintetico dos."},
                {"event_id": "lvl3_evt_003", "narrative": "Highlight provisional sintetico tres."},
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
            {"clip_id": "video_test", "highlight_id": "lvl3_evt_002", "rank": 2, "frame_start": 12, "frame_end": 13, "asset_path": "overlay_02.png", "confidence": 0.85, "status": "generated", "notes": "synthetic"},
            {"clip_id": "video_test", "highlight_id": "lvl3_evt_003", "rank": 3, "frame_start": 14, "frame_end": 15, "asset_path": "overlay_03.png", "confidence": 0.82, "status": "generated", "notes": "synthetic"},
        ],
        ["clip_id", "highlight_id", "rank", "frame_start", "frame_end", "asset_path", "confidence", "status", "notes"],
    )
    write_csv(
        visualization_manifest,
        [
            visual_row(1, "lvl3_evt_001"),
            visual_row(2, "lvl3_evt_002"),
            visual_row(3, "lvl3_evt_003"),
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
    dashboard_html.parent.mkdir(parents=True, exist_ok=True)
    dashboard_html.write_text("<!doctype html><html></html>\n", encoding="utf-8")
    return Level3ReelConfig(
        highlights_csv=highlights_csv.as_posix(),
        events_json=events_json.as_posix(),
        overlay_validation_csv=overlay_csv.as_posix(),
        advanced_events_dir=events_dir.as_posix(),
        visualization_manifest_csv=visualization_manifest.as_posix(),
        storyboard_manifest_csv=storyboard_manifest.as_posix(),
        visualizations_dir=visuals_dir.as_posix(),
        dashboard_html=dashboard_html.as_posix(),
        output_dir=output_dir.as_posix(),
        local_reel_path=(root / "local_outputs" / "reel.mp4").as_posix(),
        segment_count=segment_count,
    )


def highlight_row(rank: int, highlight_id: str) -> dict[str, object]:
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
        "confidence": 0.9,
        "reliability": "provisional",
        "reason": "velocidad_norm=0.100; posesion_candidata; zona=middle_third",
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
