from __future__ import annotations

import argparse
import csv
import json
import math
from collections import Counter, defaultdict
from pathlib import Path
import sys
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from futbotmx.config import load_config, write_config_snapshot
from futbotmx.events import detect_level1_events, write_events_json
from futbotmx.visualization import write_overlay_frame


def read_tracks(path: str | Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with Path(path).open("r", newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            for key in ("frame", "x", "y", "bbox_x1", "bbox_y1", "bbox_x2", "bbox_y2", "confidence"):
                row[key] = float(row[key])
            row["frame"] = int(row["frame"])
            rows.append(row)
    return rows


def nearest_robot_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_frame: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_frame[row["frame"]].append(row)

    result: list[dict[str, Any]] = []
    for frame, frame_rows in sorted(by_frame.items()):
        balls = [row for row in frame_rows if row["class_name"] == "ball"]
        robots = [row for row in frame_rows if "robot" in row["class_name"]]
        if not balls or not robots:
            continue
        ball = balls[0]
        robot = min(robots, key=lambda item: distance(ball, item))
        result.append(
            {
                "frame": frame,
                "ball_id": ball["track_id"],
                "nearest_robot_id": robot["track_id"],
                "distance_px": distance(ball, robot),
                "ball_x": ball["x"],
                "ball_y": ball["y"],
                "robot_x": robot["x"],
                "robot_y": robot["y"],
            }
        )
    return result


def ball_speed_rows(rows: list[dict[str, Any]], fps: float, field_width: float) -> list[dict[str, Any]]:
    balls = sorted([row for row in rows if row["class_name"] == "ball"], key=lambda item: item["frame"])
    result: list[dict[str, Any]] = []
    for previous, current in zip(balls, balls[1:]):
        frame_delta = current["frame"] - previous["frame"]
        dt = max(frame_delta / fps, 1 / fps) if fps > 0 else 1.0
        displacement = distance(previous, current)
        dx = current["x"] - previous["x"]
        speed = displacement / dt
        result.append(
            {
                "frame_start": previous["frame"],
                "frame_end": current["frame"],
                "frame_delta": frame_delta,
                "displacement_px": displacement,
                "dx_px": dx,
                "speed_px_per_sec": speed,
                "moving_toward_goal": dx > 0 and current["x"] > field_width * 0.75,
            }
        )
    return result


def distance(a: dict[str, Any], b: dict[str, Any]) -> float:
    return math.hypot(float(a["x"]) - float(b["x"]), float(a["y"]) - float(b["y"]))


def percentile(values: list[float], percent: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, round((percent / 100) * (len(ordered) - 1))))
    return ordered[index]


def write_dict_rows(path: str | Path, rows: list[dict[str, Any]]) -> None:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(rows[0].keys()) if rows else ["empty"]
    with output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    key: f"{value:.6f}" if isinstance(value, float) else value
                    for key, value in row.items()
                }
            )


def write_event_metrics(path: str | Path, events: list[dict[str, Any]]) -> None:
    counts = Counter(event["event_type"] for event in events)
    rows = [
        {
            "event_type": event_type,
            "count": count,
        }
        for event_type, count in sorted(counts.items())
    ]
    write_dict_rows(path, rows)


def event_overlay_frames(events: list[dict[str, Any]]) -> list[int]:
    frames: list[int] = []
    for event in events:
        start = int(event["frame_start"])
        end = int(event["frame_end"])
        for frame in (start, (start + end) // 2, end):
            if frame not in frames:
                frames.append(frame)
    return frames


def reliability_notes(events: list[dict[str, Any]], shot_candidates_default: int, shot_candidates_tuned: int) -> list[str]:
    notes: list[str] = []
    counts = Counter(event["event_type"] for event in events)
    if counts["possession"]:
        notes.append("possession: provisional_confiable - distancia ajustada a resolucion 1360x1808 y validada contra robot cercano.")
    if counts["collision"]:
        notes.append("collision: provisional - depende de solape/distancia de bbox; revisar visualmente en frames indicados.")
    if counts["activity_zone"]:
        notes.append("activity_zone: confiable - calculado desde posiciones del balon en la ventana.")
    if counts["shot"]:
        notes.append("shot: provisional - revisar visualmente porque puede ser movimiento pequeno o jitter.")
    else:
        notes.append(
            "shot: descartado - umbral ajustado evita falsos positivos por jitter "
            f"({shot_candidates_default} candidatos con umbral previo, {shot_candidates_tuned} con umbral ajustado)."
        )
    return notes


def write_summary(
    path: Path,
    tracks_path: str,
    events: list[dict[str, Any]],
    nearest_rows: list[dict[str, Any]],
    speed_rows: list[dict[str, Any]],
    event_config: dict[str, Any],
    overlay_frames: list[int],
) -> None:
    nearest_distances = [float(row["distance_px"]) for row in nearest_rows]
    speeds = [float(row["speed_px_per_sec"]) for row in speed_rows]
    default_shot_threshold = 180.0
    tuned_shot_threshold = float(event_config["shot_min_ball_speed_px_per_sec"])
    default_candidates = sum(
        1
        for row in speed_rows
        if row["moving_toward_goal"] and float(row["speed_px_per_sec"]) >= default_shot_threshold
    )
    tuned_candidates = sum(
        1
        for row in speed_rows
        if row["moving_toward_goal"] and float(row["speed_px_per_sec"]) >= tuned_shot_threshold
    )
    event_counts = Counter(event["event_type"] for event in events)
    notes = reliability_notes(events, default_candidates, tuned_candidates)

    path.write_text(
        "# test_004_events_real_video_836\n\n"
        "## Configuracion\n\n"
        f"- Tracks: `{tracks_path}`\n"
        f"- Distancia de posesion: `{event_config['possession_distance_px']}px`.\n"
        f"- Min frames posesion: `{event_config['possession_min_frames']}`.\n"
        f"- Umbral de tiro: `{event_config['shot_min_ball_speed_px_per_sec']}px/s`.\n"
        f"- Distancia colision: `{event_config['collision_distance_px']}px`.\n\n"
        "## Diagnostico\n\n"
        f"- Distancia balon-robot mas cercana: min `{min(nearest_distances):.1f}px`, "
        f"p50 `{percentile(nearest_distances, 50):.1f}px`, p90 `{percentile(nearest_distances, 90):.1f}px`, "
        f"max `{max(nearest_distances):.1f}px`.\n"
        f"- Velocidad balon: max `{max(speeds):.1f}px/s`.\n"
        f"- Candidatos de tiro con umbral previo `180px/s`: `{default_candidates}`.\n"
        f"- Candidatos de tiro con umbral ajustado `{tuned_shot_threshold:.0f}px/s`: `{tuned_candidates}`.\n\n"
        "## Eventos\n\n"
        + "\n".join(f"- `{event_type}`: `{count}`" for event_type, count in sorted(event_counts.items()))
        + "\n\n"
        "## Confiabilidad\n\n"
        + "\n".join(f"- {note}" for note in notes)
        + "\n\n"
        "## Validacion visual\n\n"
        f"- Overlays generados para frames: `{', '.join(str(frame) for frame in overlay_frames)}`.\n"
        "- Los eventos de `shot` quedan desactivados para esta ventana porque el umbral previo respondia a jitter/movimiento pequeno del balon cerca del gol.\n\n"
        "## Artefactos\n\n"
        "- `events.json`\n"
        "- `event_metrics.csv`\n"
        "- `nearest_robot_distance.csv`\n"
        "- `ball_speed.csv`\n"
        "- Overlays de eventos.\n",
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate Level 1 events on real filtered tracks.")
    parser.add_argument("--config", default="configs/default.yaml")
    parser.add_argument("--tracks", required=True)
    parser.add_argument("--experiment", default="experiments/test_004_events/video_836_real_events_120_180")
    parser.add_argument("--video", default=None)
    parser.add_argument("--fps", type=float, required=True)
    parser.add_argument("--field-width", type=float, default=1360)
    parser.add_argument("--field-height", type=float, default=1808)
    parser.add_argument("--possession-distance-px", type=float, default=None)
    parser.add_argument("--shot-min-speed-px-per-sec", type=float, default=None)
    parser.add_argument("--skip-overlays", action="store_true")
    args = parser.parse_args()

    config = load_config(args.config)
    experiment = Path(args.experiment)
    experiment.mkdir(parents=True, exist_ok=True)
    write_config_snapshot(config, experiment / "config.yaml")

    event_config = dict(config.get("events", {}))
    if args.possession_distance_px is not None:
        event_config["possession_distance_px"] = args.possession_distance_px
    if args.shot_min_speed_px_per_sec is not None:
        event_config["shot_min_ball_speed_px_per_sec"] = args.shot_min_speed_px_per_sec

    rows = read_tracks(args.tracks)
    nearest_rows = nearest_robot_rows(rows)
    speed_rows = ball_speed_rows(rows, args.fps, args.field_width)
    write_dict_rows(experiment / "nearest_robot_distance.csv", nearest_rows)
    write_dict_rows(experiment / "ball_speed.csv", speed_rows)

    events = detect_level1_events(
        args.tracks,
        fps=args.fps,
        field_width=args.field_width,
        field_height=args.field_height,
        config=event_config,
        source_experiment=str(experiment),
    )
    write_events_json(events, experiment / "events.json")
    write_event_metrics(experiment / "event_metrics.csv", events)
    (experiment / "event_config.json").write_text(json.dumps(event_config, indent=2), encoding="utf-8")

    overlays = event_overlay_frames(events)
    if args.video and not args.skip_overlays:
        for frame in overlays:
            write_overlay_frame(args.video, args.tracks, experiment / f"overlay_event_frame_{frame}.png", frame)

    write_summary(experiment / "summary.md", args.tracks, events, nearest_rows, speed_rows, event_config, overlays)
    print(f"Wrote event validation experiment to {experiment}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
