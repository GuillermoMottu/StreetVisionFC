from __future__ import annotations

import argparse
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from futbotmx.config import load_config
from futbotmx.level3 import FinalReportConfig, build_final_report_package


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate the FutBotMX printable final HTML report package.")
    parser.add_argument("--config", default="configs/default.yaml")
    parser.add_argument("--experiment", default="experiments/test_038_final_report")
    parser.add_argument("--project-readme", default="README.md")
    parser.add_argument("--dashboard-html", default="experiments/test_035_human_review/dashboard/dashboard.html")
    parser.add_argument("--reel-html", default="experiments/test_035_human_review/reel/reel_demo.html")
    parser.add_argument("--review-panel-html", default="experiments/test_035_human_review/human_review_panel.html")
    parser.add_argument("--final-demo-report", default="experiments/final_demo_report/FINAL_DEMO_REPORT.html")
    parser.add_argument("--closure-summary", default="experiments/test_027_level3_closure/LEVEL3_CLOSURE_SUMMARY.md")
    parser.add_argument("--closure-checks", default="experiments/test_027_level3_closure/closure_checks.csv")
    parser.add_argument("--full-analysis-summary", default="experiments/test_034_full_analysis/summary.md")
    parser.add_argument("--full-analysis-manifest", default="experiments/test_034_full_analysis/full_analysis_manifest.csv")
    parser.add_argument("--multiclip-comparison", default="experiments/test_026_level3_multiclip/level3_multiclip_comparison.csv")
    parser.add_argument("--activity18-summary", default="experiments/test_036_activity18_clip_validation/summary.md")
    parser.add_argument("--activity18-comparison", default="experiments/test_036_activity18_clip_validation/clip_validation_comparison.csv")
    parser.add_argument("--activity18-failures", default="experiments/test_036_activity18_clip_validation/failure_modes.csv")
    parser.add_argument("--activity19-summary", default="experiments/test_037_activity19_video_overlay/summary.md")
    parser.add_argument("--activity19-segments", default="experiments/test_037_activity19_video_overlay/video_overlay_segments.csv")
    parser.add_argument("--activity19-contact-sheet", default="experiments/test_037_activity19_video_overlay/video_overlay_contact_sheet.png")
    parser.add_argument("--activity19-render-plan", default="experiments/test_037_activity19_video_overlay/render_overlay_clip_plan.md")
    parser.add_argument("--local-pdf", default="local_outputs/activity20/futbotmx_final_report.pdf")
    args = parser.parse_args()

    report_config = FinalReportConfig(
        output_dir=args.experiment,
        project_readme_md=args.project_readme,
        dashboard_html=args.dashboard_html,
        reel_html=args.reel_html,
        review_panel_html=args.review_panel_html,
        final_demo_report_html=args.final_demo_report,
        closure_summary_md=args.closure_summary,
        closure_checks_csv=args.closure_checks,
        full_analysis_summary_md=args.full_analysis_summary,
        full_analysis_manifest_csv=args.full_analysis_manifest,
        multiclip_comparison_csv=args.multiclip_comparison,
        activity18_summary_md=args.activity18_summary,
        activity18_comparison_csv=args.activity18_comparison,
        activity18_failure_modes_csv=args.activity18_failures,
        activity19_summary_md=args.activity19_summary,
        activity19_segments_csv=args.activity19_segments,
        activity19_contact_sheet_png=args.activity19_contact_sheet,
        activity19_render_plan_md=args.activity19_render_plan,
        local_pdf_path=args.local_pdf,
    )
    context = build_final_report_package(report_config, load_config(args.config))
    print(
        "Wrote final report to "
        f"{args.experiment}/final_report.html "
        f"({context['summary']['links'] - context['summary']['missing_links']} links OK, "
        f"{context['summary']['missing_links']} missing)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
