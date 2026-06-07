from __future__ import annotations

import argparse
import copy
from pathlib import Path
import sys
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from futbotmx.config import load_config, write_config_snapshot
from futbotmx.level3 import (
    LEVEL3_DASHBOARD_RULE_VERSION,
    Level3DashboardConfig,
    build_dashboard,
    dashboard_config_to_dict,
)


DEFAULT_OUTPUT_DIR = Path("experiments/test_024_level3_dashboard")


def write_config(config: dict[str, Any], output_dir: Path, dashboard_config: Level3DashboardConfig) -> None:
    snapshot = copy.deepcopy(config)
    snapshot["level3_dashboard"] = {
        "rule_version": LEVEL3_DASHBOARD_RULE_VERSION,
        "format": "static_html",
        "architecture": "local_file_no_backend",
        **dashboard_config_to_dict(dashboard_config),
        "outputs": [
            "dashboard.html",
            "dashboard_manifest.csv",
            "config.yaml",
            "summary.md",
        ],
    }
    write_config_snapshot(snapshot, output_dir / "config.yaml")


def write_summary(path: Path, context: dict[str, Any]) -> None:
    config: Level3DashboardConfig = context["config"]
    summary = context["summary"]
    visual_assets = context["visual_assets"]
    manifest = context["manifest"]
    missing_assets = [name for name, asset in visual_assets.items() if not asset]
    lines = [
        "# Dashboard Ligero Nivel 3",
        "",
        "## Resultado",
        "",
        "- Estado: `generado`.",
        f"- Regla: `{LEVEL3_DASHBOARD_RULE_VERSION}`.",
        "- Formato: `HTML estatico local`.",
        "- Arquitectura: sin backend, sin login, sin dependencias nuevas.",
        f"- Clips integrados: `{', '.join(summary['clip_ids'])}`.",
        f"- Highlights enlazados: `{summary['highlights']}`.",
        f"- Highlights con revision humana: `{summary['reviewed_highlights']}`.",
        f"- Highlights descartados por revision: `{summary['discarded_highlights']}`.",
        f"- Metricas CSV: `{summary['metrics']}`.",
        f"- Eventos avanzados: `{summary['events']}`.",
        f"- Muestras de interaccion: `{summary['interaction_samples']}`.",
        f"- Aristas de grafo: `{summary['graph_edges']}`.",
        f"- Cadenas de pase conservadoras: `{summary['pass_chains']}`.",
        "",
        "## Secciones",
        "",
        "- Resumen con score de highlight, conteos de metricas, interacciones, aristas y cadenas.",
        "- Metricas por clip y control medio por robot.",
        "- Visualizaciones: storyboard, grafo, Voronoi en mini-mapa y Voronoi proyectado.",
            "- Highlights y aristas principales.",
            "- Revision humana opcional aplicada a highlights sin borrar el ranking original.",
            "- Evidencia con links relativos a CSV, JSON, Markdown y manifest.",
        "",
        "## Assets Integrados",
        "",
    ]
    for name, asset in visual_assets.items():
        if asset:
            lines.append(f"- `{name}`: `{asset['path']}`.")
        else:
            lines.append(f"- `{name}`: sin asset disponible.")
    lines.extend(
        [
            "",
            "## Manifest",
            "",
            f"- Filas en `dashboard_manifest.csv`: `{len(manifest)}`.",
            "- El dashboard referencia assets ligeros existentes; no duplica PNGs ni versiona video.",
            "",
            "## Limitaciones",
            "",
            "- El dashboard presenta analisis aproximado Nivel 3, no arbitraje oficial ni reproduccion de video completo.",
            "- Los links dependen de la estructura relativa de `experiments/` versionada en el repositorio.",
            "- Las visualizaciones se muestran como capturas estaticas para mantener el paquete liviano.",
            "",
            "## Artefactos",
            "",
            "- `dashboard.html`",
            "- `dashboard_manifest.csv`",
            "- `config.yaml`",
            "- `summary.md`",
            "",
            "## Comando",
            "",
            "```bash",
            ".venv/bin/python scripts/run_level3_dashboard.py",
            "```",
        ]
    )
    if missing_assets:
        lines.extend(["", "## Assets No Disponibles", ""])
        for name in missing_assets:
            lines.append(f"- `{name}`.")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run_dashboard(config_path: str | Path, dashboard_config: Level3DashboardConfig) -> dict[str, Any]:
    config = load_config(config_path)
    output_dir = Path(dashboard_config.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    context = build_dashboard(dashboard_config)
    write_config(config, output_dir, dashboard_config)
    write_summary(output_dir / "summary.md", context)
    return context


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate the static Level 3 dashboard.")
    parser.add_argument("--config", default="configs/default.yaml")
    parser.add_argument("--experiment", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--metrics-csv", default="experiments/test_021_level3_tactical_metrics/level3_metrics.csv")
    parser.add_argument("--metrics-json", default="experiments/test_021_level3_tactical_metrics/level3_metrics.json")
    parser.add_argument("--interaction-edges", default="experiments/test_021_level3_tactical_metrics/interaction_edges.csv")
    parser.add_argument("--highlights", default="experiments/test_022_level3_advanced_events/level3_highlights.csv")
    parser.add_argument("--events", default="experiments/test_022_level3_advanced_events/level3_events.json")
    parser.add_argument("--narrative", default="experiments/test_022_level3_advanced_events/level3_narrative.md")
    parser.add_argument("--visualizations-dir", default="experiments/test_023_level3_visualizations")
    parser.add_argument("--visualization-manifest", default="experiments/test_023_level3_visualizations/visualization_manifest.csv")
    parser.add_argument("--human-review", default="")
    parser.add_argument("--top-highlights", type=int, default=6)
    parser.add_argument("--top-edges", type=int, default=5)
    args = parser.parse_args()

    dashboard_config = Level3DashboardConfig(
        metrics_csv=args.metrics_csv,
        metrics_json=args.metrics_json,
        interaction_edges_csv=args.interaction_edges,
        highlights_csv=args.highlights,
        events_json=args.events,
        narrative_md=args.narrative,
        visualizations_dir=args.visualizations_dir,
        visualization_manifest_csv=args.visualization_manifest,
        human_review_csv=args.human_review,
        output_dir=args.experiment,
        top_highlights=args.top_highlights,
        top_edges=args.top_edges,
    )
    context = run_dashboard(args.config, dashboard_config)
    print(
        "Wrote Level 3 dashboard to "
        f"{args.experiment} ({len(context['manifest'])} manifest rows, {len(context['top_highlights'])} highlights shown)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
