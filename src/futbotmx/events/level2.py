from __future__ import annotations

import csv
import json
import math
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from futbotmx.tracking import read_tracks_csv


@dataclass(frozen=True)
class PossessionRun:
    robot_id: str
    team: str
    ball_id: str
    frame_start: int
    frame_end: int
    frames: int
    mean_distance_px: float
    position_start: dict[str, float]
    position_end: dict[str, float]


def _distance(a: dict[str, Any], b: dict[str, Any]) -> float:
    return math.hypot(float(a["x"]) - float(b["x"]), float(a["y"]) - float(b["y"]))


def _zone(row: dict[str, Any], field_width: float, field_height: float, zone_axis: str = "x") -> str:
    axis = "y" if zone_axis == "y" else "x"
    span = field_height if axis == "y" else field_width
    position = float(row[axis])
    if position < span / 3:
        return "defensive_third"
    if position < 2 * span / 3:
        return "middle_third"
    return "attacking_third"


def _time(frame: int, fps: float) -> float:
    return round(frame / fps, 3) if fps > 0 else 0.0


def _event(
    index: int,
    event_type: str,
    frame_start: int,
    frame_end: int,
    fps: float,
    rule_version: str,
    source_experiment: str,
    tracks_file: str,
    reliability: str,
    confidence: float,
    **extra: Any,
) -> dict[str, Any]:
    return {
        "event_id": f"lvl2_evt_{index:06d}",
        "event_type": event_type,
        "frame_start": frame_start,
        "frame_end": frame_end,
        "time_start_sec": _time(frame_start, fps),
        "time_end_sec": _time(frame_end, fps),
        "team": extra.pop("team", "unknown"),
        "primary_object_id": extra.pop("primary_object_id", None),
        "secondary_object_id": extra.pop("secondary_object_id", None),
        "ball_id": extra.pop("ball_id", "ball_01"),
        "zone": extra.pop("zone", "unknown"),
        "position_start": extra.pop("position_start", None),
        "position_end": extra.pop("position_end", None),
        "confidence": round(float(confidence), 3),
        "reliability": reliability,
        "rule_version": rule_version,
        "evidence": {
            "source_experiment": source_experiment,
            "tracks_file": tracks_file,
            "config_file": "config.yaml",
            "notes": extra.pop("notes", ""),
            "signals": extra,
        },
    }


def _by_frame(rows: list[dict[str, Any]]) -> dict[int, list[dict[str, Any]]]:
    grouped: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[int(row["frame"])].append(row)
    return grouped


def _best_ball(rows: list[dict[str, Any]]) -> dict[str, Any] | None:
    balls = [row for row in rows if row["class_name"] == "ball"]
    if not balls:
        return None
    return max(balls, key=lambda item: float(item.get("confidence", 0.0)))


def _robots(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [row for row in rows if "robot" in str(row["class_name"])]


def _possession_samples(
    rows: list[dict[str, Any]],
    possession_distance_px: float,
    field_width: float,
    field_height: float,
    zone_axis: str,
) -> dict[int, dict[str, Any]]:
    samples: dict[int, dict[str, Any]] = {}
    for frame, frame_rows in sorted(_by_frame(rows).items()):
        ball = _best_ball(frame_rows)
        robots = _robots(frame_rows)
        if ball is None or not robots:
            continue
        robot = min(robots, key=lambda item: _distance(ball, item))
        distance_px = _distance(ball, robot)
        if distance_px <= possession_distance_px:
            samples[frame] = {
                "frame": frame,
                "robot_id": robot["track_id"],
                "team": robot.get("team", "unknown") or "unknown",
                "ball_id": ball["track_id"],
                "distance_px": distance_px,
                "ball": ball,
                "zone": _zone(ball, field_width, field_height, zone_axis),
            }
    return samples


def _build_possession_runs(
    rows: list[dict[str, Any]],
    possession_distance_px: float,
    field_width: float,
    field_height: float,
    zone_axis: str,
) -> list[PossessionRun]:
    samples = _possession_samples(rows, possession_distance_px, field_width, field_height, zone_axis)
    all_frames = sorted({int(row["frame"]) for row in rows})
    runs: list[PossessionRun] = []
    active: dict[str, Any] | None = None
    distance_sum = 0.0
    frames = 0
    start_ball: dict[str, Any] | None = None
    end_ball: dict[str, Any] | None = None

    def flush() -> None:
        nonlocal active, distance_sum, frames, start_ball, end_ball
        if active is None or start_ball is None or end_ball is None or frames == 0:
            return
        runs.append(
            PossessionRun(
                robot_id=active["robot_id"],
                team=active["team"],
                ball_id=active["ball_id"],
                frame_start=active["frame_start"],
                frame_end=active["frame_end"],
                frames=frames,
                mean_distance_px=distance_sum / frames,
                position_start={"x": float(start_ball["x"]), "y": float(start_ball["y"])},
                position_end={"x": float(end_ball["x"]), "y": float(end_ball["y"])},
            )
        )
        active = None
        distance_sum = 0.0
        frames = 0
        start_ball = None
        end_ball = None

    for frame in all_frames:
        sample = samples.get(frame)
        owner = (sample["robot_id"], sample["team"]) if sample else None
        active_owner = (active["robot_id"], active["team"]) if active else None
        if owner is None:
            flush()
            continue
        if active is None or owner != active_owner:
            flush()
            active = dict(sample)
            active["frame_start"] = frame
            active["frame_end"] = frame
            distance_sum = float(sample["distance_px"])
            frames = 1
            start_ball = sample["ball"]
            end_ball = sample["ball"]
            continue
        active["frame_end"] = frame
        distance_sum += float(sample["distance_px"])
        frames += 1
        end_ball = sample["ball"]
    flush()
    return runs


def _ball_speeds(rows: list[dict[str, Any]], fps: float, field_width: float, field_height: float, zone_axis: str) -> list[dict[str, Any]]:
    by_track: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        if row["class_name"] == "ball":
            by_track[str(row["track_id"])].append(row)

    speeds: list[dict[str, Any]] = []
    for track_id, balls in sorted(by_track.items()):
        ordered = sorted(balls, key=lambda item: item["frame"])
        for previous, current in zip(ordered, ordered[1:]):
            frame_delta = max(1, int(current["frame"]) - int(previous["frame"]))
            dt = frame_delta / fps if fps > 0 else 1.0
            speed = _distance(previous, current) / dt if dt > 0 else 0.0
            speeds.append(
                {
                    "frame_start": int(previous["frame"]),
                    "frame_end": int(current["frame"]),
                    "speed_px_per_sec": speed,
                    "zone": _zone(current, field_width, field_height, zone_axis),
                    "position_start": {"x": float(previous["x"]), "y": float(previous["y"])},
                    "position_end": {"x": float(current["x"]), "y": float(current["y"])},
                    "ball_id": track_id,
                    "is_discontinuous": False,
                }
            )
    return speeds


def _run_reliability(run: PossessionRun, min_frames: int, possession_distance_px: float) -> tuple[str, float]:
    if run.frames < min_frames:
        return "descartado", 0.15
    if run.frames >= min_frames * 2 and run.mean_distance_px <= possession_distance_px * 0.8:
        return "confiable", 0.78
    return "provisional", 0.58


def detect_level2_events(
    tracks_csv: str | Path,
    fps: float,
    field_width: float,
    field_height: float,
    config: dict[str, Any],
    source_experiment: str = "experiments/test_013_level2_events",
) -> list[dict[str, Any]]:
    rows = read_tracks_csv(tracks_csv)
    tracks_file = str(tracks_csv)
    if not rows:
        return []

    rule_version = config.get("rule_version", "level2_events_v0.1")
    possession_distance = float(config.get("possession_distance_px", 190))
    recovery_min_frames = int(config.get("recovery_min_frames", 5))
    interception_max_gap = int(config.get("interception_max_gap_frames", 12))
    interception_min_speed = float(config.get("interception_min_speed_px_per_sec", 120))
    highlight_min_speed = float(config.get("highlight_min_speed_px_per_sec", 250))
    zone_axis = str(config.get("zone_axis", "x"))

    events: list[dict[str, Any]] = []
    runs = _build_possession_runs(rows, possession_distance, field_width, field_height, zone_axis)
    speeds = _ball_speeds(rows, fps, field_width, field_height, zone_axis)
    max_speed = max(speeds, key=lambda item: item["speed_px_per_sec"]) if speeds else None

    for run in runs:
        reliability, confidence = _run_reliability(run, recovery_min_frames, possession_distance)
        events.append(
            _event(
                len(events) + 1,
                "ball_recovery",
                run.frame_start,
                run.frame_end,
                fps,
                rule_version,
                source_experiment,
                tracks_file,
                reliability,
                confidence,
                team=run.team,
                primary_object_id=run.robot_id,
                ball_id=run.ball_id,
                position_start=run.position_start,
                position_end=run.position_end,
                notes="Robot recovered or re-established ball proximity after a free/unknown possession segment.",
                frames=run.frames,
                min_frames=recovery_min_frames,
                mean_distance_px=round(run.mean_distance_px, 3),
            )
        )

    interception_count = 0
    for previous, current in zip(runs, runs[1:]):
        if previous.robot_id == current.robot_id:
            continue
        gap = current.frame_start - previous.frame_end
        speed_candidates = [
            item
            for item in speeds
            if previous.frame_end <= item["frame_start"] and item["frame_end"] <= current.frame_start
            and item["ball_id"] in {previous.ball_id, current.ball_id}
        ]
        best_speed = max(speed_candidates, key=lambda item: item["speed_px_per_sec"]) if speed_candidates else None
        speed_value = float(best_speed["speed_px_per_sec"]) if best_speed else 0.0
        same_team = previous.team == current.team and previous.team not in ("unknown", "neutral")
        reliability = "provisional"
        confidence = 0.6
        notes = "Ball changed possession between robots inside the interception gap."
        if gap > interception_max_gap or speed_value < interception_min_speed or same_team:
            reliability = "descartado"
            confidence = 0.18
            notes = "Candidate rejected by gap, speed or same-team rule."
        events.append(
            _event(
                len(events) + 1,
                "interception",
                previous.frame_end,
                current.frame_start,
                fps,
                rule_version,
                source_experiment,
                tracks_file,
                reliability,
                confidence,
                team=current.team,
                primary_object_id=previous.robot_id,
                secondary_object_id=current.robot_id,
                ball_id=current.ball_id,
                position_start=previous.position_end,
                position_end=current.position_start,
                notes=notes,
                gap_frames=gap,
                max_gap_frames=interception_max_gap,
                speed_px_per_sec=round(speed_value, 3),
                min_speed_px_per_sec=interception_min_speed,
            )
        )
        if reliability != "descartado":
            interception_count += 1

    if interception_count == 0:
        first_frame = min(int(row["frame"]) for row in rows)
        last_frame = max(int(row["frame"]) for row in rows)
        events.append(
            _event(
                len(events) + 1,
                "interception",
                first_frame,
                last_frame,
                fps,
                rule_version,
                source_experiment,
                tracks_file,
                "descartado",
                0.05,
                notes="No possession change between different robots satisfied interception criteria.",
                possession_runs=len(runs),
                max_gap_frames=interception_max_gap,
                min_speed_px_per_sec=interception_min_speed,
            )
        )

    if max_speed and float(max_speed["speed_px_per_sec"]) >= highlight_min_speed:
        reliability = "provisional"
        confidence = min(0.82, 0.45 + float(max_speed["speed_px_per_sec"]) / max(highlight_min_speed, 1) * 0.18)
        notes = "Ball speed and field zone produced a highlight candidate."
    else:
        reliability = "descartado"
        confidence = 0.1
        notes = "No speed or possession-change signal reached highlight threshold."
    highlight_start = int(max_speed["frame_start"]) if max_speed else min(int(row["frame"]) for row in rows)
    highlight_end = int(max_speed["frame_end"]) if max_speed else max(int(row["frame"]) for row in rows)
    events.append(
        _event(
            len(events) + 1,
            "highlight_play",
            highlight_start,
            highlight_end,
            fps,
            rule_version,
            source_experiment,
            tracks_file,
            reliability,
            confidence,
            ball_id=max_speed["ball_id"] if max_speed else "ball_01",
            zone=max_speed["zone"] if max_speed else "unknown",
            position_start=max_speed["position_start"] if max_speed else None,
            position_end=max_speed["position_end"] if max_speed else None,
            notes=notes,
            speed_px_per_sec=round(float(max_speed["speed_px_per_sec"]), 3) if max_speed else 0.0,
            min_speed_px_per_sec=highlight_min_speed,
            ball_track_continuity="same_track" if max_speed else "unavailable",
            zone_axis=zone_axis,
        )
    )
    return events


def write_level2_events_json(events: list[dict[str, Any]], path: str | Path) -> None:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as handle:
        json.dump(events, handle, indent=2)


def write_level2_event_metrics(events: list[dict[str, Any]], path: str | Path) -> None:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    counts = Counter((event["event_type"], event["reliability"]) for event in events)
    with output_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["event_type", "reliability", "count"], lineterminator="\n")
        writer.writeheader()
        for (event_type, reliability), count in sorted(counts.items()):
            writer.writerow({"event_type": event_type, "reliability": reliability, "count": count})
