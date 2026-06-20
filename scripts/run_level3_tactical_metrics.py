from __future__ import annotations

import argparse
import copy
import json
from collections import Counter
from pathlib import Path
import sys
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from futbotmx.artifact_names import (
    LEGACY_TACTICAL_METRICS_CSV,
    LEGACY_TACTICAL_METRICS_JSON,
    SPATIAL_TRACKS_CSV,
    TACTICAL_METRICS_CSV,
    TACTICAL_METRICS_JSON,
    mirror_legacy_file,
)
from futbotmx.config import load_config, write_config_snapshot
from futbotmx.level3 import (
    LEVEL3_TACTICAL_RULE_VERSION,
    TacticalConfig,
    compute_tactical_outputs,
    write_interaction_edges,
    write_interaction_metrics,
    write_level3_metrics_csv,
    write_level3_metrics_json,
    write_spatial_control_csv,
    write_voronoi_frames_csv,
)


DEFAULT_SOURCE_TRACKS = Path("experiments/test_020_spatial_model/spatial_tracks.csv")
DEFAULT_OUTPUT_DIR = Path("experiments/test_021_tactical_metrics")


def write_tactical_config(config: dict[str, Any], output_dir: Path, tactical_config: TacticalConfig) -> None:
    snapshot = copy.deepcopy(config)
    snapshot["tactical_metrics"] = {
        "rule_version": LEVEL3_TACTICAL_RULE_VERSION,
        "source_tracks": tactical_config.source_tracks,
        "output_dir": output_dir.as_posix(),
        "grid": {
            "x": tactical_config.grid_x,
            "y": tactical_config.grid_y,
            "cells": tactical_config.grid_cell_count,
        },
        "thresholds": {
            "possession_distance_norm": tactical_config.possession_distance_norm,
            "pressure_distance_norm": tactical_config.pressure_distance_norm,
            "robot_interaction_distance_norm": tactical_config.robot_interaction_distance_norm,
            "dispute_distance_norm": tactical_config.dispute_distance_norm,
            "min_track_confidence": tactical_config.min_track_confidence,
        },
        "outputs": [
            TACTICAL_METRICS_CSV,
            TACTICAL_METRICS_JSON,
            "spatial_control.csv",
            "voronoi_frames.csv",
            "interaction_metrics.csv",
            "interaction_edges.csv",
            "interaction_graph.json",
            "summary.md",
        ],
    }
    write_config_snapshot(snapshot, output_dir / "config.yaml")


def write_graph_json(path: Path, graph: dict[str, Any]) -> None:
    path.write_text(json.dumps(graph, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")


def write_summary(path: Path, outputs: dict[str, Any]) -> None:
    tactical_config: TacticalConfig = outputs["config"]
    tracks = outputs["tracks"]
    control_rows = outputs["control_rows"]
    control_aggregate = outputs["control_aggregate"]
    team_control_aggregate = outputs["team_control_aggregate"]
    frame_summaries = outputs["frame_summaries"]
    voronoi_frames = outputs["voronoi_frames"]
    interaction_samples = outputs["interaction_samples"]
    edge_rows = outputs["edge_rows"]
    metric_rows = outputs["metric_rows"]
    graph = outputs["graph"]

    clips = sorted({str(row["clip_id"]) for row in tracks})
    interaction_counts = Counter(str(row["metric_type"]) for row in interaction_samples)
    control_modes = Counter(str(row["control_mode"]) for row in control_rows)
    top_edges = sorted(edge_rows, key=lambda row: float(row["weight"]), reverse=True)[:5]

    lines = [
        "# Metricas tacticas avanzadas",
        "",
        "## Resultado",
        "",
        "- Estado: `calculado`.",
        f"- Regla: `{LEVEL3_TACTICAL_RULE_VERSION}`.",
        f"- Fuente: `{tactical_config.source_tracks}`.",
        f"- Clips analizados: `{', '.join(clips)}`.",
        f"- Frames con control espacial: `{len(frame_summaries)}`.",
        f"- Metricas exportadas: `{len(metric_rows)}`.",
        f"- Muestras de interaccion: `{len(interaction_samples)}`.",
        f"- Aristas de grafo: `{len(edge_rows)}`.",
        f"- Equipos con control agregado: `{len(team_control_aggregate)}`.",
        "",
        "## Control Espacial",
        "",
        f"- Grilla: `{tactical_config.grid_x}x{tactical_config.grid_y}` (`{tactical_config.grid_cell_count}` celdas).",
    ]
    for mode, count in sorted(control_modes.items()):
        lines.append(f"- Modo `{mode}`: `{count}` filas de control.")
    lines.extend(["", "## Control Por Equipo", ""])
    if team_control_aggregate:
        for item in team_control_aggregate:
            lines.append(
                f"- `{item['clip_id']}` `{item['team']}`: control medio `{item['mean_control_percent']}`%, "
                f"zona dominante `{item['dominant_zone']}`, contributors `{item['contributors']}`."
            )
    else:
        lines.append("- Sin etiquetas de equipo conocidas; se conserva fallback por robot individual.")
    lines.extend(["", "## Voronoi Aproximado", ""])
    lines.extend(
        [
            "- Voronoi se aproxima asignando cada celda normalizada al robot mas cercano.",
            "- Las regiones quedan recortadas automaticamente al rectangulo `[0,1] x [0,1]` de la cancha visible.",
            f"- Frames representativos guardados: `{len(voronoi_frames)}` en `voronoi_frames.csv`.",
        ]
    )
    lines.extend(["", "## Interacciones", ""])
    if interaction_counts:
        for metric_type, count in sorted(interaction_counts.items()):
            lines.append(f"- `{metric_type}`: `{count}`.")
    else:
        lines.append("- Sin interacciones detectadas.")
    lines.extend(["", "## Top Aristas", ""])
    if top_edges:
        for edge in top_edges:
            lines.append(
                f"- `{edge['clip_id']}` `{edge['source']}` -> `{edge['target']}` "
                f"(`{edge['edge_type']}`): frames `{edge['frames']}`, peso `{edge['weight']}`."
            )
    else:
        lines.append("- Sin aristas agregadas.")
    lines.extend(
        [
            "",
            "## Comparabilidad",
            "",
            f"- `video_595` y `video_667` usan el mismo contrato `{SPATIAL_TRACKS_CSV}`, la misma grilla y los mismos umbrales normalizados.",
            "- Si `team_assignment.csv` ya fue aplicado, se exportan metricas por equipo ademas del fallback por robot.",
            f"- Cada fila de `{TACTICAL_METRICS_CSV}`, `interaction_metrics.csv` e `interaction_edges.csv` incluye confianza o confiabilidad provisional.",
            "",
            "## Limitaciones",
            "",
            "- Control, Voronoi y presion son aproximaciones tacticas sobre homografia, no mediciones oficiales.",
            "- La posesion se conserva como candidato por proximidad; contacto fisico y reglas oficiales quedan fuera del alcance.",
            "- El grafo pondera duracion, distancia y confianza para comparacion interna de la demo.",
            "",
            "## Artefactos",
            "",
            "- `config.yaml`",
            f"- `{TACTICAL_METRICS_CSV}`",
            f"- `{TACTICAL_METRICS_JSON}`",
            "- `spatial_control.csv`",
            "- `voronoi_frames.csv`",
            "- `interaction_metrics.csv`",
            "- `interaction_edges.csv`",
            "- `interaction_graph.json`",
            "- `summary.md`",
            "",
            "## Comando",
            "",
            "```bash",
            ".venv/bin/python scripts/run_tactical_metrics.py",
            "```",
            "",
            "## Grafo",
            "",
            f"- Nodos: `{graph['summary']['nodes']}`.",
            f"- Aristas: `{graph['summary']['edges']}`.",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def build_tactical_metrics(
    config_path: str | Path,
    tracks_path: Path,
    output_dir: Path,
    tactical_config: TacticalConfig,
) -> dict[str, Any]:
    config = load_config(config_path)
    output_dir.mkdir(parents=True, exist_ok=True)
    outputs = compute_tactical_outputs(tracks_path, tactical_config)
    write_tactical_config(config, output_dir, tactical_config)
    write_level3_metrics_csv(output_dir / TACTICAL_METRICS_CSV, outputs["metric_rows"])
    write_level3_metrics_json(
        output_dir / TACTICAL_METRICS_JSON,
        outputs["metric_rows"],
        tactical_config,
        outputs["control_aggregate"],
        outputs["frame_summaries"],
        outputs["voronoi_frames"],
        outputs["interaction_samples"],
        outputs["edge_rows"],
        outputs["team_control_aggregate"],
    )
    mirror_legacy_file(output_dir / TACTICAL_METRICS_CSV, output_dir / LEGACY_TACTICAL_METRICS_CSV)
    mirror_legacy_file(output_dir / TACTICAL_METRICS_JSON, output_dir / LEGACY_TACTICAL_METRICS_JSON)
    write_spatial_control_csv(output_dir / "spatial_control.csv", outputs["control_rows"])
    write_voronoi_frames_csv(output_dir / "voronoi_frames.csv", outputs["voronoi_frames"])
    write_interaction_metrics(output_dir / "interaction_metrics.csv", outputs["interaction_samples"])
    write_interaction_edges(output_dir / "interaction_edges.csv", outputs["edge_rows"])
    write_graph_json(output_dir / "interaction_graph.json", outputs["graph"])
    write_summary(output_dir / "summary.md", outputs)
    return outputs


def main() -> int:
    parser = argparse.ArgumentParser(description="Compute tactical metrics from rectified tracks.")
    parser.add_argument("--config", default="configs/default.yaml")
    parser.add_argument("--tracks", default=str(DEFAULT_SOURCE_TRACKS))
    parser.add_argument("--experiment", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--grid-x", type=int, default=24)
    parser.add_argument("--grid-y", type=int, default=16)
    parser.add_argument("--possession-distance-norm", type=float, default=0.28)
    parser.add_argument("--pressure-distance-norm", type=float, default=0.32)
    parser.add_argument("--robot-interaction-distance-norm", type=float, default=0.22)
    parser.add_argument("--dispute-distance-norm", type=float, default=0.32)
    parser.add_argument("--min-track-confidence", type=float, default=0.5)
    args = parser.parse_args()

    tracks_path = Path(args.tracks)
    tactical_config = TacticalConfig(
        grid_x=args.grid_x,
        grid_y=args.grid_y,
        possession_distance_norm=args.possession_distance_norm,
        pressure_distance_norm=args.pressure_distance_norm,
        robot_interaction_distance_norm=args.robot_interaction_distance_norm,
        dispute_distance_norm=args.dispute_distance_norm,
        min_track_confidence=args.min_track_confidence,
        source_tracks=tracks_path.as_posix(),
    )
    outputs = build_tactical_metrics(args.config, tracks_path, Path(args.experiment), tactical_config)
    print(
        "Wrote tactical metrics to "
        f"{args.experiment} ({len(outputs['metric_rows'])} metrics, {len(outputs['edge_rows'])} graph edges)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
