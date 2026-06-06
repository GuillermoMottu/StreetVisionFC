from __future__ import annotations

import csv
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest

import matplotlib

matplotlib.use("Agg")

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from futbotmx.level3 import AdvancedEventsConfig, Level3DashboardConfig, Level3VisualizationConfig, TacticalConfig
from run_level3_advanced_events import run_advanced_events
from run_level3_dashboard import run_dashboard
from run_level3_spatial_model import run_spatial_model
from run_level3_tactical_metrics import build_tactical_metrics
from run_level3_visualizations import run_visualizations


class Level3IntegrationTests(unittest.TestCase):
    def test_lightweight_level3_pipeline_produces_core_artifacts(self) -> None:
        with TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            config_path = root / "config.yaml"
            source_dir = root / "level2_source"
            output_dir = root / "level3_pipeline"
            create_pipeline_fixture(config_path, source_dir)

            spatial_dir = output_dir / "spatial"
            run_spatial_model(config_path, source_dir, spatial_dir, ("video_test",), 0.5, 0.2)
            tracks_csv = spatial_dir / "level3_tracks.csv"

            tactical_dir = output_dir / "tactical"
            build_tactical_metrics(
                config_path,
                tracks_csv,
                tactical_dir,
                TacticalConfig(grid_x=4, grid_y=3, source_tracks=tracks_csv.as_posix()),
            )

            events_dir = output_dir / "events"
            run_advanced_events(
                config_path,
                events_dir,
                AdvancedEventsConfig(
                    tracks_csv=tracks_csv.as_posix(),
                    interaction_metrics_csv=(tactical_dir / "interaction_metrics.csv").as_posix(),
                    interaction_edges_csv=(tactical_dir / "interaction_edges.csv").as_posix(),
                    level2_root=source_dir.as_posix(),
                    primary_clip="video_test",
                    highlight_top_n=3,
                ),
            )

            visual_dir = output_dir / "visuals"
            run_visualizations(
                config_path,
                Level3VisualizationConfig(
                    tracks_csv=tracks_csv.as_posix(),
                    calibration_json=(spatial_dir / "field_calibration.json").as_posix(),
                    spatial_control_csv=(tactical_dir / "spatial_control.csv").as_posix(),
                    voronoi_frames_csv=(tactical_dir / "voronoi_frames.csv").as_posix(),
                    interaction_graph_json=(tactical_dir / "interaction_graph.json").as_posix(),
                    interaction_edges_csv=(tactical_dir / "interaction_edges.csv").as_posix(),
                    highlights_csv=(events_dir / "level3_highlights.csv").as_posix(),
                    events_json=(events_dir / "level3_events.json").as_posix(),
                    level2_root=source_dir.as_posix(),
                    output_dir=visual_dir.as_posix(),
                    top_highlights=2,
                    grid_x=4,
                    grid_y=3,
                ),
            )

            dashboard_dir = output_dir / "dashboard"
            dashboard_context = run_dashboard(
                config_path,
                Level3DashboardConfig(
                    metrics_csv=(tactical_dir / "level3_metrics.csv").as_posix(),
                    metrics_json=(tactical_dir / "level3_metrics.json").as_posix(),
                    interaction_edges_csv=(tactical_dir / "interaction_edges.csv").as_posix(),
                    highlights_csv=(events_dir / "level3_highlights.csv").as_posix(),
                    events_json=(events_dir / "level3_events.json").as_posix(),
                    narrative_md=(events_dir / "level3_narrative.md").as_posix(),
                    visualizations_dir=visual_dir.as_posix(),
                    visualization_manifest_csv=(visual_dir / "visualization_manifest.csv").as_posix(),
                    output_dir=dashboard_dir.as_posix(),
                    top_highlights=3,
                ),
            )

            self.assertTrue(tracks_csv.exists())
            self.assertTrue((tactical_dir / "level3_metrics.csv").exists())
            self.assertTrue((tactical_dir / "level3_metrics.json").exists())
            self.assertTrue((events_dir / "level3_events.json").exists())
            self.assertTrue((events_dir / "level3_highlights.csv").exists())
            self.assertTrue((visual_dir / "visualization_manifest.csv").exists())
            self.assertTrue((dashboard_dir / "dashboard.html").exists())

            metrics = read_csv(tactical_dir / "level3_metrics.csv")
            highlights = read_csv(events_dir / "level3_highlights.csv")
            visual_manifest = read_csv(visual_dir / "visualization_manifest.csv")
            metrics_json = json.loads((tactical_dir / "level3_metrics.json").read_text(encoding="utf-8"))

            self.assertTrue(any(row["metric_name"] == "frames_analyzed" for row in metrics))
            self.assertGreaterEqual(metrics_json["summary"]["interaction_samples"], 1)
            self.assertGreaterEqual(len(highlights), 1)
            self.assertTrue(any(row["asset_type"] == "png" for row in visual_manifest))
            self.assertGreater(dashboard_context["summary"]["highlights"], 0)
            self.assertIn("level3_metrics.csv", (dashboard_dir / "dashboard.html").read_text(encoding="utf-8"))


def create_pipeline_fixture(config_path: Path, source_dir: Path) -> None:
    clip_dir = source_dir / "video_test"
    clip_dir.mkdir(parents=True, exist_ok=True)
    write_tracks(clip_dir / "tracks_level2.csv")
    (clip_dir / "level2_events.json").write_text(
        json.dumps(
            [
                {
                    "event_id": "lvl2_evt_test",
                    "event_type": "possession_candidate",
                    "frame_start": 10,
                    "frame_end": 14,
                    "confidence": 0.8,
                }
            ],
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    (clip_dir / "level2_metrics.json").write_text(
        json.dumps({"summary": {"observed_frames": 6}, "possession_timeline": []}, indent=2) + "\n",
        encoding="utf-8",
    )
    (clip_dir / "summary.md").write_text("# Synthetic Level 2 clip\n", encoding="utf-8")
    config_path.write_text(
        "\n".join(
            [
                "level2_events:",
                "  zone_axis: y",
                "level2_closure:",
                "  clips:",
                "    - clip_id: video_test",
                "      role: synthetic",
                "      width: 120",
                "      height: 240",
                "      fps: 10.0",
                "",
            ]
        ),
        encoding="utf-8",
    )


def write_tracks(path: Path) -> None:
    fieldnames = ["frame", "track_id", "class_name", "x", "y", "bbox_x1", "bbox_y1", "bbox_x2", "bbox_y2", "confidence", "team"]
    rows: list[dict[str, object]] = []
    for index, frame in enumerate(range(10, 16)):
        ball_x = 50 + index * 5
        ball_y = 120
        rows.extend(
            [
                track_row(frame, "green_soccer_field_bt_01", "green_soccer_field", 60, 120, 10, 20, 110, 220, 0.95),
                track_row(frame, "ball_bt_01", "ball", ball_x, ball_y, ball_x - 2, ball_y - 2, ball_x + 2, ball_y + 2, 0.9),
                track_row(frame, "small_robot_bt_01", "small_robot", ball_x + 4, ball_y, ball_x, ball_y - 6, ball_x + 10, ball_y + 6, 0.92),
                track_row(frame, "small_robot_bt_02", "small_robot", 92, 120, 87, 114, 97, 126, 0.88),
            ]
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def track_row(
    frame: int,
    track_id: str,
    class_name: str,
    x: float,
    y: float,
    x1: float,
    y1: float,
    x2: float,
    y2: float,
    confidence: float,
) -> dict[str, object]:
    return {
        "frame": frame,
        "track_id": track_id,
        "class_name": class_name,
        "x": x,
        "y": y,
        "bbox_x1": x1,
        "bbox_y1": y1,
        "bbox_x2": x2,
        "bbox_y2": y2,
        "confidence": confidence,
        "team": "neutral",
    }


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


if __name__ == "__main__":
    unittest.main()
