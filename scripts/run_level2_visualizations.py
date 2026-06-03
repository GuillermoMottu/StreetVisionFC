from __future__ import annotations

import argparse
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from futbotmx.config import load_config, write_config_snapshot
from futbotmx.visualization import (
    build_heatmap_specs,
    summarize_visual_inputs,
    write_event_timeline,
    write_filtered_heatmap,
    write_manifest,
    write_possession_timeline,
)


def write_summary(
    path: Path,
    tracks: str,
    events: str,
    metrics: str,
    manifest_rows: list[dict[str, object]],
    visual_summary: dict[str, object],
) -> None:
    event_counts = visual_summary["event_counts"]
    reliability_counts = visual_summary["reliability_counts"]
    image_count = sum(1 for row in manifest_rows if row["type"] == "png")
    lines = [
        "# test_014_level2_visualizations_video_836",
        "",
        "## Configuracion",
        "",
        f"- Tracks: `{tracks}`.",
        f"- Eventos Nivel 2: `{events}`.",
        f"- Metricas Nivel 2: `{metrics}`.",
        "",
        "## Visualizaciones",
        "",
        f"- Imagenes ligeras generadas: `{image_count}`.",
        f"- Timeline de eventos: `event_timeline.png`.",
        f"- Timeline de posesion: `possession_timeline.png`.",
        "- Mapas de calor separados por clase y por track.",
        "",
        "## Resumen Del Clip",
        "",
        f"- Frames observados: `{visual_summary['observed_frames']}`.",
        f"- Tracks analizados: `{visual_summary['track_count']}`.",
        f"- Intervalos de posesion: `{visual_summary['possession_intervals']}`.",
        "",
        "## Eventos Por Tipo",
        "",
    ]
    if event_counts:
        for event_type, count in event_counts.items():  # type: ignore[union-attr]
            lines.append(f"- `{event_type}`: `{count}`.")
    else:
        lines.append("- Sin eventos.")
    lines.extend(["", "## Confiabilidad", ""])
    if reliability_counts:
        for reliability, count in reliability_counts.items():  # type: ignore[union-attr]
            lines.append(f"- `{reliability}`: `{count}`.")
    else:
        lines.append("- Sin confiabilidad reportada.")
    lines.extend(
        [
            "",
            "## Artefactos",
            "",
            "- `event_timeline.png`",
            "- `possession_timeline.png`",
            "- `heatmap_*.png`",
            "- `visualization_manifest.csv`",
            "- `visual_summary.md`",
            "- `config.yaml`",
            "",
            "## Politica De Archivos",
            "",
            "- No se genero ni versiono video completo.",
            "- Solo se versionan PNG/CSV/Markdown ligeros.",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate Level 2 lightweight timelines and separated heatmaps.")
    parser.add_argument("--config", default="configs/default.yaml")
    parser.add_argument("--tracks", required=True)
    parser.add_argument("--events", required=True)
    parser.add_argument("--metrics", required=True)
    parser.add_argument("--experiment", default="experiments/test_014_level2_visualizations/video_836_real_visuals_120_180")
    parser.add_argument("--width", type=int, default=1360)
    parser.add_argument("--height", type=int, default=1808)
    args = parser.parse_args()

    config = load_config(args.config)
    experiment = Path(args.experiment)
    experiment.mkdir(parents=True, exist_ok=True)
    write_config_snapshot(config, experiment / "config.yaml")

    manifest_rows: list[dict[str, object]] = []
    event_count = write_event_timeline(args.events, experiment / "event_timeline.png")
    manifest_rows.append({"artifact": "event_timeline", "type": "png", "path": "event_timeline.png", "rows": event_count})
    possession_count = write_possession_timeline(args.metrics, experiment / "possession_timeline.png")
    manifest_rows.append(
        {"artifact": "possession_timeline", "type": "png", "path": "possession_timeline.png", "rows": possession_count}
    )

    for spec in build_heatmap_specs(args.tracks):
        output = experiment / spec["filename"]
        if spec["kind"] == "class":
            rows = write_filtered_heatmap(
                args.tracks,
                output,
                width=args.width,
                height=args.height,
                class_name=spec["id"],
                title=f"Heatmap clase {spec['id']}",
            )
        else:
            rows = write_filtered_heatmap(
                args.tracks,
                output,
                width=args.width,
                height=args.height,
                track_id=spec["id"],
                title=f"Heatmap track {spec['id']}",
            )
        manifest_rows.append({"artifact": spec["id"], "type": "png", "path": spec["filename"], "rows": rows})

    visual_summary = summarize_visual_inputs(args.events, args.metrics)
    write_manifest(experiment / "visualization_manifest.csv", manifest_rows)
    write_summary(experiment / "visual_summary.md", args.tracks, args.events, args.metrics, manifest_rows, visual_summary)
    print(f"Wrote Level 2 visualizations experiment to {experiment}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
