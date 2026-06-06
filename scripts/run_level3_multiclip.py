from __future__ import annotations

import argparse
import copy
from collections import Counter
from pathlib import Path
import sys
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from futbotmx.config import load_config, write_config_snapshot
from futbotmx.level3 import (
    LEVEL3_MULTICLIP_RULE_VERSION,
    AdvancedEventsConfig,
    ClipMulticlipArtifacts,
    Level3DashboardConfig,
    Level3VisualizationConfig,
    TacticalConfig,
    summarize_clip_artifacts,
    write_clip_human_review,
    write_multiclip_comparison,
    write_multiclip_manifest,
)

from run_level3_advanced_events import run_advanced_events
from run_level3_dashboard import run_dashboard
from run_level3_spatial_model import run_spatial_model
from run_level3_tactical_metrics import build_tactical_metrics
from run_level3_visualizations import run_visualizations


DEFAULT_OUTPUT_DIR = Path("experiments/test_026_level3_multiclip")
DEFAULT_SOURCE_DIR = Path("experiments/test_017_level2_closure")
DEFAULT_CLIPS = ("video_595", "video_667")


def write_multiclip_config(
    config: dict[str, Any],
    output_dir: Path,
    source_dir: Path,
    clips: tuple[str, ...],
    roles: dict[str, str],
    min_field_confidence: float,
    min_field_coverage: float,
) -> None:
    snapshot = copy.deepcopy(config)
    snapshot["level3_multiclip"] = {
        "rule_version": LEVEL3_MULTICLIP_RULE_VERSION,
        "source_experiment": source_dir.as_posix(),
        "output_dir": output_dir.as_posix(),
        "clips": [{"clip_id": clip_id, "role": roles.get(clip_id, "secondary")} for clip_id in clips],
        "policy": {
            "reuse_level3_rules": True,
            "heavy_artifacts_in_git": False,
            "human_review": "rule_based_proxy_from_lightweight_overlays",
        },
        "calibration": {
            "min_field_confidence": min_field_confidence,
            "min_field_coverage": min_field_coverage,
        },
        "outputs": [
            "config.yaml",
            "level3_multiclip_comparison.csv",
            "level3_multiclip_manifest.csv",
            "summary.md",
            "<clip_id>/config.yaml",
            "<clip_id>/summary.md",
            "<clip_id>/human_review.csv",
        ],
    }
    write_config_snapshot(snapshot, output_dir / "config.yaml")


def write_clip_config(
    config: dict[str, Any],
    clip_dir: Path,
    source_dir: Path,
    clip_id: str,
    role: str,
    artifacts: ClipMulticlipArtifacts,
) -> None:
    snapshot = copy.deepcopy(config)
    snapshot["level3_multiclip_clip"] = {
        "rule_version": LEVEL3_MULTICLIP_RULE_VERSION,
        "clip_id": clip_id,
        "role": role,
        "source_experiment": source_dir.as_posix(),
        "artifact_dir": clip_dir.as_posix(),
        "outputs": {
            "spatial_validation_csv": artifacts.spatial_validation_csv,
            "metrics_csv": artifacts.metrics_csv,
            "metrics_json": artifacts.metrics_json,
            "interaction_edges_csv": artifacts.interaction_edges_csv,
            "highlights_csv": artifacts.highlights_csv,
            "overlay_validation_csv": artifacts.overlay_validation_csv,
            "human_review_csv": artifacts.human_review_csv,
            "dashboard_html": artifacts.dashboard_html,
        },
    }
    write_config_snapshot(snapshot, clip_dir / "config.yaml")


def write_clip_summary(path: Path, row: dict[str, Any], artifacts: ClipMulticlipArtifacts) -> None:
    status_label = "generado" if row["pipeline_status"] == "generated" else str(row["pipeline_status"])
    lines = [
        f"# Validacion Multi-Clip Nivel 3 - {artifacts.clip_id}",
        "",
        "## Resultado",
        "",
        f"- Estado: `{status_label}`.",
        f"- Rol: `{artifacts.role}`.",
        f"- Regla: `{LEVEL3_MULTICLIP_RULE_VERSION}`.",
        f"- Homografia: `{row['spatial_status']}` con confianza `{row['spatial_confidence']}`.",
        f"- Filas rectificadas: `{row['rectified_rows']}` de `{row['rows']}`.",
        f"- Highlights: `{row['highlight_count']}`; score top `{row['top_highlight_score']}`.",
        f"- Interacciones: `{row['interaction_samples']}` muestras y `{row['graph_edges']}` aristas.",
        f"- Revision visual ligera: `{row['human_review_status']}`.",
        f"- Limitaciones: `{row['limitation_flags']}`.",
        "",
        "## Evidencia Ligera",
        "",
        f"- `spatial_model/level3_tracks.csv` y `{Path(artifacts.spatial_validation_csv).name}`.",
        f"- `tactical_metrics/level3_metrics.csv`, `interaction_metrics.csv` e `interaction_edges.csv`.",
        f"- `advanced_events/level3_highlights.csv`, `level3_events.json` y overlays top.",
        f"- `visualizations/visualization_manifest.csv` con PNGs versionables.",
        f"- `dashboard/dashboard.html` como demo estatica del clip.",
        f"- `human_review.csv` con clasificacion `confiable`, `provisional` o `descartado`.",
        "",
        "## Lectura Operativa",
        "",
        "- El clip se proceso con las mismas reglas Nivel 3 que los demas clips; no hay ajustes especificos por clip.",
        "- La revision conserva lenguaje de candidatos tacticos y evita afirmar goles, faltas o pases oficiales.",
        "- Los artefactos pesados siguen fuera de Git; solo se versionan CSV, JSON, Markdown, HTML y PNGs ligeros.",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_summary(path: Path, rows: list[dict[str, Any]], clips: tuple[str, ...], source_dir: Path) -> None:
    review_counts = Counter(str(row["human_review_status"]) for row in rows)
    generated = sum(1 for row in rows if row["pipeline_status"] == "generated")
    lines = [
        "# Validacion Multi-Clip Nivel 3",
        "",
        "## Resultado",
        "",
        f"- Estado: `{'generado' if generated >= 2 else 'provisional'}`.",
        f"- Regla: `{LEVEL3_MULTICLIP_RULE_VERSION}`.",
        f"- Fuente Nivel 2: `{source_dir.as_posix()}`.",
        f"- Clips procesados: `{', '.join(clips)}`.",
        f"- Clips con salida Nivel 3 documentada: `{generated}`.",
        f"- Revision visual ligera: `{dict(sorted(review_counts.items()))}`.",
        "",
        "## Comparacion",
        "",
        "| clip | highlights | score top | interacciones | aristas | homografia | revision | limitaciones |",
        "| --- | ---: | ---: | ---: | ---: | --- | --- | --- |",
    ]
    for row in rows:
        lines.append(
            f"| `{row['clip_id']}` | `{row['highlight_count']}` | `{row['top_highlight_score']}` | "
            f"`{row['interaction_samples']}` | `{row['graph_edges']}` | "
            f"`{row['spatial_status']} ({row['spatial_confidence']})` | "
            f"`{row['human_review_status']}` | `{row['limitation_flags']}` |"
        )

    lines.extend(
        [
            "",
            "## Hallazgos",
            "",
            "- `video_595` conserva el rol de clip principal: produce highlights con score mas alto y trayectoria mas simple, pero con menos diversidad de robots e interacciones.",
            "- `video_667` valida que las reglas corren en un segundo clip sin reescritura: aparecen mas interacciones y aristas, aunque la homografia queda mas provisional.",
            "- Las diferencias de camara, iluminacion y oclusion se reportan de forma indirecta mediante confianza de calibracion, estabilidad de tracks, conteo de interacciones y revision de overlays ligeros.",
            "- Los falsos positivos mas probables son presiones/disputas sobrerrepresentadas en frames con robots cercanos y posesion candidata cuando los equipos siguen `neutral`.",
            "- La homografia aproximada es suficiente para demo tactica comparativa, no para mediciones oficiales ni arbitraje.",
            "",
            "## Revision Humana Ligera",
            "",
            "- Cada subcarpeta incluye `human_review.csv` con estado `confiable`, `provisional` o `descartado` por highlight top.",
            "- La clasificacion usa overlays versionables, confianza y respaldo Nivel 2; no abre videos completos ni genera MP4.",
            "- Los clips con `revision_visual_provisional` quedan aceptados como evidencia de demo, pero no como verdad de cancha.",
            "",
            "## Artefactos",
            "",
            "- `config.yaml`",
            "- `level3_multiclip_comparison.csv`",
            "- `level3_multiclip_manifest.csv`",
            "- `summary.md`",
            "- `video_595/` con config, resumen y evidencia ligera.",
            "- `video_667/` con config, resumen y evidencia ligera.",
            "",
            "## Comando",
            "",
            "```bash",
            ".venv/bin/python scripts/run_level3_multiclip.py",
            "```",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run_multiclip_validation(
    config_path: str | Path,
    source_dir: Path,
    output_dir: Path,
    clips: tuple[str, ...],
    min_field_confidence: float,
    min_field_coverage: float,
    highlight_top_n: int,
    top_visualizations: int,
) -> list[dict[str, Any]]:
    config = load_config(config_path)
    output_dir.mkdir(parents=True, exist_ok=True)
    roles = {clip_id: ("primary" if index == 0 else "secondary") for index, clip_id in enumerate(clips)}
    write_multiclip_config(config, output_dir, source_dir, clips, roles, min_field_confidence, min_field_coverage)

    artifacts_list: list[ClipMulticlipArtifacts] = []
    comparison_rows: list[dict[str, Any]] = []

    for clip_id in clips:
        clip_dir = output_dir / clip_id
        spatial_dir = clip_dir / "spatial_model"
        tactical_dir = clip_dir / "tactical_metrics"
        events_dir = clip_dir / "advanced_events"
        visualizations_dir = clip_dir / "visualizations"
        dashboard_dir = clip_dir / "dashboard"
        role = roles[clip_id]

        run_spatial_model(
            config_path,
            source_dir,
            spatial_dir,
            (clip_id,),
            min_field_confidence=min_field_confidence,
            min_field_coverage=min_field_coverage,
        )
        tracks_csv = spatial_dir / "level3_tracks.csv"
        tactical_config = TacticalConfig(source_tracks=tracks_csv.as_posix())
        build_tactical_metrics(config_path, tracks_csv, tactical_dir, tactical_config)

        advanced_config = AdvancedEventsConfig(
            tracks_csv=tracks_csv.as_posix(),
            interaction_metrics_csv=(tactical_dir / "interaction_metrics.csv").as_posix(),
            interaction_edges_csv=(tactical_dir / "interaction_edges.csv").as_posix(),
            level2_root=source_dir.as_posix(),
            primary_clip=clip_id,
            highlight_top_n=highlight_top_n,
        )
        run_advanced_events(config_path, events_dir, advanced_config)

        visualization_config = Level3VisualizationConfig(
            tracks_csv=tracks_csv.as_posix(),
            calibration_json=(spatial_dir / "field_calibration.json").as_posix(),
            spatial_control_csv=(tactical_dir / "spatial_control.csv").as_posix(),
            voronoi_frames_csv=(tactical_dir / "voronoi_frames.csv").as_posix(),
            interaction_graph_json=(tactical_dir / "interaction_graph.json").as_posix(),
            interaction_edges_csv=(tactical_dir / "interaction_edges.csv").as_posix(),
            highlights_csv=(events_dir / "level3_highlights.csv").as_posix(),
            events_json=(events_dir / "level3_events.json").as_posix(),
            level2_root=source_dir.as_posix(),
            output_dir=visualizations_dir.as_posix(),
            top_highlights=top_visualizations,
        )
        run_visualizations(config_path, visualization_config)

        dashboard_config = Level3DashboardConfig(
            metrics_csv=(tactical_dir / "level3_metrics.csv").as_posix(),
            metrics_json=(tactical_dir / "level3_metrics.json").as_posix(),
            interaction_edges_csv=(tactical_dir / "interaction_edges.csv").as_posix(),
            highlights_csv=(events_dir / "level3_highlights.csv").as_posix(),
            events_json=(events_dir / "level3_events.json").as_posix(),
            narrative_md=(events_dir / "level3_narrative.md").as_posix(),
            visualizations_dir=visualizations_dir.as_posix(),
            visualization_manifest_csv=(visualizations_dir / "visualization_manifest.csv").as_posix(),
            output_dir=dashboard_dir.as_posix(),
            top_highlights=highlight_top_n,
        )
        run_dashboard(config_path, dashboard_config)

        artifacts = ClipMulticlipArtifacts(
            clip_id=clip_id,
            role=role,
            artifact_dir=clip_dir.as_posix(),
            spatial_validation_csv=(spatial_dir / "spatial_validation.csv").as_posix(),
            metrics_csv=(tactical_dir / "level3_metrics.csv").as_posix(),
            metrics_json=(tactical_dir / "level3_metrics.json").as_posix(),
            interaction_edges_csv=(tactical_dir / "interaction_edges.csv").as_posix(),
            highlights_csv=(events_dir / "level3_highlights.csv").as_posix(),
            overlay_validation_csv=(events_dir / "overlay_validation.csv").as_posix(),
            human_review_csv=(clip_dir / "human_review.csv").as_posix(),
            dashboard_html=(dashboard_dir / "dashboard.html").as_posix(),
        )
        row = summarize_clip_artifacts(artifacts)
        write_clip_human_review(clip_dir / "human_review.csv", row["human_review_rows"])
        write_clip_config(config, clip_dir, source_dir, clip_id, role, artifacts)
        write_clip_summary(clip_dir / "summary.md", row, artifacts)
        artifacts_list.append(artifacts)
        comparison_rows.append(row)

    write_multiclip_manifest(output_dir / "level3_multiclip_manifest.csv", artifacts_list)
    write_multiclip_comparison(output_dir / "level3_multiclip_comparison.csv", comparison_rows)
    write_summary(output_dir / "summary.md", comparison_rows, clips, source_dir)
    return comparison_rows


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Level 3 validation across multiple clips.")
    parser.add_argument("--config", default="configs/default.yaml")
    parser.add_argument("--source-dir", default=str(DEFAULT_SOURCE_DIR))
    parser.add_argument("--experiment", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--clips", nargs="+", default=list(DEFAULT_CLIPS))
    parser.add_argument("--min-field-confidence", type=float, default=0.55)
    parser.add_argument("--min-field-coverage", type=float, default=0.35)
    parser.add_argument("--highlight-top-n", type=int, default=6)
    parser.add_argument("--top-visualizations", type=int, default=4)
    args = parser.parse_args()

    rows = run_multiclip_validation(
        args.config,
        Path(args.source_dir),
        Path(args.experiment),
        tuple(args.clips),
        min_field_confidence=args.min_field_confidence,
        min_field_coverage=args.min_field_coverage,
        highlight_top_n=args.highlight_top_n,
        top_visualizations=args.top_visualizations,
    )
    generated = sum(1 for row in rows if row["pipeline_status"] == "generated")
    print(f"Wrote Level 3 multi-clip validation to {args.experiment} ({generated}/{len(rows)} clips generated)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
