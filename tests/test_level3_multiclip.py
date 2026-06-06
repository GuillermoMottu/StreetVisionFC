from __future__ import annotations

import csv
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from futbotmx.level3 import (
    ClipMulticlipArtifacts,
    classify_review_status,
    summarize_clip_artifacts,
    write_clip_human_review,
    write_multiclip_comparison,
)


def write_csv(path: Path, rows: list[dict[str, object]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


class Level3MulticlipTests(unittest.TestCase):
    def test_review_classification_is_conservative(self) -> None:
        self.assertEqual(classify_review_status(0.9, True, "velocidad; respaldo_level2"), "confiable")
        self.assertEqual(classify_review_status(0.7, True, "presion_o_disputa"), "provisional")
        self.assertEqual(classify_review_status(0.8, False, "respaldo_level2"), "descartado")
        self.assertEqual(classify_review_status(0.3, True, "respaldo_level2"), "descartado")

    def test_summarize_clip_artifacts_writes_comparison_and_human_review(self) -> None:
        with TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            artifacts = create_fixture(root)

            row = summarize_clip_artifacts(artifacts)
            write_clip_human_review(root / "human_review.csv", row["human_review_rows"])
            write_multiclip_comparison(root / "level3_multiclip_comparison.csv", [row])

            review_rows = read_csv(root / "human_review.csv")
            comparison_rows = read_csv(root / "level3_multiclip_comparison.csv")

            self.assertEqual(row["clip_id"], "video_test")
            self.assertEqual(row["pipeline_status"], "generated")
            self.assertEqual(row["highlight_count"], 2)
            self.assertEqual(row["top_highlight_score"], 91.0)
            self.assertEqual(row["interaction_samples"], 7.0)
            self.assertEqual(row["human_review_status"], "provisional")
            self.assertIn("homografia_provisional", row["limitation_flags"])
            self.assertIn("equipos_neutrales", row["limitation_flags"])
            self.assertEqual(review_rows[0]["review_status"], "confiable")
            self.assertEqual(comparison_rows[0]["dashboard_path"], "dashboard/dashboard.html")


def create_fixture(root: Path) -> ClipMulticlipArtifacts:
    spatial_csv = root / "spatial_validation.csv"
    metrics_csv = root / "level3_metrics.csv"
    metrics_json = root / "level3_metrics.json"
    edges_csv = root / "interaction_edges.csv"
    highlights_csv = root / "level3_highlights.csv"
    overlay_csv = root / "overlay_validation.csv"
    human_review_csv = root / "human_review.csv"
    dashboard_html = Path("dashboard/dashboard.html")

    write_csv(
        spatial_csv,
        [
            {
                "clip_id": "video_test",
                "rows": 10,
                "frames": 5,
                "tracks": 3,
                "classes": "ball|small_robot",
                "calibration_id": "cal_test",
                "calibration_status": "usable",
                "calibration_confidence": 0.72,
                "rectified_rows": 9,
                "fallback_rows": 1,
                "out_of_bounds_rows": 0,
                "usable_rows": 8,
                "provisional_rows": 1,
                "x_norm_min": 0.1,
                "x_norm_max": 0.9,
                "y_norm_min": 0.2,
                "y_norm_max": 0.8,
            }
        ],
        [
            "clip_id",
            "rows",
            "frames",
            "tracks",
            "classes",
            "calibration_id",
            "calibration_status",
            "calibration_confidence",
            "rectified_rows",
            "fallback_rows",
            "out_of_bounds_rows",
            "usable_rows",
            "provisional_rows",
            "x_norm_min",
            "x_norm_max",
            "y_norm_min",
            "y_norm_max",
        ],
    )
    write_csv(
        metrics_csv,
        [
            metric_row("frames_analyzed", 5, "clip", "video_test"),
            metric_row("interaction_samples", 7, "clip", "video_test"),
            metric_row("graph_edges", 2, "clip", "video_test"),
            metric_row("mean_control_entropy", 0.4, "clip", "video_test"),
            metric_row("mean_control_percent", 55.0, "track", "robot_a"),
            metric_row("mean_control_percent", 45.0, "track", "robot_b"),
        ],
        [
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
        ],
    )
    metrics_json.write_text(
        json.dumps(
            {
                "summary": {"frames_analyzed": 5},
                "spatial_control": {
                    "aggregate_by_track": [
                        {"track_id": "robot_a", "team": "neutral"},
                        {"track_id": "robot_b", "team": "unknown"},
                    ]
                },
            },
            indent=2,
        )
        + "\n",
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
                "frames": 5,
                "duration_sec": 0.5,
                "frame_start": 10,
                "frame_end": 14,
                "mean_distance_norm": 0.1,
                "weight": 4.0,
                "confidence": 0.8,
                "reliability": "provisional",
                "evidence_frames": "10|11",
                "notes": "synthetic",
            },
            {
                "clip_id": "video_test",
                "source": "robot_b",
                "target": "robot_a",
                "edge_type": "pressure_candidate",
                "frames": 2,
                "duration_sec": 0.2,
                "frame_start": 11,
                "frame_end": 12,
                "mean_distance_norm": 0.2,
                "weight": 2.0,
                "confidence": 0.7,
                "reliability": "provisional",
                "evidence_frames": "11|12",
                "notes": "synthetic",
            },
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
            highlight_row("evt_1", 1, 91.0, 0.9, "velocidad; respaldo_level2"),
            highlight_row("evt_2", 2, 50.0, 0.6, "presion_o_disputa"),
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
    write_csv(
        overlay_csv,
        [
            {
                "clip_id": "video_test",
                "highlight_id": "evt_1",
                "rank": 1,
                "frame_start": 10,
                "frame_end": 11,
                "asset_path": "overlay_1.png",
                "confidence": 0.9,
                "status": "generated",
                "notes": "synthetic",
            },
            {
                "clip_id": "video_test",
                "highlight_id": "evt_2",
                "rank": 2,
                "frame_start": 12,
                "frame_end": 13,
                "asset_path": "overlay_2.png",
                "confidence": 0.6,
                "status": "generated",
                "notes": "synthetic",
            },
        ],
        ["clip_id", "highlight_id", "rank", "frame_start", "frame_end", "asset_path", "confidence", "status", "notes"],
    )
    return ClipMulticlipArtifacts(
        clip_id="video_test",
        role="primary",
        artifact_dir="video_test",
        spatial_validation_csv=spatial_csv.as_posix(),
        metrics_csv=metrics_csv.as_posix(),
        metrics_json=metrics_json.as_posix(),
        interaction_edges_csv=edges_csv.as_posix(),
        highlights_csv=highlights_csv.as_posix(),
        overlay_validation_csv=overlay_csv.as_posix(),
        human_review_csv=human_review_csv.as_posix(),
        dashboard_html=dashboard_html.as_posix(),
    )


def metric_row(metric_name: str, value: float, entity_type: str, entity_id: str) -> dict[str, object]:
    return {
        "clip_id": "video_test",
        "metric_category": "interaction" if metric_name in {"interaction_samples", "graph_edges"} else "spatial_control",
        "entity_type": entity_type,
        "entity_id": entity_id,
        "class_name": entity_type,
        "team": "neutral",
        "metric_name": metric_name,
        "value": value,
        "unit": "count",
        "frame_start": 10,
        "frame_end": 14,
        "confidence": 0.8,
        "source": "synthetic",
        "notes": "synthetic",
    }


def highlight_row(highlight_id: str, rank: int, score: float, confidence: float, reason: str) -> dict[str, object]:
    return {
        "clip_id": "video_test",
        "highlight_id": highlight_id,
        "rank": rank,
        "score": score,
        "event_type": "advanced_highlight",
        "frame_start": 10 + rank,
        "frame_end": 11 + rank,
        "time_start_sec": 1.0,
        "time_end_sec": 1.1,
        "primary_track_id": "robot_a",
        "secondary_track_ids": "ball_01",
        "zone": "middle_third",
        "confidence": confidence,
        "reliability": "provisional",
        "reason": reason,
        "source_event_ids": "lvl2_evt_1",
    }


if __name__ == "__main__":
    unittest.main()
