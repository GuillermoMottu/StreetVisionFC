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
    LEVEL3_VISUALIZATIONS_RULE_VERSION,
    Level3VisualizationConfig,
    build_visualizations,
    visualization_config_to_dict,
)


DEFAULT_OUTPUT_DIR = Path("experiments/test_023_level3_visualizations")


def write_config(config: dict[str, Any], output_dir: Path, visualization_config: Level3VisualizationConfig) -> None:
    snapshot = copy.deepcopy(config)
    snapshot["level3_visualizations"] = {
        "rule_version": LEVEL3_VISUALIZATIONS_RULE_VERSION,
        **visualization_config_to_dict(visualization_config),
        "outputs": [
            "voronoi_frame_*.png",
            "voronoi_original_frame_*.png",
            "interaction_graph.png",
            "minimap_highlight_*.png",
            "highlight_storyboard.png",
            "highlight_storyboard_manifest.csv",
            "visualization_manifest.csv",
            "summary.md",
        ],
    }
    write_config_snapshot(snapshot, output_dir / "config.yaml")


def write_summary(path: Path, outputs: dict[str, Any]) -> None:
    config: Level3VisualizationConfig = outputs["config"]
    manifest = outputs["manifest"]
    storyboard_rows = outputs["storyboard_rows"]
    asset_counts = Counter(str(row["asset_type"]) for row in manifest)
    asset_ids = Counter(str(row["asset_id"]).split("_")[0] for row in manifest)
    versioned = sum(1 for row in manifest if str(row["is_versioned"]) == "true")
    lines = [
        "# Visualizaciones Avanzadas Nivel 3",
        "",
        "## Resultado",
        "",
        "- Estado: `generado`.",
        f"- Regla: `{LEVEL3_VISUALIZATIONS_RULE_VERSION}`.",
        f"- Artefactos visuales indexados: `{len(manifest)}`.",
        f"- Artefactos versionados: `{versioned}`.",
        f"- Highlights en storyboard: `{len(storyboard_rows)}`.",
        f"- Grilla Voronoi: `{config.grid_x}x{config.grid_y}` (`{config.grid_cell_count}` celdas).",
        "",
        "## Tipos De Asset",
        "",
    ]
    for asset_type, count in sorted(asset_counts.items()):
        lines.append(f"- `{asset_type}`: `{count}`.")
    lines.extend(["", "## Familias", ""])
    for asset_id, count in sorted(asset_ids.items()):
        lines.append(f"- `{asset_id}`: `{count}`.")
    lines.extend(
        [
            "",
            "## Cobertura",
            "",
            "- Voronoi se renderiza en mini-mapa para frames representativos de `voronoi_frames.csv`.",
            "- Cuando existe overlay ligero Nivel 2 y homografia, tambien se genera `voronoi_original_frame_*.png` sobre esa referencia.",
            "- El grafo diferencia posesion, disputa, presion y proximidad con color y grosor por duracion/frecuencia.",
            "- Los mini-mapas de highlights muestran trails, zona de actividad y etiqueta del evento.",
            "- El storyboard combina referencia de frame Nivel 2, mini-mapa y texto conservador.",
            "",
            "## Limitaciones",
            "",
            "- Las proyecciones sobre frame original usan overlays ligeros existentes; no se abre ni versiona video completo.",
            "- La homografia sigue siendo aproximada, por lo que Voronoi proyectado se trata como validacion visual, no medicion oficial.",
            "- No se genero GIF; la secuencia queda como PNGs ligeros manifestados.",
            "",
            "## Artefactos",
            "",
            "- `config.yaml`",
            "- `voronoi_frame_*.png`",
            "- `voronoi_original_frame_*.png`",
            "- `interaction_graph.png`",
            "- `minimap_highlight_*.png`",
            "- `highlight_storyboard.png`",
            "- `highlight_storyboard_manifest.csv`",
            "- `visualization_manifest.csv`",
            "- `summary.md`",
            "",
            "## Comando",
            "",
            "```bash",
            ".venv/bin/python scripts/run_level3_visualizations.py",
            "```",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run_visualizations(config_path: str | Path, visualization_config: Level3VisualizationConfig) -> dict[str, Any]:
    config = load_config(config_path)
    output_dir = Path(visualization_config.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    outputs = build_visualizations(visualization_config)
    write_config(config, output_dir, visualization_config)
    write_summary(output_dir / "summary.md", outputs)
    return outputs


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate Level 3 advanced visualization assets.")
    parser.add_argument("--config", default="configs/default.yaml")
    parser.add_argument("--experiment", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--tracks", default="experiments/test_020_level3_spatial_model/level3_tracks.csv")
    parser.add_argument("--calibration", default="experiments/test_020_level3_spatial_model/field_calibration.json")
    parser.add_argument("--spatial-control", default="experiments/test_021_level3_tactical_metrics/spatial_control.csv")
    parser.add_argument("--voronoi-frames", default="experiments/test_021_level3_tactical_metrics/voronoi_frames.csv")
    parser.add_argument("--interaction-graph", default="experiments/test_021_level3_tactical_metrics/interaction_graph.json")
    parser.add_argument("--interaction-edges", default="experiments/test_021_level3_tactical_metrics/interaction_edges.csv")
    parser.add_argument("--highlights", default="experiments/test_022_level3_advanced_events/level3_highlights.csv")
    parser.add_argument("--events", default="experiments/test_022_level3_advanced_events/level3_events.json")
    parser.add_argument("--level2-root", default="experiments/test_017_level2_closure")
    parser.add_argument("--top-highlights", type=int, default=4)
    args = parser.parse_args()

    visualization_config = Level3VisualizationConfig(
        tracks_csv=args.tracks,
        calibration_json=args.calibration,
        spatial_control_csv=args.spatial_control,
        voronoi_frames_csv=args.voronoi_frames,
        interaction_graph_json=args.interaction_graph,
        interaction_edges_csv=args.interaction_edges,
        highlights_csv=args.highlights,
        events_json=args.events,
        level2_root=args.level2_root,
        output_dir=args.experiment,
        top_highlights=args.top_highlights,
    )
    outputs = run_visualizations(args.config, visualization_config)
    print(f"Wrote Level 3 visualizations to {args.experiment} ({len(outputs['manifest'])} assets)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
