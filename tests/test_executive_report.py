from __future__ import annotations

import csv
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from futbotmx.level3 import ExecutiveReportConfig, build_executive_report_package, narrative_example


def write_csv(path: Path, rows: list[dict[str, object]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


class ExecutiveReportTests(unittest.TestCase):
    def test_build_report_writes_html_manifest_summary_and_captures(self) -> None:
        with TemporaryDirectory() as tmpdir:
            config = create_fixture(Path(tmpdir))

            context = build_executive_report_package(config, {"project": {"name": "FutBotMX"}})

            output = Path(config.output_dir)
            html = (output / "FINAL_DEMO_REPORT.html").read_text(encoding="utf-8")
            manifest = read_csv(output / "final_demo_report_manifest.csv")

            self.assertTrue((output / "config.yaml").exists())
            self.assertTrue((output / "summary.md").exists())
            self.assertTrue((output / "assets" / "highlight_storyboard.png").exists())
            self.assertTrue((output / "assets" / "interaction_graph.png").exists())
            self.assertTrue((output / "assets" / "reel_contact_sheet.png").exists())
            self.assertIn("Reporte ejecutivo para evaluadores", html)
            self.assertIn("../dashboard/dashboard.html", html)
            self.assertIn("Tabla multi-clip", html)
            self.assertEqual(context["summary"]["closure_pass"], 2)
            self.assertEqual(context["summary"]["capture_count"], 3)
            self.assertTrue(any(row["asset_id"] == "final_demo_report" for row in manifest))

    def test_narrative_example_prefers_ranked_and_pass_chain_bullets(self) -> None:
        text = "\n".join(
            [
                "# Narrative",
                "- Rank `1` `video_a` frames `1-2`: score `90`.",
                "- Rank `2` `video_a` frames `3-4`: score `80`.",
                "- `video_a` `posesion`: cadena candidata.",
                "- Extra bullet.",
            ]
        )

        lines = narrative_example(text)

        self.assertEqual(len(lines), 3)
        self.assertTrue(lines[0].startswith("- Rank `1`"))
        self.assertIn("posesion", lines[2])


def create_fixture(root: Path) -> ExecutiveReportConfig:
    report_dir = root / "report"
    dashboard = root / "dashboard" / "dashboard.html"
    reel = root / "reel" / "reel_demo.html"
    review = root / "review" / "human_review_panel.html"
    closure_summary = root / "closure" / "LEVEL3_CLOSURE_SUMMARY.md"
    closure_checks = root / "closure" / "closure_checks.csv"
    comparison = root / "multiclip" / "level3_multiclip_comparison.csv"
    narrative = root / "events" / "level3_narrative.md"
    storyboard = root / "visuals" / "highlight_storyboard.png"
    graph = root / "visuals" / "interaction_graph.png"
    contact_sheet = root / "reel" / "reel_contact_sheet.png"

    for path in (dashboard, reel, review):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("<!doctype html><html></html>\n", encoding="utf-8")
    closure_summary.parent.mkdir(parents=True, exist_ok=True)
    closure_summary.write_text("# Closure\n", encoding="utf-8")
    write_csv(
        closure_checks,
        [
            {"check_id": "unit_tests", "status": "pass", "evidence": "tests", "notes": "ok"},
            {"check_id": "dashboard", "status": "pass", "evidence": "dashboard", "notes": "ok"},
        ],
        ["check_id", "status", "evidence", "notes"],
    )
    write_csv(
        comparison,
        [
            {
                "clip_id": "video_595",
                "role": "primary",
                "pipeline_status": "generated",
                "highlight_count": 10,
                "top_highlight_score": 82.5,
                "interaction_samples": 57,
                "spatial_status": "usable",
                "spatial_confidence": 0.82,
                "human_review_status": "provisional",
                "limitation_flags": "equipos_neutrales",
            },
            {
                "clip_id": "video_667",
                "role": "secondary",
                "pipeline_status": "generated",
                "highlight_count": 8,
                "top_highlight_score": 74.0,
                "interaction_samples": 128,
                "spatial_status": "usable",
                "spatial_confidence": 0.73,
                "human_review_status": "provisional",
                "limitation_flags": "homografia_provisional",
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
            "human_review_status",
            "limitation_flags",
        ],
    )
    narrative.parent.mkdir(parents=True, exist_ok=True)
    narrative.write_text("- Rank `1` `video_595` frames `122-123`: score `82`.\n", encoding="utf-8")
    for path in (storyboard, graph, contact_sheet):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"png")

    return ExecutiveReportConfig(
        output_dir=report_dir.as_posix(),
        dashboard_html=dashboard.as_posix(),
        reel_html=reel.as_posix(),
        review_panel_html=review.as_posix(),
        closure_summary_md=closure_summary.as_posix(),
        closure_checks_csv=closure_checks.as_posix(),
        multiclip_comparison_csv=comparison.as_posix(),
        narrative_md=narrative.as_posix(),
        storyboard_png=storyboard.as_posix(),
        interaction_graph_png=graph.as_posix(),
        reel_contact_sheet_png=contact_sheet.as_posix(),
    )


if __name__ == "__main__":
    unittest.main()
