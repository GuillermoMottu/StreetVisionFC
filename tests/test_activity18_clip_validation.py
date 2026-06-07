from __future__ import annotations

import csv
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from futbotmx.level3 import ClipValidationSpec, build_activity18_package, build_validation_context


def write_csv(path: Path, rows: list[dict[str, object]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


class Activity18ClipValidationTests(unittest.TestCase):
    def test_context_separates_success_degradation_and_known_failure(self) -> None:
        with TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            comparison = root / "level3_multiclip_comparison.csv"
            write_level3_comparison(comparison)
            baseline_summary = root / "video_baseline_summary.md"
            baseline_summary.write_text("# baseline\n", encoding="utf-8")
            diagnostic_summary = root / "video_missing_ball.md"
            diagnostic_summary.write_text("# diagnostic\n- Balon detectado: `0`.\n", encoding="utf-8")
            specs = [
                ClipValidationSpec(
                    clip_id="video_success",
                    role="primary",
                    pipeline_scope="level3_reused",
                    camera_condition="stable",
                    light_condition="normal",
                    occlusion_condition="baja",
                    ball_visibility="alta",
                    robot_visibility="alta",
                    field_visibility="alta",
                    selection_reason="solid level3",
                    level3_comparison_csv=comparison.as_posix(),
                ),
                ClipValidationSpec(
                    clip_id="video_degraded",
                    role="secondary",
                    pipeline_scope="level3_reused",
                    camera_condition="stable",
                    light_condition="normal",
                    occlusion_condition="media",
                    ball_visibility="alta",
                    robot_visibility="alta",
                    field_visibility="media",
                    selection_reason="provisional homography",
                    level3_comparison_csv=comparison.as_posix(),
                ),
                ClipValidationSpec(
                    clip_id="video_baseline",
                    role="baseline",
                    pipeline_scope="level2_baseline",
                    camera_condition="baseline",
                    light_condition="normal",
                    occlusion_condition="media",
                    ball_visibility="media",
                    robot_visibility="alta",
                    field_visibility="alta",
                    selection_reason="level2 only",
                    level2_summary_md=baseline_summary.as_posix(),
                ),
                ClipValidationSpec(
                    clip_id="video_missing_ball",
                    role="diagnostic",
                    pipeline_scope="diagnostic_only",
                    camera_condition="diagnostic",
                    light_condition="normal",
                    occlusion_condition="alta",
                    ball_visibility="missing",
                    robot_visibility="alta",
                    field_visibility="media",
                    selection_reason="ball not detected",
                    diagnostic_summary_md=diagnostic_summary.as_posix(),
                ),
            ]

            context = build_validation_context(specs)
            by_clip = {row["clip_id"]: row for row in context["comparison_rows"]}
            failure_types = {(row["clip_id"], row["failure_type"]) for row in context["failure_rows"]}

            self.assertEqual(by_clip["video_success"]["outcome_status"], "exito")
            self.assertEqual(by_clip["video_degraded"]["outcome_status"], "degradacion")
            self.assertEqual(by_clip["video_baseline"]["outcome_status"], "degradacion")
            self.assertEqual(by_clip["video_missing_ball"]["outcome_status"], "fallo_conocido")
            self.assertIn(("video_degraded", "mala_homografia"), failure_types)
            self.assertIn(("video_missing_ball", "perdida_de_balon"), failure_types)
            self.assertIn(("video_success", "falsos_highlights"), failure_types)

    def test_package_writes_per_clip_outputs_and_manifest(self) -> None:
        with TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            comparison = root / "level3_multiclip_comparison.csv"
            write_level3_comparison(comparison)
            output = root / "activity18"
            specs = [
                ClipValidationSpec(
                    clip_id="video_success",
                    role="primary",
                    pipeline_scope="level3_reused",
                    camera_condition="stable",
                    light_condition="normal",
                    occlusion_condition="baja",
                    ball_visibility="alta",
                    robot_visibility="alta",
                    field_visibility="alta",
                    selection_reason="solid level3",
                    level3_comparison_csv=comparison.as_posix(),
                )
            ]

            build_activity18_package(output, specs, {"project": "test"})
            comparison_rows = read_csv(output / "clip_validation_comparison.csv")
            manifest_rows = read_csv(output / "activity18_manifest.csv")

            self.assertEqual(comparison_rows[0]["outcome_status"], "exito")
            self.assertTrue((output / "video_success" / "summary.md").exists())
            self.assertIn("clip_validation_comparison.csv", {row["path"] for row in manifest_rows})
            self.assertTrue((output / "config.yaml").exists())


def write_level3_comparison(path: Path) -> None:
    rows = [
        {
            "clip_id": "video_success",
            "role": "primary",
            "pipeline_status": "generated",
            "spatial_status": "usable",
            "spatial_confidence": 0.91,
            "rows": 100,
            "rectified_rows": 100,
            "rectified_ratio": 1.0,
            "frames_analyzed": 61,
            "highlight_count": 5,
            "top_highlight_score": 90.0,
            "mean_highlight_confidence": 0.9,
            "provisional_highlights": 5,
            "doubtful_highlights": 0,
            "interaction_samples": 12,
            "graph_edges": 2,
            "mean_control_entropy": 0.4,
            "control_tracks": 3,
            "mean_track_control_percent": 33.3,
            "human_review_status": "provisional",
            "limitation_flags": "revision_visual_provisional",
            "artifact_dir": "video_success",
            "dashboard_path": "video_success/dashboard.html",
        },
        {
            "clip_id": "video_degraded",
            "role": "secondary",
            "pipeline_status": "generated",
            "spatial_status": "usable",
            "spatial_confidence": 0.7,
            "rows": 100,
            "rectified_rows": 90,
            "rectified_ratio": 0.9,
            "frames_analyzed": 61,
            "highlight_count": 3,
            "top_highlight_score": 70.0,
            "mean_highlight_confidence": 0.7,
            "provisional_highlights": 3,
            "doubtful_highlights": 0,
            "interaction_samples": 9,
            "graph_edges": 1,
            "mean_control_entropy": 0.6,
            "control_tracks": 2,
            "mean_track_control_percent": 50.0,
            "human_review_status": "provisional",
            "limitation_flags": "homografia_provisional|revision_visual_provisional",
            "artifact_dir": "video_degraded",
            "dashboard_path": "video_degraded/dashboard.html",
        },
    ]
    write_csv(
        path,
        rows,
        [
            "clip_id",
            "role",
            "pipeline_status",
            "spatial_status",
            "spatial_confidence",
            "rows",
            "rectified_rows",
            "rectified_ratio",
            "frames_analyzed",
            "highlight_count",
            "top_highlight_score",
            "mean_highlight_confidence",
            "provisional_highlights",
            "doubtful_highlights",
            "interaction_samples",
            "graph_edges",
            "mean_control_entropy",
            "control_tracks",
            "mean_track_control_percent",
            "human_review_status",
            "limitation_flags",
            "artifact_dir",
            "dashboard_path",
        ],
    )


if __name__ == "__main__":
    unittest.main()
