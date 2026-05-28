from __future__ import annotations

import csv
import json
import math
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


def _read_tracks(path: str | Path) -> list[dict[str, Any]]:
    with Path(path).open("r", newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    for row in rows:
        for key in ("frame", "x", "y", "bbox_x1", "bbox_y1", "bbox_x2", "bbox_y2", "confidence"):
            if key in row and row[key] != "":
                row[key] = float(row[key])
        row["frame"] = int(row["frame"])
    return rows


def _distance(a: dict[str, Any], b: dict[str, Any]) -> float:
    return math.hypot(float(a["x"]) - float(b["x"]), float(a["y"]) - float(b["y"]))


def _bbox_overlap(a: dict[str, Any], b: dict[str, Any]) -> bool:
    return not (
        float(a["bbox_x2"]) < float(b["bbox_x1"])
        or float(b["bbox_x2"]) < float(a["bbox_x1"])
        or float(a["bbox_y2"]) < float(b["bbox_y1"])
        or float(b["bbox_y2"]) < float(a["bbox_y1"])
    )


def _event(
    index: int,
    event_type: str,
    frame_start: int,
    frame_end: int,
    fps: float,
    rule_version: str,
    source_experiment: str,
    **extra: Any,
) -> dict[str, Any]:
    return {
        "event_id": f"evt_{index:06d}",
        "event_type": event_type,
        "frame_start": frame_start,
        "frame_end": frame_end,
        "time_start_sec": round(frame_start / fps, 3) if fps > 0 else 0.0,
        "time_end_sec": round(frame_end / fps, 3) if fps > 0 else 0.0,
        "team": extra.pop("team", "unknown"),
        "primary_object_id": extra.pop("primary_object_id", None),
        "secondary_object_id": extra.pop("secondary_object_id", None),
        "ball_id": extra.pop("ball_id", "ball_01"),
        "zone": extra.pop("zone", "unknown"),
        "position_start": extra.pop("position_start", None),
        "position_end": extra.pop("position_end", None),
        "confidence": round(float(extra.pop("confidence", 0.5)), 3),
        "rule_version": rule_version,
        "evidence": {
            "source_experiment": source_experiment,
            "tracks_file": "tracks.csv",
            "config_file": "config.yaml",
            "notes": extra.pop("notes", ""),
        },
    }


def detect_level1_events(
    tracks_csv: str | Path,
    fps: float,
    field_width: float,
    field_height: float,
    config: dict[str, Any],
    source_experiment: str = "experiments/test_004_events",
) -> list[dict[str, Any]]:
    rows = _read_tracks(tracks_csv)
    by_frame: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_frame[int(row["frame"])].append(row)

    events: list[dict[str, Any]] = []
    rule_version = config.get("rule_version", "events_v0.1")
    possession_distance = float(config.get("possession_distance_px", 45))
    possession_min_frames = int(config.get("possession_min_frames", 8))
    collision_distance = float(config.get("collision_distance_px", 35))
    collision_min_frames = int(config.get("collision_min_frames", 4))
    shot_speed = float(config.get("shot_min_ball_speed_px_per_sec", 180))

    possession_runs: list[tuple[int, int, dict[str, Any], dict[str, Any]]] = []
    current_owner: tuple[str, str] | None = None
    current_start = 0
    current_ball: dict[str, Any] | None = None
    current_robot: dict[str, Any] | None = None

    for frame in sorted(by_frame):
        frame_rows = by_frame[frame]
        balls = [row for row in frame_rows if row["class_name"] == "ball"]
        robots = [row for row in frame_rows if "robot" in row["class_name"]]
        owner = None
        ball = balls[0] if balls else None
        robot = None
        if ball and robots:
            robot = min(robots, key=lambda item: _distance(ball, item))
            if _distance(ball, robot) <= possession_distance:
                owner = (robot["track_id"], robot.get("team", "unknown"))

        if owner != current_owner:
            if current_owner and current_robot and current_ball:
                if frame - current_start >= possession_min_frames:
                    possession_runs.append((current_start, frame - 1, current_robot, current_ball))
            current_owner = owner
            current_start = frame
            current_robot = robot
            current_ball = ball

    if current_owner and current_robot and current_ball:
        last_frame = max(by_frame)
        if last_frame - current_start + 1 >= possession_min_frames:
            possession_runs.append((current_start, last_frame, current_robot, current_ball))

    for start, end, robot, ball in possession_runs:
        events.append(
            _event(
                len(events) + 1,
                "possession",
                start,
                end,
                fps,
                rule_version,
                source_experiment,
                team=robot.get("team", "unknown"),
                primary_object_id=robot["track_id"],
                ball_id=ball["track_id"],
                position_start={"x": float(ball["x"]), "y": float(ball["y"])},
                position_end={"x": float(ball["x"]), "y": float(ball["y"])},
                confidence=0.65,
                notes="Ball stayed within possession distance of robot.",
            )
        )

    for previous, current in zip(possession_runs, possession_runs[1:]):
        _, previous_end, previous_robot, previous_ball = previous
        current_start, current_end, current_robot, current_ball = current
        if previous_robot.get("team") == current_robot.get("team") and previous_robot["track_id"] != current_robot["track_id"]:
            events.append(
                _event(
                    len(events) + 1,
                    "pass",
                    previous_end,
                    current_start,
                    fps,
                    rule_version,
                    source_experiment,
                    team=current_robot.get("team", "unknown"),
                    primary_object_id=previous_robot["track_id"],
                    secondary_object_id=current_robot["track_id"],
                    ball_id=current_ball["track_id"],
                    position_start={"x": float(previous_ball["x"]), "y": float(previous_ball["y"])},
                    position_end={"x": float(current_ball["x"]), "y": float(current_ball["y"])},
                    confidence=0.55,
                    notes="Possession changed between robots of the same team.",
                )
            )

    ball_rows = sorted([row for row in rows if row["class_name"] == "ball"], key=lambda item: item["frame"])
    for a, b in zip(ball_rows, ball_rows[1:]):
        dt = max((int(b["frame"]) - int(a["frame"])) / fps, 1 / fps) if fps > 0 else 1.0
        speed = _distance(a, b) / dt
        moving_toward_goal = float(b["x"]) > float(a["x"]) and float(b["x"]) > field_width * 0.75
        if speed >= shot_speed and moving_toward_goal:
            events.append(
                _event(
                    len(events) + 1,
                    "shot",
                    int(a["frame"]),
                    int(b["frame"]),
                    fps,
                    rule_version,
                    source_experiment,
                    team="unknown",
                    primary_object_id=None,
                    ball_id=b["track_id"],
                    zone="attacking_third",
                    position_start={"x": float(a["x"]), "y": float(a["y"])},
                    position_end={"x": float(b["x"]), "y": float(b["y"])},
                    confidence=0.5,
                    notes="Ball speed exceeded threshold while moving toward goal area.",
                )
            )
            break

    collision_runs: Counter[tuple[str, str]] = Counter()
    collision_start: dict[tuple[str, str], int] = {}
    for frame in sorted(by_frame):
        robots = [row for row in by_frame[frame] if "robot" in row["class_name"]]
        active_pairs: set[tuple[str, str]] = set()
        for index, a in enumerate(robots):
            for b in robots[index + 1 :]:
                pair = tuple(sorted((a["track_id"], b["track_id"])))
                if _distance(a, b) <= collision_distance or _bbox_overlap(a, b):
                    active_pairs.add(pair)
                    collision_runs[pair] += 1
                    collision_start.setdefault(pair, frame)
        for pair in list(collision_runs):
            if pair not in active_pairs and collision_runs[pair] >= collision_min_frames:
                events.append(
                    _event(
                        len(events) + 1,
                        "collision",
                        collision_start[pair],
                        frame - 1,
                        fps,
                        rule_version,
                        source_experiment,
                        primary_object_id=pair[0],
                        secondary_object_id=pair[1],
                        confidence=0.5,
                        notes="Robots remained close or overlapping for minimum duration.",
                    )
                )
                collision_runs[pair] = 0

    last_frame = max(by_frame) if by_frame else 0
    for pair, count in collision_runs.items():
        if count >= collision_min_frames:
            events.append(
                _event(
                    len(events) + 1,
                    "collision",
                    collision_start[pair],
                    last_frame,
                    fps,
                    rule_version,
                    source_experiment,
                    primary_object_id=pair[0],
                    secondary_object_id=pair[1],
                    confidence=0.5,
                    notes="Robots remained close or overlapping for minimum duration.",
                )
            )

    zone_counts: Counter[str] = Counter()
    for row in rows:
        if row["class_name"] == "ball":
            if float(row["x"]) < field_width / 3:
                zone = "defensive_third"
            elif float(row["x"]) < 2 * field_width / 3:
                zone = "middle_third"
            else:
                zone = "attacking_third"
            zone_counts[zone] += 1
    if zone_counts:
        zone, count = zone_counts.most_common(1)[0]
        events.append(
            _event(
                len(events) + 1,
                "activity_zone",
                min(by_frame),
                max(by_frame),
                fps,
                rule_version,
                source_experiment,
                zone=zone,
                confidence=min(0.9, count / max(1, len(ball_rows))),
                notes="Dominant ball activity zone from tracked positions.",
            )
        )

    return events


def write_events_json(events: list[dict[str, Any]], path: str | Path) -> None:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as handle:
        json.dump(events, handle, indent=2)
