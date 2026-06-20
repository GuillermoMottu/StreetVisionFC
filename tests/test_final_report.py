from __future__ import annotations

import csv
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from futbotmx.level3 import FinalReportConfig, build_final_report_package, scan_heavy_outputs, validate_report_links


def write_csv(path: Path, rows: list[dict[str, object]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


class FinalReportTests(unittest.TestCase):
    def test_build_final_report_writes_printable_html_manifest_and_link_validation(self) -> None:
        with TemporaryDirectory() as tmpdir:
            config = create_fixture(Path(tmpdir))

            context = build_final_report_package(config, {"project": {"name": "FutBotMX"}})

            output_dir = Path(config.output_dir)
            html = (output_dir / "final_report.html").read_text(encoding="utf-8")
            manifest = read_csv(output_dir / "final_report_manifest.csv")
            link_validation = read_csv(output_dir / "link_validation.csv")

            self.assertTrue((output_dir / "config.yaml").exists())
            self.assertTrue((output_dir / "summary.md").exists())
            self.assertTrue((output_dir / "pdf_export_plan.md").exists())
            self.assertTrue((output_dir / "render_final_report_pdf.sh").exists())
            self.assertIn("@media print", html)
            self.assertIn('data-ui-shell="futbotmx-ui-v1"', html)
            self.assertIn('data-product-flow="report"', html)
            self.assertIn("Reporte Final FutBotMX", html)
            self.assertIn("clip_validation_comparison.csv", html)
            self.assertIn("contact_sheet.png", html)
            self.assertEqual(context["summary"]["missing_links"], 0)
            self.assertEqual(context["summary"]["overlay_segments"], 2)
            self.assertTrue(all(row["exists"] == "true" for row in link_validation))
            self.assertTrue(any(row["asset_id"] == "local_pdf" and row["is_versioned"] == "false" for row in manifest))
            self.assertFalse(Path(config.local_pdf_path).exists())
            self.assertEqual(scan_heavy_outputs(output_dir), [])

    def test_validate_report_links_marks_missing_targets(self) -> None:
        with TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            existing = root / "ok.md"
            existing.write_text("# ok\n", encoding="utf-8")
            rows = validate_report_links(
                [
                    {"link_id": "ok", "label": "OK", "path": existing, "required": True, "notes": ""},
                    {"link_id": "missing", "label": "Missing", "path": root / "missing.md", "required": True, "notes": ""},
                ],
                root,
            )

            self.assertEqual([row["exists"] for row in rows], ["true", "false"])
            self.assertEqual(rows[0]["path"], "ok.md")


def create_fixture(root: Path) -> FinalReportConfig:
    report_dir = root / "report"
    readme = root / "README.md"
    dashboard = root / "human_review" / "dashboard" / "dashboard.html"
    reel = root / "human_review" / "reel" / "reel_demo.html"
    review_panel = root / "human_review" / "human_review_panel.html"
    final_demo = root / "final_demo_report" / "FINAL_DEMO_REPORT.html"
    closure_summary = root / "closure" / "LEVEL3_CLOSURE_SUMMARY.md"
    closure_checks = root / "closure" / "closure_checks.csv"
    full_summary = root / "full_analysis" / "summary.md"
    full_manifest = root / "full_analysis" / "full_analysis_manifest.csv"
    multiclip = root / "multiclip" / "level3_multiclip_comparison.csv"
    activity18_summary = root / "activity18" / "summary.md"
    activity18_comparison = root / "activity18" / "clip_validation_comparison.csv"
    activity18_failures = root / "activity18" / "failure_modes.csv"
    activity19_summary = root / "activity19" / "summary.md"
    activity19_segments = root / "activity19" / "video_overlay_segments.csv"
    activity19_contact_sheet = root / "activity19" / "contact_sheet.png"
    activity19_render_plan = root / "activity19" / "render_overlay_clip_plan.md"
    local_pdf = root / "local_outputs" / "final_report.pdf"

    for path, text in [
        (readme, "# FutBotMX\n"),
        (dashboard, "<!doctype html><html></html>\n"),
        (reel, "<!doctype html><html></html>\n"),
        (review_panel, "<!doctype html><html></html>\n"),
        (final_demo, "<!doctype html><html></html>\n"),
        (closure_summary, "# Closure\n"),
        (full_summary, "# Full analysis\n"),
        (activity18_summary, "# Activity 18\n"),
        (activity19_summary, "# Activity 19\n"),
        (activity19_render_plan, "# Render\n"),
    ]:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    activity19_contact_sheet.write_bytes(b"png")
    write_csv(
        closure_checks,
        [
            {"check_id": "unit_tests", "status": "pass", "evidence": "tests", "notes": "ok"},
            {"check_id": "links", "status": "pass", "evidence": "report", "notes": "ok"},
        ],
        ["check_id", "status", "evidence", "notes"],
    )
    write_csv(full_manifest, [{"asset_id": "summary", "path": "summary.md"}], ["asset_id", "path"])
    write_csv(
        multiclip,
        [
            {
                "clip_id": "video_595",
                "role": "principal",
                "pipeline_status": "generated",
                "highlight_count": 8,
                "top_highlight_score": 82.5,
                "interaction_samples": 57,
                "spatial_status": "usable",
                "spatial_confidence": 0.82,
            },
            {
                "clip_id": "video_667",
                "role": "secondary",
                "pipeline_status": "generated",
                "highlight_count": 4,
                "top_highlight_score": 74.0,
                "interaction_samples": 128,
                "spatial_status": "usable",
                "spatial_confidence": 0.73,
            },
        ],
        [
            "clip_id",
            "role",
            "pipeline_status",
            "highlight_count",
            "top_highlight_score",
            "interaction_samples",
            "spatial_status",
            "spatial_confidence",
        ],
    )
    write_csv(
        activity18_comparison,
        [
            {
                "clip_id": "video_595",
                "pipeline_scope": "level3_reused",
                "outcome_status": "exito",
                "homography_status": "usable",
                "homography_confidence": 0.82,
                "ball_status": "exito",
                "highlight_status": "degradacion",
                "limitation_flags": "revision_visual_provisional",
            },
            {
                "clip_id": "video_480",
                "pipeline_scope": "diagnostic_only",
                "outcome_status": "fallo_conocido",
                "homography_status": "not_evaluated",
                "homography_confidence": 0.0,
                "ball_status": "fallo",
                "highlight_status": "not_evaluated",
                "limitation_flags": "no_level3_outputs",
            },
        ],
        [
            "clip_id",
            "pipeline_scope",
            "outcome_status",
            "homography_status",
            "homography_confidence",
            "ball_status",
            "highlight_status",
            "limitation_flags",
        ],
    )
    write_csv(
        activity18_failures,
        [
            {
                "clip_id": "video_480",
                "failure_type": "perdida_de_balon",
                "severity": "alta",
                "status": "fallo_conocido",
                "evidence": "diagnostic",
                "recommendation": "revisar prompts",
            }
        ],
        ["clip_id", "failure_type", "severity", "status", "evidence", "recommendation"],
    )
    write_csv(
        activity19_segments,
        [
            overlay_row(1),
            overlay_row(2),
        ],
        [
            "segment_id",
            "rank",
            "clip_id",
            "highlight_id",
            "frame_start",
            "frame_end",
            "time_start_sec",
            "time_end_sec",
            "duration_sec",
            "score",
            "confidence",
            "reliability",
            "zone",
            "event_label",
            "source_overlay_path",
            "reference_frame_path",
            "minimap_path",
            "thumbnail_path",
            "selection_reason",
        ],
    )
    return FinalReportConfig(
        output_dir=report_dir.as_posix(),
        project_readme_md=readme.as_posix(),
        dashboard_html=dashboard.as_posix(),
        reel_html=reel.as_posix(),
        review_panel_html=review_panel.as_posix(),
        final_demo_report_html=final_demo.as_posix(),
        closure_summary_md=closure_summary.as_posix(),
        closure_checks_csv=closure_checks.as_posix(),
        full_analysis_summary_md=full_summary.as_posix(),
        full_analysis_manifest_csv=full_manifest.as_posix(),
        multiclip_comparison_csv=multiclip.as_posix(),
        activity18_summary_md=activity18_summary.as_posix(),
        activity18_comparison_csv=activity18_comparison.as_posix(),
        activity18_failure_modes_csv=activity18_failures.as_posix(),
        activity19_summary_md=activity19_summary.as_posix(),
        activity19_segments_csv=activity19_segments.as_posix(),
        activity19_contact_sheet_png=activity19_contact_sheet.as_posix(),
        activity19_render_plan_md=activity19_render_plan.as_posix(),
        local_pdf_path=local_pdf.as_posix(),
    )


def overlay_row(rank: int) -> dict[str, object]:
    frame = 120 + rank
    return {
        "segment_id": f"overlay_segment_{rank:02d}",
        "rank": rank,
        "clip_id": "video_595",
        "highlight_id": f"evt_{rank}",
        "frame_start": frame,
        "frame_end": frame + 1,
        "time_start_sec": rank * 1.5,
        "time_end_sec": rank * 1.5 + 0.1,
        "duration_sec": 2.5,
        "score": 84.0 - rank,
        "confidence": 0.9,
        "reliability": "provisional",
        "zone": "middle_third",
        "event_label": "posesion_candidata",
        "source_overlay_path": "overlay.png",
        "reference_frame_path": "",
        "minimap_path": "minimap.png",
        "thumbnail_path": f"thumb_{rank}.png",
        "selection_reason": "ranking_highlight",
    }


if __name__ == "__main__":
    unittest.main()
