from __future__ import annotations

import argparse
import csv
import json
import shutil
from pathlib import Path
import sys
from typing import Any

import matplotlib.image as mpimg
import matplotlib.pyplot as plt

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from futbotmx.config import load_config, write_config_snapshot


DEFAULT_VISUALS_DIR = Path("experiments/test_014_level2_visualizations/video_836_real_visuals_120_180")
DEFAULT_METRICS_JSON = Path("experiments/test_012_level2_metrics/video_836_real_metrics_120_180/level2_metrics.json")
DEFAULT_EVENTS_JSON = Path("experiments/test_013_level2_events/video_836_real_events_120_180/level2_events.json")
DEFAULT_COMPARISON_CSV = Path("experiments/test_015_level2_multiclip/multiclip_comparison.csv")


def load_json(path: str | Path) -> Any:
    with Path(path).open("r", encoding="utf-8") as handle:
        return json.load(handle)


def read_csv_rows(path: str | Path) -> list[dict[str, str]]:
    with Path(path).open("r", newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def event_counts(events: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for event in events:
        event_type = str(event["event_type"])
        counts[event_type] = counts.get(event_type, 0) + 1
    return dict(sorted(counts.items()))


def reliability_counts(events: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for event in events:
        reliability = str(event.get("reliability", "unknown"))
        counts[reliability] = counts.get(reliability, 0) + 1
    return dict(sorted(counts.items()))


def build_demo_facts(metrics: dict[str, Any], events: list[dict[str, Any]], comparison_rows: list[dict[str, str]]) -> dict[str, Any]:
    summary = metrics.get("summary", {})
    possession = metrics.get("possession_by_robot", [])
    top_possession = possession[0] if possession else {}
    baseline = next((row for row in comparison_rows if row["clip_id"] == "video_836"), {})
    candidates = [row for row in comparison_rows if row.get("role") == "candidate"]
    diagnostic = next((row for row in comparison_rows if row["clip_id"] == "video_480"), {})
    return {
        "observed_frames": summary.get("observed_frames", 0),
        "track_count": summary.get("track_count", 0),
        "possession_seconds": summary.get("possession_assigned_seconds", 0),
        "top_possession_robot": top_possession.get("robot_id", "unknown"),
        "top_possession_percent": top_possession.get("percent_observed_time", 0),
        "event_counts": event_counts(events),
        "reliability_counts": reliability_counts(events),
        "baseline": baseline,
        "candidates": candidates,
        "diagnostic": diagnostic,
    }


def copy_demo_assets(visuals_dir: Path, output_dir: Path) -> list[dict[str, Any]]:
    assets = [
        ("event_timeline", visuals_dir / "event_timeline.png", output_dir / "event_timeline.png"),
        ("possession_timeline", visuals_dir / "possession_timeline.png", output_dir / "possession_timeline.png"),
        ("heatmap_ball", visuals_dir / "heatmap_class_ball.png", output_dir / "heatmap_class_ball.png"),
        ("heatmap_robot", visuals_dir / "heatmap_class_robot.png", output_dir / "heatmap_class_robot.png"),
    ]
    rows: list[dict[str, Any]] = []
    output_dir.mkdir(parents=True, exist_ok=True)
    for artifact, source, target in assets:
        shutil.copy2(source, target)
        rows.append({"artifact": artifact, "type": "png", "path": target.name, "source": str(source), "bytes": target.stat().st_size})
    return rows


def write_manifest(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = ["artifact", "type", "path", "source", "bytes"]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def image_or_placeholder(path: Path) -> Any:
    if path.exists():
        return mpimg.imread(path)
    return None


def add_image_axis(ax: Any, image_path: Path, title: str) -> None:
    image = image_or_placeholder(image_path)
    if image is None:
        ax.text(0.5, 0.5, "sin imagen", ha="center", va="center")
    else:
        ax.imshow(image)
    ax.set_title(title, fontsize=11)
    ax.set_axis_off()


def write_demo_board(output_path: Path, output_dir: Path, facts: dict[str, Any]) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig = plt.figure(figsize=(14, 10), constrained_layout=True)
    grid = fig.add_gridspec(3, 2, height_ratios=[0.85, 1.25, 1.25])

    ax_text = fig.add_subplot(grid[0, :])
    ax_text.set_axis_off()
    event_text = ", ".join(f"{key}: {value}" for key, value in facts["event_counts"].items())
    reliability_text = ", ".join(f"{key}: {value}" for key, value in facts["reliability_counts"].items())
    candidates = "; ".join(
        f"{row['clip_id']} frames {row['observed_frames']} tracks {row['track_count']}" for row in facts["candidates"]
    )
    text = (
        "FutBotMX Nivel 2 Demo\n"
        f"video_836: {facts['observed_frames']} frames, {facts['track_count']} tracks, "
        f"posesion {facts['possession_seconds']}s, robot principal {facts['top_possession_robot']} "
        f"({facts['top_possession_percent']}%).\n"
        f"Eventos: {event_text}. Confiabilidad: {reliability_text}.\n"
        f"Multi-clip: {candidates}. video_480 queda como diagnostico de balon."
    )
    ax_text.text(0.01, 0.95, text, va="top", ha="left", fontsize=12, linespacing=1.45)

    add_image_axis(fig.add_subplot(grid[1, 0]), output_dir / "event_timeline.png", "Timeline de eventos")
    add_image_axis(fig.add_subplot(grid[1, 1]), output_dir / "possession_timeline.png", "Timeline de posesion")
    add_image_axis(fig.add_subplot(grid[2, 0]), output_dir / "heatmap_class_ball.png", "Heatmap balon")
    add_image_axis(fig.add_subplot(grid[2, 1]), output_dir / "heatmap_class_robot.png", "Heatmap robots")
    fig.savefig(output_path, dpi=140)
    plt.close(fig)


def write_demo_local(path: Path, facts: dict[str, Any]) -> None:
    path.write_text(
        "# Demo local Nivel 2\n\n"
        "## Estado\n\n"
        "- Demo ligera generada como `demo_board.png` con timelines, metricas y heatmaps.\n"
        "- No se genero ni versiono MP4 en Git.\n"
        "- Si se genera un video anotado local, debe quedar en `outputs/videos/` y permanecer ignorado por `.gitignore`.\n\n"
        "## Contenido\n\n"
        "- `event_timeline.png`\n"
        "- `possession_timeline.png`\n"
        "- `heatmap_class_ball.png`\n"
        "- `heatmap_class_robot.png`\n"
        "- `demo_board.png`\n"
        "- `demo_manifest.csv`\n\n"
        "## Resumen Operativo\n\n"
        f"- Frames baseline: `{facts['observed_frames']}`.\n"
        f"- Tracks baseline: `{facts['track_count']}`.\n"
        f"- Posesion asignada baseline: `{facts['possession_seconds']}s`.\n",
        encoding="utf-8",
    )


def write_final_summary(path: Path, facts: dict[str, Any]) -> None:
    event_lines = "\n".join(f"- `{key}`: `{value}`." for key, value in facts["event_counts"].items())
    reliability_lines = "\n".join(f"- `{key}`: `{value}`." for key, value in facts["reliability_counts"].items())
    candidate_lines = "\n".join(
        f"- `{row['clip_id']}`: frames `{row['observed_frames']}`, tracks `{row['track_count']}`, "
        f"posesion `{row['possession_assigned_seconds']}s`, eventos "
        f"`{row['ball_recovery']}/{row['interception']}/{row['highlight_play']}`."
        for row in facts["candidates"]
    )
    diagnostic = facts["diagnostic"]
    path.write_text(
        "# Resumen Final Nivel 2\n\n"
        "## Alcance Completado\n\n"
        "- Metricas deportivas intermedias: posesion temporal, distancia y velocidad por track.\n"
        "- Eventos intermedios: recuperacion, intercepcion aproximada y jugada destacada con confiabilidad.\n"
        "- Visualizaciones: timelines, posesion y heatmaps separados.\n"
        "- Multi-clip real: `video_595`, `video_667`, baseline `video_836` y diagnostico `video_480`.\n"
        "- Demo ligera: `demo_board.png` y resumen local sin videos versionados.\n\n"
        "## Baseline video_836\n\n"
        f"- Frames observados: `{facts['observed_frames']}`.\n"
        f"- Tracks: `{facts['track_count']}`.\n"
        f"- Posesion asignada: `{facts['possession_seconds']}s`.\n"
        f"- Robot principal: `{facts['top_possession_robot']}` (`{facts['top_possession_percent']}%`).\n\n"
        "## Eventos\n\n"
        f"{event_lines}\n\n"
        "## Confiabilidad\n\n"
        f"{reliability_lines}\n\n"
        "## Multi-Clip\n\n"
        f"{candidate_lines}\n"
        f"- `video_480`: diagnostico de balon con `{diagnostic.get('ball_detections', 0)}` detecciones de balon "
        f"y `{diagnostic.get('robot_detections', 0)}` detecciones de robot.\n\n"
        "## Limitaciones\n\n"
        "- Las metricas estan en pixeles por perspectiva no rectificada.\n"
        "- `video_595` y `video_667` usan muestras sparse cada 30 frames, no tracking denso equivalente a `video_836`.\n"
        "- La intercepcion aproximada requiere validacion visual humana cuando exista cambio real de poseedor.\n\n"
        "## Entrega Ligera\n\n"
        "- `demo_board.png`\n"
        "- `demo_local.md`\n"
        "- `LEVEL2_FINAL_SUMMARY.md`\n"
        "- `demo_manifest.csv`\n"
        "- Capturas copiadas desde `test_014`.\n",
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Build a lightweight Level 2 demo package.")
    parser.add_argument("--config", default="configs/default.yaml")
    parser.add_argument("--output", default="experiments/test_016_level2_demo")
    parser.add_argument("--visuals-dir", default=str(DEFAULT_VISUALS_DIR))
    parser.add_argument("--metrics", default=str(DEFAULT_METRICS_JSON))
    parser.add_argument("--events", default=str(DEFAULT_EVENTS_JSON))
    parser.add_argument("--comparison", default=str(DEFAULT_COMPARISON_CSV))
    args = parser.parse_args()

    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=True)
    config = load_config(args.config)
    write_config_snapshot(config, output / "config.yaml")

    metrics = load_json(args.metrics)
    events = load_json(args.events)
    comparison_rows = read_csv_rows(args.comparison)
    facts = build_demo_facts(metrics, events, comparison_rows)
    manifest_rows = copy_demo_assets(Path(args.visuals_dir), output)
    write_demo_board(output / "demo_board.png", output, facts)
    manifest_rows.append(
        {
            "artifact": "demo_board",
            "type": "png",
            "path": "demo_board.png",
            "source": "generated",
            "bytes": (output / "demo_board.png").stat().st_size,
        }
    )
    write_manifest(output / "demo_manifest.csv", manifest_rows)
    write_demo_local(output / "demo_local.md", facts)
    write_final_summary(output / "LEVEL2_FINAL_SUMMARY.md", facts)
    print(f"Wrote Level 2 demo package to {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
