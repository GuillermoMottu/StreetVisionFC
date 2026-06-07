from __future__ import annotations

import csv
import json
from dataclasses import replace
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from futbotmx.level3 import (
    Level3DashboardConfig,
    build_dashboard,
    build_dashboard_context,
    render_dashboard_html,
)


METRIC_FIELDS = [
    "clip_id",
    "metric_category",
    "entity_type",
    "entity_id",
    "class_name",
    "team",
    "metric_name",
    "value",
    "unit",
    "frame_start",
    "frame_end",
    "confidence",
    "source",
    "notes",
]


def write_csv(path: Path, rows: list[dict[str, object]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


class Level3DashboardTests(unittest.TestCase):
    def test_dashboard_context_summarizes_metrics_highlights_and_events(self) -> None:
        with TemporaryDirectory() as tmpdir:
            config = create_fixture(Path(tmpdir))

            context = build_dashboard_context(config)

            self.assertEqual(context["summary"]["clips"], 1)
            self.assertEqual(context["summary"]["top_highlight_score"], 90.0)
            self.assertEqual(context["summary"]["interaction_samples"], 3)
            self.assertEqual(len(context["pass_chains"]), 1)
            self.assertEqual(context["visual_assets"]["storyboard"]["path"], "highlight_storyboard.png")

    def test_dashboard_html_contains_visual_assets_and_evidence_links(self) -> None:
        with TemporaryDirectory() as tmpdir:
            config = create_fixture(Path(tmpdir))
            context = build_dashboard_context(config)

            html = render_dashboard_html(context)

            self.assertIn("Dashboard tactico avanzado", html)
            self.assertIn("storyboard.png", html)
            self.assertIn("level3_metrics.csv", html)
            self.assertIn("Highlights", html)
            self.assertIn("robot_a -> ball_01", html)

    def test_build_dashboard_writes_html_and_manifest(self) -> None:
        with TemporaryDirectory() as tmpdir:
            config = create_fixture(Path(tmpdir))

            context = build_dashboard(config)

            dashboard_html = Path(config.output_dir) / "dashboard.html"
            manifest_csv = Path(config.output_dir) / "dashboard_manifest.csv"
            self.assertTrue(dashboard_html.exists())
            self.assertTrue(manifest_csv.exists())
            self.assertGreater(dashboard_html.stat().st_size, 0)
            self.assertTrue(any(row["asset_id"] == "dashboard_html" for row in context["manifest"]))
            self.assertTrue(any(row["asset_id"] == "highlight_storyboard" for row in context["manifest"]))

    def test_human_review_discards_highlight_from_dashboard_top_list(self) -> None:
        with TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            config = create_fixture(root)
            review_csv = root / "review" / "human_review.csv"
            write_csv(
                review_csv,
                [
                    {"highlight_id": "lvl3_evt_test", "review_status": "descartado", "reviewer": "tester", "reviewed_at": "2026-06-07", "notes": "false positive"},
                    {"highlight_id": "lvl3_evt_other", "review_status": "confiable", "reviewer": "tester", "reviewed_at": "2026-06-07", "notes": "usable"},
                ],
                ["highlight_id", "review_status", "reviewer", "reviewed_at", "notes"],
            )
            reviewed = replace(config, human_review_csv=review_csv.as_posix())

            context = build_dashboard_context(reviewed)

            self.assertEqual(context["top_highlights"][0]["highlight_id"], "lvl3_evt_other")
            self.assertEqual(context["summary"]["discarded_highlights"], 1)


def create_fixture(root: Path) -> Level3DashboardConfig:
    metrics_csv = root / "metrics" / "level3_metrics.csv"
    metrics_json = root / "metrics" / "level3_metrics.json"
    edges_csv = root / "metrics" / "interaction_edges.csv"
    highlights_csv = root / "events" / "level3_highlights.csv"
    events_json = root / "events" / "level3_events.json"
    narrative_md = root / "events" / "level3_narrative.md"
    visual_dir = root / "visuals"
    visual_manifest = visual_dir / "visualization_manifest.csv"
    output_dir = root / "dashboard"

    write_csv(
        metrics_csv,
        [
            metric_row("video_test", "clip", "video_test", "frames_analyzed", 2, "frames"),
            metric_row("video_test", "clip", "video_test", "mean_control_entropy", 0.5, "ratio"),
            metric_row("video_test", "clip", "video_test", "interaction_samples", 3, "samples"),
            metric_row("video_test", "clip", "video_test", "graph_edges", 1, "edges"),
            metric_row("video_test", "track", "robot_a", "mean_control_percent", 64.5, "percent", "track_fallback; dominant_zone=middle_third"),
        ],
        METRIC_FIELDS,
    )
    metrics_json.write_text(
        json.dumps({"summary": {"frames_analyzed": 2, "interaction_samples": 3}}, indent=2) + "\n",
        encoding="utf-8",
    )
    write_csv(
        edges_csv,
        [
            {
                "clip_id": "video_test",
                "source": "robot_a",
                "target": "ball_01",
                "edge_type": "possession_candidate",
                "frames": 2,
                "duration_sec": 0.2,
                "frame_start": 10,
                "frame_end": 11,
                "mean_distance_norm": 0.1,
                "weight": 4.5,
                "confidence": 0.8,
                "reliability": "provisional",
                "evidence_frames": "10|11",
                "notes": "synthetic",
            }
        ],
        [
            "clip_id",
            "source",
            "target",
            "edge_type",
            "frames",
            "duration_sec",
            "frame_start",
            "frame_end",
            "mean_distance_norm",
            "weight",
            "confidence",
            "reliability",
            "evidence_frames",
            "notes",
        ],
    )
    write_csv(
        highlights_csv,
        [
            {
                "clip_id": "video_test",
                "highlight_id": "lvl3_evt_test",
                "rank": 1,
                "score": 90.0,
                "event_type": "advanced_highlight",
                "frame_start": 10,
                "frame_end": 11,
                "time_start_sec": 1.0,
                "time_end_sec": 1.1,
                "primary_track_id": "robot_a",
                "secondary_track_ids": "ball_01",
                "zone": "middle_third",
                "confidence": 0.8,
                "reliability": "provisional",
                "reason": "synthetic",
                "source_event_ids": "lvl2_evt_test",
            },
            {
                "clip_id": "video_test",
                "highlight_id": "lvl3_evt_other",
                "rank": 2,
                "score": 80.0,
                "event_type": "advanced_highlight",
                "frame_start": 12,
                "frame_end": 13,
                "time_start_sec": 1.2,
                "time_end_sec": 1.3,
                "primary_track_id": "robot_a",
                "secondary_track_ids": "ball_01",
                "zone": "middle_third",
                "confidence": 0.78,
                "reliability": "provisional",
                "reason": "synthetic secondary",
                "source_event_ids": "lvl2_evt_test",
            },
        ],
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
                {"event_id": "lvl3_evt_pass", "event_type": "pass_chain", "reliability": "dudoso"},
                {"event_id": "lvl3_evt_test", "event_type": "advanced_highlight", "reliability": "provisional"},
            ],
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    narrative_md.write_text("# Narrative\n", encoding="utf-8")
    write_csv(
        visual_manifest,
        [
            visual_row("highlight_storyboard", "highlight_storyboard.png", "multi_clip"),
            visual_row("interaction_graph", "interaction_graph.png", "multi_clip"),
            visual_row("voronoi_video_test_10", "voronoi_frame_video_test_10.png", "video_test"),
            visual_row("voronoi_original_video_test_10", "voronoi_original_frame_video_test_10.png", "video_test"),
        ],
        ["clip_id", "asset_id", "asset_type", "path", "source_artifact", "frame_start", "frame_end", "event_id", "is_versioned", "notes"],
    )
    return Level3DashboardConfig(
        metrics_csv=metrics_csv.as_posix(),
        metrics_json=metrics_json.as_posix(),
        interaction_edges_csv=edges_csv.as_posix(),
        highlights_csv=highlights_csv.as_posix(),
        events_json=events_json.as_posix(),
        narrative_md=narrative_md.as_posix(),
        visualizations_dir=visual_dir.as_posix(),
        visualization_manifest_csv=visual_manifest.as_posix(),
        output_dir=output_dir.as_posix(),
    )


def metric_row(
    clip_id: str,
    entity_type: str,
    entity_id: str,
    metric_name: str,
    value: float,
    unit: str,
    notes: str = "synthetic",
) -> dict[str, object]:
    return {
        "clip_id": clip_id,
        "metric_category": "interaction" if "interaction" in metric_name or metric_name == "graph_edges" else "spatial_control",
        "entity_type": entity_type,
        "entity_id": entity_id,
        "class_name": entity_type,
        "team": "neutral",
        "metric_name": metric_name,
        "value": value,
        "unit": unit,
        "frame_start": 10,
        "frame_end": 11,
        "confidence": 0.8,
        "source": "synthetic",
        "notes": notes,
    }


def visual_row(asset_id: str, path: str, clip_id: str) -> dict[str, object]:
    return {
        "clip_id": clip_id,
        "asset_id": asset_id,
        "asset_type": "png",
        "path": path,
        "source_artifact": "synthetic.csv",
        "frame_start": 10,
        "frame_end": 11,
        "event_id": "",
        "is_versioned": "true",
        "notes": "synthetic asset",
    }


if __name__ == "__main__":
    unittest.main()
