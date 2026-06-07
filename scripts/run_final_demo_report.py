from __future__ import annotations

import argparse
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from futbotmx.config import load_config
from futbotmx.level3 import ExecutiveReportConfig, build_executive_report_package


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate the FutBotMX final executive demo report.")
    parser.add_argument("--config", default="configs/default.yaml")
    parser.add_argument("--experiment", default="experiments/final_demo_report")
    parser.add_argument("--dashboard-html", default="experiments/test_035_human_review/dashboard/dashboard.html")
    parser.add_argument("--reel-html", default="experiments/test_035_human_review/reel/reel_demo.html")
    parser.add_argument("--review-panel-html", default="experiments/test_035_human_review/human_review_panel.html")
    parser.add_argument("--closure-summary", default="experiments/test_027_level3_closure/LEVEL3_CLOSURE_SUMMARY.md")
    parser.add_argument("--closure-checks", default="experiments/test_027_level3_closure/closure_checks.csv")
    parser.add_argument("--multiclip-comparison", default="experiments/test_026_level3_multiclip/level3_multiclip_comparison.csv")
    parser.add_argument("--narrative", default="experiments/test_034_full_analysis/level3_events/level3_narrative.md")
    parser.add_argument("--storyboard", default="experiments/test_034_full_analysis/level3_visualizations/highlight_storyboard.png")
    parser.add_argument("--interaction-graph", default="experiments/test_034_full_analysis/level3_visualizations/interaction_graph.png")
    parser.add_argument("--reel-contact-sheet", default="experiments/test_035_human_review/reel/reel_contact_sheet.png")
    args = parser.parse_args()

    report_config = ExecutiveReportConfig(
        output_dir=args.experiment,
        dashboard_html=args.dashboard_html,
        reel_html=args.reel_html,
        review_panel_html=args.review_panel_html,
        closure_summary_md=args.closure_summary,
        closure_checks_csv=args.closure_checks,
        multiclip_comparison_csv=args.multiclip_comparison,
        narrative_md=args.narrative,
        storyboard_png=args.storyboard,
        interaction_graph_png=args.interaction_graph,
        reel_contact_sheet_png=args.reel_contact_sheet,
    )
    context = build_executive_report_package(report_config, load_config(args.config))
    print(
        "Wrote final demo report to "
        f"{args.experiment} ({context['summary']['capture_count']} captures, "
        f"{context['summary']['closure_pass']} closure checks pass)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
