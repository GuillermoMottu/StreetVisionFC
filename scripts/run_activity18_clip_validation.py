from __future__ import annotations

import argparse
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from futbotmx.config import load_config
from futbotmx.level3 import ClipValidationSpec, build_activity18_package


DEFAULT_OUTPUT_DIR = Path("experiments/test_036_activity18_clip_validation")
LEVEL3_COMPARISON = "experiments/test_026_level3_multiclip/level3_multiclip_comparison.csv"


def default_specs() -> list[ClipValidationSpec]:
    return [
        ClipValidationSpec(
            clip_id="video_595",
            role="principal_level3",
            pipeline_scope="level3_reused",
            camera_condition="vertical_estable",
            light_condition="normal",
            occlusion_condition="baja",
            ball_visibility="alta",
            robot_visibility="media",
            field_visibility="alta",
            selection_reason="Clip principal Nivel 3 con dashboard, visualizaciones y highlights ya versionados.",
            level3_comparison_csv=LEVEL3_COMPARISON,
            level2_summary_md="experiments/test_017_level2_closure/video_595/summary.md",
        ),
        ClipValidationSpec(
            clip_id="video_667",
            role="secundario_level3",
            pipeline_scope="level3_reused",
            camera_condition="vertical_con_mas_interacciones",
            light_condition="normal",
            occlusion_condition="media",
            ball_visibility="alta",
            robot_visibility="alta",
            field_visibility="media",
            selection_reason="Clip secundario Nivel 3 con mas robots/interacciones y homografia mas exigente.",
            level3_comparison_csv=LEVEL3_COMPARISON,
            level2_summary_md="experiments/test_017_level2_closure/video_667/summary.md",
        ),
        ClipValidationSpec(
            clip_id="video_836",
            role="baseline_level2",
            pipeline_scope="level2_baseline",
            camera_condition="vertical_baseline",
            light_condition="normal",
            occlusion_condition="media",
            ball_visibility="media",
            robot_visibility="alta",
            field_visibility="alta",
            selection_reason="Baseline historico Nivel 2 con tracks ByteTrack densos, util para comparar degradacion sin Level 3 completo.",
            level2_summary_md="experiments/test_015_level2_multiclip/video_836/summary.md",
        ),
        ClipValidationSpec(
            clip_id="video_480",
            role="diagnostico_fallo",
            pipeline_scope="diagnostic_only",
            camera_condition="vertical_diagnostico",
            light_condition="normal",
            occlusion_condition="alta",
            ball_visibility="missing",
            robot_visibility="alta",
            field_visibility="media",
            selection_reason="Caso diagnostico con robots/campo detectados pero sin balon en la muestra ligera.",
            level2_summary_md="experiments/test_015_level2_multiclip/video_480/summary.md",
            diagnostic_summary_md="experiments/test_017_level2_closure/video_480/diagnostic_summary.md",
        ),
    ]


def main() -> int:
    parser = argparse.ArgumentParser(description="Build Activity 18 lightweight multi-clip validation package.")
    parser.add_argument("--config", default="configs/default.yaml")
    parser.add_argument("--experiment", default=DEFAULT_OUTPUT_DIR.as_posix())
    args = parser.parse_args()

    config = load_config(args.config)
    context = build_activity18_package(args.experiment, default_specs(), config)
    outcomes = {}
    for row in context["comparison_rows"]:
        outcomes[row["outcome_status"]] = outcomes.get(row["outcome_status"], 0) + 1
    print(f"Wrote Activity 18 clip validation to {args.experiment} ({outcomes})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
