from __future__ import annotations

import csv
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from futbotmx.level3 import VideoOverlayConfig, build_video_overlay_package, select_overlay_segments


def write_csv(path: Path, rows: list[dict[str, object]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


class Activity19VideoOverlayTests(unittest.TestCase):
    def test_select_overlay_segments_prefers_generated_high_confidence_overlays(self) -> None:
        config = VideoOverlayConfig(segment_count=2, min_confidence=0.8)
        highlights = [
            highlight_row(1, "evt_1", 0.9),
            highlight_row(2, "evt_2", 0.7),
            highlight_row(3, "evt_3", 0.95),
        ]
        overlays = [
            overlay_row("evt_1", "overlay_1.png", "generated"),
            overlay_row("evt_2", "overlay_2.png", "generated"),
            overlay_row("evt_3", "overlay_3.png", "missing"),
        ]

        segments = select_overlay_segments(highlights, overlays, [], config)

        self.assertEqual([segment["highlight_id"] for segment in segments], ["evt_1", "evt_2"])
        self.assertIn("overlay_ids_trails_event", segments[0]["selection_reason"])
        self.assertEqual(segments[0]["thumbnail_path"], "overlay_thumb_rank_01_video_test_frame_12.png")

    def test_build_video_overlay_package_writes_evidence_without_mp4(self) -> None:
        with TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            config = create_fixture(root)

            context = build_video_overlay_package(config)

            output_dir = Path(config.output_dir)
            self.assertEqual(len(context["segments"]), 3)
            self.assertTrue((output_dir / "video_overlay_segments.csv").exists())
            self.assertTrue((output_dir / "video_overlay_manifest.csv").exists())
            self.assertTrue((output_dir / "video_overlay_contact_sheet.png").exists())
            self.assertTrue((output_dir / "overlay_thumb_rank_01_video_test_frame_12.png").exists())
            self.assertTrue((output_dir / "render_overlay_clip.sh").exists())
            self.assertFalse(Path(config.local_mp4_path).exists())
            manifest = read_csv(output_dir / "video_overlay_manifest.csv")
            self.assertTrue(any(row["asset_id"] == "local_overlay_mp4" and row["is_versioned"] == "false" for row in manifest))


def create_fixture(root: Path) -> VideoOverlayConfig:
    events_dir = root / "events"
    visuals_dir = root / "visuals"
    output_dir = root / "activity19"
    local_mp4 = root / "local_outputs" / "overlay.mp4"
    highlights_csv = events_dir / "level3_highlights.csv"
    overlay_csv = events_dir / "overlay_validation.csv"
    storyboard_csv = visuals_dir / "highlight_storyboard_manifest.csv"
    events_dir.mkdir(parents=True)
    visuals_dir.mkdir(parents=True)
    for index in range(1, 4):
        draw_test_image(events_dir / f"overlay_{index}.png", f"overlay {index}")
        draw_test_image(visuals_dir / f"minimap_{index}.png", f"minimap {index}")
    write_csv(
        highlights_csv,
        [highlight_row(1, "evt_1", 0.9), highlight_row(2, "evt_2", 0.85), highlight_row(3, "evt_3", 0.82)],
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
    write_csv(
        overlay_csv,
        [
            overlay_row("evt_1", "overlay_1.png", "generated"),
            overlay_row("evt_2", "overlay_2.png", "generated"),
            overlay_row("evt_3", "overlay_3.png", "generated"),
        ],
        ["clip_id", "highlight_id", "rank", "frame_start", "frame_end", "asset_path", "confidence", "status", "notes"],
    )
    write_csv(
        storyboard_csv,
        [
            {"highlight_id": "evt_1", "rank": 1, "clip_id": "video_test", "frame_start": 12, "frame_end": 13, "reference_frame_path": "", "minimap_path": "minimap_1.png", "notes": "synthetic"},
            {"highlight_id": "evt_2", "rank": 2, "clip_id": "video_test", "frame_start": 14, "frame_end": 15, "reference_frame_path": "", "minimap_path": "minimap_2.png", "notes": "synthetic"},
            {"highlight_id": "evt_3", "rank": 3, "clip_id": "video_test", "frame_start": 16, "frame_end": 17, "reference_frame_path": "", "minimap_path": "minimap_3.png", "notes": "synthetic"},
        ],
        ["highlight_id", "rank", "clip_id", "frame_start", "frame_end", "reference_frame_path", "minimap_path", "notes"],
    )
    return VideoOverlayConfig(
        highlights_csv=highlights_csv.as_posix(),
        overlay_validation_csv=overlay_csv.as_posix(),
        advanced_events_dir=events_dir.as_posix(),
        storyboard_manifest_csv=storyboard_csv.as_posix(),
        visualizations_dir=visuals_dir.as_posix(),
        output_dir=output_dir.as_posix(),
        local_mp4_path=local_mp4.as_posix(),
        segment_count=3,
    )


def highlight_row(rank: int, highlight_id: str, confidence: float) -> dict[str, object]:
    frame = 10 + rank * 2
    return {
        "clip_id": "video_test",
        "highlight_id": highlight_id,
        "rank": rank,
        "score": 90.0 - rank,
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
        "reason": "velocidad_norm=0.100; posesion_candidata; zona=middle_third",
        "source_event_ids": "lvl2_evt_test",
    }


def overlay_row(highlight_id: str, asset_path: str, status: str) -> dict[str, object]:
    rank = int(highlight_id.split("_")[-1])
    frame = 10 + rank * 2
    return {
        "clip_id": "video_test",
        "highlight_id": highlight_id,
        "rank": rank,
        "frame_start": frame,
        "frame_end": frame + 1,
        "asset_path": asset_path,
        "confidence": 0.9,
        "status": status,
        "notes": "Overlay with IDs/trails/event label.",
    }


def draw_test_image(path: Path, label: str) -> None:
    fig, ax = plt.subplots(figsize=(2.4, 1.6))
    ax.set_axis_off()
    ax.text(0.5, 0.5, label, ha="center", va="center")
    fig.savefig(path, dpi=80)
    plt.close(fig)


if __name__ == "__main__":
    unittest.main()
