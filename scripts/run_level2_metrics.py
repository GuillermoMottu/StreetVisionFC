from __future__ import annotations

import argparse
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from futbotmx.config import load_config, write_config_snapshot
from futbotmx.metrics import (
    compute_level2_metrics,
    read_tracks_csv,
    write_level2_metrics_csv,
    write_level2_metrics_json,
)


def write_summary(path: Path, metrics_file: Path, json_file: Path, metrics: object) -> None:
    data = metrics.to_json_dict()
    summary = data["summary"]
    source = data["source"]
    lines = [
        "# test_012_level2_metrics_video_836",
        "",
        "## Configuracion",
        "",
        f"- Tracks: `{source['tracks_file']}`.",
        f"- FPS: `{source['fps']}`.",
        f"- Resolucion/cancha usada: `{source['field_width']}x{source['field_height']}`.",
        f"- Umbral de posesion: `{summary['possession_threshold_px']}px`.",
        "",
        "## Resultados",
        "",
        f"- Frames observados: `{summary['observed_frames']}`.",
        f"- Tracks analizados: `{summary['track_count']}`.",
        f"- Tiempo observado aproximado: `{summary['total_observed_seconds']}s`.",
        f"- Tiempo con posesion asignada: `{summary['possession_assigned_seconds']}s`.",
        f"- Tiempo sin posesion asignada: `{summary['possession_unassigned_seconds']}s`.",
        "",
        "## Posesion Por Robot",
        "",
    ]
    if data["possession_by_robot"]:
        for item in data["possession_by_robot"]:
            lines.append(
                f"- `{item['robot_id']}` (`{item['team']}`): `{item['seconds']}s`, "
                f"`{item['percent_observed_time']}%`, distancia media `{item['mean_ball_distance_px']}px`."
            )
    else:
        lines.append("- Sin posesion asignada con el umbral configurado.")
    lines.extend(["", "## Posesion Por Equipo", ""])
    if data["possession_by_team"]:
        for item in data["possession_by_team"]:
            lines.append(f"- `{item['team']}`: `{item['seconds']}s`, `{item['percent_observed_time']}%`.")
    else:
        lines.append("- Sin posesion por equipo asignada.")
    lines.extend(
        [
            "",
            "## Supuestos",
            "",
            *[f"- {item}" for item in data["assumptions"]],
            "",
            "## Limitaciones",
            "",
            *[f"- {item}" for item in data["limitations"]],
            "",
            "## Artefactos",
            "",
            f"- `{metrics_file.name}`",
            f"- `{json_file.name}`",
            "- `config.yaml`",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Compute Level 2 intermediate sports metrics from tracks.csv.")
    parser.add_argument("--config", default="configs/default.yaml")
    parser.add_argument("--tracks", required=True)
    parser.add_argument("--experiment", default="experiments/test_012_level2_metrics/video_836_real_metrics_120_180")
    parser.add_argument("--fps", type=float, required=True)
    parser.add_argument("--field-width", type=float, default=1360)
    parser.add_argument("--field-height", type=float, default=1808)
    parser.add_argument("--possession-distance-px", type=float, default=None)
    args = parser.parse_args()

    config = load_config(args.config)
    experiment = Path(args.experiment)
    experiment.mkdir(parents=True, exist_ok=True)
    write_config_snapshot(config, experiment / "config.yaml")

    event_config = config.get("events", {})
    possession_distance = (
        args.possession_distance_px
        if args.possession_distance_px is not None
        else float(event_config.get("possession_distance_px", 190))
    )
    rows = read_tracks_csv(args.tracks)
    metrics = compute_level2_metrics(
        rows,
        fps=args.fps,
        possession_distance_px=possession_distance,
        tracks_file=args.tracks,
        field_width=args.field_width,
        field_height=args.field_height,
        source_experiment=str(experiment),
    )
    csv_path = experiment / "level2_metrics.csv"
    json_path = experiment / "level2_metrics.json"
    write_level2_metrics_csv(metrics, csv_path)
    write_level2_metrics_json(metrics, json_path)
    write_summary(experiment / "summary.md", csv_path, json_path, metrics)
    print(f"Wrote Level 2 metrics experiment to {experiment}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
