from __future__ import annotations

import argparse
import copy
from pathlib import Path
import sys
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from futbotmx.artifact_names import ADVANCED_EVENTS_DIR, ADVANCED_EVENTS_JSON, HIGHLIGHTS_CSV, NARRATIVE_MD, VISUALIZATION_MANIFEST_CSV, VISUALIZATIONS_DIR
from futbotmx.config import load_config, write_config_snapshot
from futbotmx.level3 import (
    LEVEL3_REEL_RULE_VERSION,
    Level3ReelConfig,
    build_reel_package,
    reel_config_to_dict,
)


DEFAULT_OUTPUT_DIR = Path("experiments/test_025_reel")


def write_config(config: dict[str, Any], output_dir: Path, reel_config: Level3ReelConfig) -> None:
    snapshot = copy.deepcopy(config)
    snapshot["tactical_reel"] = {
        "rule_version": LEVEL3_REEL_RULE_VERSION,
        "format": "static_demo_plus_local_render_plan",
        "mp4_policy": "local_only_not_versioned",
        **reel_config_to_dict(reel_config),
        "outputs": [
            "reel_segments.csv",
            "reel_manifest.csv",
            "reel_narrative.md",
            "reel_render_plan.md",
            "render_reel_local.sh",
            "reel_ffmpeg_inputs.txt",
            "reel_demo.html",
            "reel_contact_sheet.png",
            "reel_thumb_rank_*.png",
            "summary.md",
        ],
    }
    write_config_snapshot(snapshot, output_dir / "config.yaml")


def write_summary(path: Path, context: dict[str, Any]) -> None:
    config: Level3ReelConfig = context["config"]
    segments = context["segments"]
    manifest = context["manifest"]
    summary = context["summary"]
    lines = [
        "# Reel final y demo de presentacion",
        "",
        "## Resultado",
        "",
        "- Estado: `generado`.",
        f"- Regla: `{LEVEL3_REEL_RULE_VERSION}`.",
        f"- Segmentos seleccionados: `{len(segments)}`.",
        f"- Clips incluidos: `{', '.join(summary['clips'])}`.",
        f"- Duracion sugerida: `{summary['duration_sec']:.1f}` segundos.",
        f"- Score top: `{summary['top_score']:.1f}`.",
        f"- Confianza minima seleccionada: `{summary['min_confidence']:.2f}`.",
        f"- Highlights con revision humana: `{summary['reviewed_highlights']}`.",
        f"- Highlights descartados por revision: `{summary['discarded_highlights']}`.",
        f"- Manifest rows: `{len(manifest)}`.",
        "- MP4 final: local y no versionado.",
        "",
        "## Segmentos",
        "",
    ]
    for segment in segments:
        lines.append(
            f"- `{segment['segment_id']}` rank `{segment['rank']}` `{segment['clip_id']}` "
            f"frames `{segment['frame_start']}-{segment['frame_end']}` "
            f"score `{float(segment['score']):.1f}` conf `{float(segment['confidence']):.2f}`."
        )
    lines.extend(
        [
            "",
            "## Narrativa",
            "",
            "- Cada thumbnail combina overlay de evento, mini-mapa y texto breve.",
            "- Los overlays muestran IDs/trails cuando existen en la evidencia tactica.",
            "- Si existe `human_review.csv`, los highlights descartados no entran al reel.",
            "- El lenguaje queda como highlight/proximidad/posesion candidata; no afirma goles ni decisiones oficiales.",
            "",
            "## Render Local",
            "",
            "```bash",
            f"cd {config.output_dir}",
            "bash render_reel_local.sh",
            "```",
            "",
            f"- Salida esperada fuera de Git: `{config.local_reel_path}`.",
            "- `*.mp4` esta ignorado por `.gitignore` y no se genera durante esta actividad.",
            "",
            "## Artefactos",
            "",
            "- `config.yaml`",
            "- `summary.md`",
            "- `reel_segments.csv`",
            "- `reel_manifest.csv`",
            "- `reel_narrative.md`",
            "- `reel_render_plan.md`",
            "- `render_reel_local.sh`",
            "- `reel_ffmpeg_inputs.txt`",
            "- `reel_demo.html`",
            "- `reel_contact_sheet.png`",
            "- `reel_thumb_rank_*.png`",
            "",
            "## Limitaciones",
            "",
            "- El paquete versiona capturas estaticas ligeras; el MP4 se renderiza localmente si se necesita.",
            "- La seleccion usa highlights rankeados y evidencia visual disponible, no revision arbitral.",
            "- Para un reel con video real, usar `reel_segments.csv` sobre videos locales fuera de Git.",
            "",
            "## Comando De Generacion",
            "",
            "```bash",
            ".venv/bin/python scripts/run_tactical_reel.py",
            "```",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run_reel(config_path: str | Path, reel_config: Level3ReelConfig) -> dict[str, Any]:
    config = load_config(config_path)
    output_dir = Path(reel_config.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    context = build_reel_package(reel_config)
    write_config(config, output_dir, reel_config)
    write_summary(output_dir / "summary.md", context)
    return context


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate final tactical reel demo package.")
    parser.add_argument("--config", default="configs/default.yaml")
    parser.add_argument("--experiment", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--highlights", default=f"experiments/test_022_advanced_events/{HIGHLIGHTS_CSV}")
    parser.add_argument("--events", default=f"experiments/test_022_advanced_events/{ADVANCED_EVENTS_JSON}")
    parser.add_argument("--overlay-validation", default="experiments/test_022_advanced_events/overlay_validation.csv")
    parser.add_argument("--advanced-events-dir", default=f"experiments/test_022_advanced_events")
    parser.add_argument("--visualization-manifest", default=f"experiments/test_023_visualizations/{VISUALIZATION_MANIFEST_CSV}")
    parser.add_argument("--storyboard-manifest", default="experiments/test_023_visualizations/highlight_storyboard_manifest.csv")
    parser.add_argument("--visualizations-dir", default="experiments/test_023_visualizations")
    parser.add_argument("--dashboard-html", default="experiments/test_024_dashboard/dashboard.html")
    parser.add_argument("--human-review", default="")
    parser.add_argument("--local-reel-path", default="local_outputs/tactical_reel/futbotmx_tactical_reel.mp4")
    parser.add_argument("--segment-count", type=int, default=4)
    parser.add_argument("--segment-duration-sec", type=float, default=3.0)
    parser.add_argument("--min-confidence", type=float, default=0.8)
    args = parser.parse_args()

    reel_config = Level3ReelConfig(
        highlights_csv=args.highlights,
        events_json=args.events,
        overlay_validation_csv=args.overlay_validation,
        advanced_events_dir=args.advanced_events_dir,
        visualization_manifest_csv=args.visualization_manifest,
        storyboard_manifest_csv=args.storyboard_manifest,
        visualizations_dir=args.visualizations_dir,
        dashboard_html=args.dashboard_html,
        human_review_csv=args.human_review,
        output_dir=args.experiment,
        local_reel_path=args.local_reel_path,
        segment_count=args.segment_count,
        segment_duration_sec=args.segment_duration_sec,
        min_confidence=args.min_confidence,
    )
    context = run_reel(args.config, reel_config)
    print(
        "Wrote tactical reel package to "
        f"{args.experiment} ({len(context['segments'])} segments, {len(context['manifest'])} manifest rows)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
