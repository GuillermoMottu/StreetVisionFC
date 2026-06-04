from __future__ import annotations

import csv
import json
import math
from collections import defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from futbotmx.tracking import read_tracks_csv


@dataclass(frozen=True)
class MetricRow:
    metric_category: str
    entity_type: str
    entity_id: str
    class_name: str
    team: str
    metric_name: str
    value: float
    unit: str
    frame_start: int | None = None
    frame_end: int | None = None
    notes: str = ""


@dataclass(frozen=True)
class Level2Metrics:
    rule_version: str
    source: dict[str, Any]
    summary: dict[str, Any]
    possession_by_robot: list[dict[str, Any]]
    possession_by_team: list[dict[str, Any]]
    possession_timeline: list[dict[str, Any]]
    track_metrics: list[dict[str, Any]]
    metric_rows: list[MetricRow]
    assumptions: list[str]
    limitations: list[str]

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "rule_version": self.rule_version,
            "source": self.source,
            "summary": self.summary,
            "possession_by_robot": self.possession_by_robot,
            "possession_by_team": self.possession_by_team,
            "possession_timeline": self.possession_timeline,
            "track_metrics": self.track_metrics,
            "assumptions": self.assumptions,
            "limitations": self.limitations,
        }


def _distance(a: dict[str, Any], b: dict[str, Any]) -> float:
    return math.hypot(float(a["x"]) - float(b["x"]), float(a["y"]) - float(b["y"]))


def _round(value: float, digits: int = 6) -> float:
    return round(float(value), digits)


def _frame_durations(frames: list[int], fps: float) -> dict[int, float]:
    unique_frames = sorted(set(frames))
    if not unique_frames or fps <= 0:
        return {frame: 0.0 for frame in unique_frames}
    if len(unique_frames) == 1:
        return {unique_frames[0]: 1 / fps}

    gaps = [b - a for a, b in zip(unique_frames, unique_frames[1:]) if b > a]
    fallback_gap = sorted(gaps)[len(gaps) // 2] if gaps else 1
    durations: dict[int, float] = {}
    for index, frame in enumerate(unique_frames):
        if index + 1 < len(unique_frames):
            frame_gap = max(1, unique_frames[index + 1] - frame)
        else:
            frame_gap = max(1, fallback_gap)
        durations[frame] = frame_gap / fps
    return durations


def _by_track(rows: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[str(row["track_id"])].append(row)
    return {track_id: sorted(items, key=lambda item: item["frame"]) for track_id, items in grouped.items()}


def _best_ball(rows: list[dict[str, Any]]) -> dict[str, Any] | None:
    balls = [row for row in rows if row["class_name"] == "ball"]
    if not balls:
        return None
    return max(balls, key=lambda item: float(item.get("confidence", 0.0)))


def _robots(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [row for row in rows if "robot" in str(row["class_name"])]


def _possession_by_frame(
    rows: list[dict[str, Any]],
    possession_distance_px: float,
) -> dict[int, dict[str, Any]]:
    by_frame: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_frame[int(row["frame"])].append(row)

    samples: dict[int, dict[str, Any]] = {}
    for frame, frame_rows in sorted(by_frame.items()):
        ball = _best_ball(frame_rows)
        robots = _robots(frame_rows)
        if ball is None or not robots:
            continue
        robot = min(robots, key=lambda item: _distance(ball, item))
        distance_px = _distance(ball, robot)
        if distance_px <= possession_distance_px:
            samples[frame] = {
                "frame": frame,
                "ball_id": ball["track_id"],
                "robot_id": robot["track_id"],
                "team": robot.get("team", "unknown") or "unknown",
                "distance_px": distance_px,
            }
    return samples


def _track_metrics(
    grouped_tracks: dict[str, list[dict[str, Any]]],
    frame_durations: dict[int, float],
    fps: float,
) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for track_id, track_rows in sorted(grouped_tracks.items()):
        total_distance = 0.0
        movement_seconds = 0.0
        segment_speeds: list[float] = []
        for previous, current in zip(track_rows, track_rows[1:]):
            frame_delta = int(current["frame"]) - int(previous["frame"])
            if frame_delta <= 0:
                continue
            duration = frame_delta / fps if fps > 0 else 0.0
            displacement = _distance(previous, current)
            total_distance += displacement
            movement_seconds += duration
            if duration > 0:
                segment_speeds.append(displacement / duration)

        observed_seconds = sum(frame_durations.get(int(row["frame"]), 0.0) for row in track_rows)
        first = track_rows[0]
        last = track_rows[-1]
        avg_speed = total_distance / movement_seconds if movement_seconds > 0 else 0.0
        results.append(
            {
                "track_id": track_id,
                "class_name": first["class_name"],
                "team": first.get("team", "unknown") or "unknown",
                "observations": len(track_rows),
                "frame_start": int(first["frame"]),
                "frame_end": int(last["frame"]),
                "observed_seconds": _round(observed_seconds),
                "movement_seconds": _round(movement_seconds),
                "total_distance_px": _round(total_distance),
                "avg_speed_px_per_sec": _round(avg_speed),
                "max_speed_px_per_sec": _round(max(segment_speeds) if segment_speeds else 0.0),
            }
        )
    return results


def _summarize_possession(
    possession_samples: dict[int, dict[str, Any]],
    frame_durations: dict[int, float],
    total_observed_seconds: float,
    key: str,
) -> list[dict[str, Any]]:
    grouped: dict[str, dict[str, Any]] = {}
    for frame, sample in possession_samples.items():
        entity_id = str(sample[key])
        current = grouped.setdefault(
            entity_id,
            {
                key: entity_id,
                "team": sample.get("team", "unknown"),
                "frames": 0,
                "seconds": 0.0,
                "mean_ball_distance_px": 0.0,
                "_distance_sum": 0.0,
            },
        )
        current["frames"] += 1
        current["seconds"] += frame_durations.get(frame, 0.0)
        current["_distance_sum"] += float(sample["distance_px"])

    result: list[dict[str, Any]] = []
    for item in grouped.values():
        frames = int(item["frames"])
        seconds = float(item["seconds"])
        result.append(
            {
                key: item[key],
                "team": item["team"],
                "frames": frames,
                "seconds": _round(seconds),
                "percent_observed_time": _round(100 * seconds / total_observed_seconds if total_observed_seconds > 0 else 0.0),
                "mean_ball_distance_px": _round(float(item["_distance_sum"]) / frames if frames else 0.0),
            }
        )
    return sorted(result, key=lambda item: (-float(item["seconds"]), str(item[key])))


def _possession_timeline(
    all_frames: list[int],
    possession_samples: dict[int, dict[str, Any]],
    frame_durations: dict[int, float],
    fps: float,
) -> list[dict[str, Any]]:
    intervals: list[dict[str, Any]] = []
    active_sample: dict[str, Any] | None = None
    start_frame: int | None = None
    end_frame: int | None = None
    duration = 0.0

    def flush() -> None:
        nonlocal active_sample, start_frame, end_frame, duration
        if active_sample is None or start_frame is None or end_frame is None:
            return
        intervals.append(
            {
                "frame_start": start_frame,
                "frame_end": end_frame,
                "time_start_sec": _round(start_frame / fps if fps > 0 else 0.0, 3),
                "time_end_sec": _round(end_frame / fps if fps > 0 else 0.0, 3),
                "duration_sec": _round(duration),
                "robot_id": active_sample["robot_id"],
                "team": active_sample["team"],
                "ball_id": active_sample["ball_id"],
                "mean_ball_distance_px": _round(active_sample["_distance_sum"] / active_sample["_frames"]),
            }
        )
        active_sample = None
        start_frame = None
        end_frame = None
        duration = 0.0

    for frame in sorted(set(all_frames)):
        sample = possession_samples.get(frame)
        owner = (sample["robot_id"], sample["team"]) if sample else None
        active_owner = (active_sample["robot_id"], active_sample["team"]) if active_sample else None
        if owner is None:
            flush()
            continue
        if active_sample is None or owner != active_owner:
            flush()
            active_sample = dict(sample)
            active_sample["_distance_sum"] = float(sample["distance_px"])
            active_sample["_frames"] = 1
            start_frame = frame
            end_frame = frame
            duration = frame_durations.get(frame, 0.0)
            continue
        active_sample["_distance_sum"] += float(sample["distance_px"])
        active_sample["_frames"] += 1
        end_frame = frame
        duration += frame_durations.get(frame, 0.0)

    flush()
    return intervals


def _metric_rows(
    track_metrics: list[dict[str, Any]],
    possession_by_robot: list[dict[str, Any]],
    possession_by_team: list[dict[str, Any]],
) -> list[MetricRow]:
    rows: list[MetricRow] = []
    for track in track_metrics:
        for metric_name, unit in (
            ("total_distance_px", "px"),
            ("avg_speed_px_per_sec", "px/s"),
            ("max_speed_px_per_sec", "px/s"),
            ("observed_seconds", "s"),
            ("observations", "frames"),
        ):
            rows.append(
                MetricRow(
                    metric_category="track",
                    entity_type="track",
                    entity_id=str(track["track_id"]),
                    class_name=str(track["class_name"]),
                    team=str(track["team"]),
                    metric_name=metric_name,
                    value=float(track[metric_name]),
                    unit=unit,
                    frame_start=int(track["frame_start"]),
                    frame_end=int(track["frame_end"]),
                )
            )
    for possession in possession_by_robot:
        robot_id = str(possession["robot_id"])
        for metric_name, unit in (
            ("seconds", "s"),
            ("percent_observed_time", "%"),
            ("mean_ball_distance_px", "px"),
        ):
            rows.append(
                MetricRow(
                    metric_category="possession",
                    entity_type="robot",
                    entity_id=robot_id,
                    class_name="robot",
                    team=str(possession["team"]),
                    metric_name=metric_name,
                    value=float(possession[metric_name]),
                    unit=unit,
                    notes="Ball assigned to nearest robot inside possession threshold.",
                )
            )
    for possession in possession_by_team:
        team_id = str(possession["team"])
        for metric_name, unit in (
            ("seconds", "s"),
            ("percent_observed_time", "%"),
        ):
            rows.append(
                MetricRow(
                    metric_category="possession",
                    entity_type="team",
                    entity_id=team_id,
                    class_name="team",
                    team=team_id,
                    metric_name=metric_name,
                    value=float(possession[metric_name]),
                    unit=unit,
                    notes="Team possession aggregates robot-level assignments.",
                )
            )
    return rows


def compute_level2_metrics(
    rows: list[dict[str, Any]],
    fps: float,
    possession_distance_px: float,
    tracks_file: str = "tracks.csv",
    field_width: float | None = None,
    field_height: float | None = None,
    source_experiment: str = "",
) -> Level2Metrics:
    frames = sorted({int(row["frame"]) for row in rows})
    frame_durations = _frame_durations(frames, fps)
    total_observed_seconds = sum(frame_durations.values())
    grouped_tracks = _by_track(rows)
    possession_samples = _possession_by_frame(rows, possession_distance_px)
    track_metrics = _track_metrics(grouped_tracks, frame_durations, fps)
    possession_by_robot = _summarize_possession(possession_samples, frame_durations, total_observed_seconds, "robot_id")
    possession_by_team = _summarize_possession(possession_samples, frame_durations, total_observed_seconds, "team")
    timeline = _possession_timeline(frames, possession_samples, frame_durations, fps)
    metric_rows = _metric_rows(track_metrics, possession_by_robot, possession_by_team)
    possession_seconds = sum(frame_durations.get(frame, 0.0) for frame in possession_samples)

    summary = {
        "observed_frames": len(frames),
        "track_count": len(grouped_tracks),
        "total_observed_seconds": _round(total_observed_seconds),
        "possession_assigned_seconds": _round(possession_seconds),
        "possession_unassigned_seconds": _round(max(0.0, total_observed_seconds - possession_seconds)),
        "possession_threshold_px": _round(possession_distance_px),
    }
    source = {
        "tracks_file": tracks_file,
        "source_experiment": source_experiment,
        "fps": fps,
        "field_width": field_width,
        "field_height": field_height,
    }
    assumptions = [
        "Las metricas temporales usan los frames observados y los saltos de frame derivados del FPS.",
        "La posesion se asigna al robot mas cercano cuando el balon queda dentro del umbral configurado en pixeles.",
        "Distancia y velocidad son estimaciones en pixeles desde desplazamiento de centroides, no metros reales.",
    ]
    limitations = [
        "La perspectiva de camara no esta rectificada; las distancias en pixeles varian con profundidad y angulo.",
        "Oclusiones, detecciones perdidas y cambios de ID pueden fragmentar distancia, velocidad y posesion.",
        "Las etiquetas de equipo quedan como unknown/neutral cuando el detector o tracker exporta clases neutrales.",
    ]
    return Level2Metrics(
        rule_version="level2_metrics_v0.1",
        source=source,
        summary=summary,
        possession_by_robot=possession_by_robot,
        possession_by_team=possession_by_team,
        possession_timeline=timeline,
        track_metrics=track_metrics,
        metric_rows=metric_rows,
        assumptions=assumptions,
        limitations=limitations,
    )


def write_level2_metrics_csv(metrics: Level2Metrics, path: str | Path) -> None:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(MetricRow.__dataclass_fields__.keys())
    with output_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        for row in metrics.metric_rows:
            data = asdict(row)
            data["value"] = f"{row.value:.6f}"
            writer.writerow(data)


def write_level2_metrics_json(metrics: Level2Metrics, path: str | Path) -> None:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as handle:
        json.dump(metrics.to_json_dict(), handle, indent=2)
