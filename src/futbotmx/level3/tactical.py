from __future__ import annotations

import csv
import json
import math
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from itertools import combinations
from pathlib import Path
from typing import Any

from futbotmx.level3.schema import write_csv_artifact
from futbotmx.level3.spatial import normalized_zone, read_level3_tracks


RULE_VERSION = "level3_tactical_metrics_v0.1"
UNKNOWN_TEAMS = {"", "neutral", "unknown", "none"}


@dataclass(frozen=True)
class TacticalConfig:
    grid_x: int = 24
    grid_y: int = 16
    possession_distance_norm: float = 0.28
    pressure_distance_norm: float = 0.32
    robot_interaction_distance_norm: float = 0.22
    dispute_distance_norm: float = 0.32
    min_track_confidence: float = 0.5
    source_tracks: str = "experiments/test_020_level3_spatial_model/level3_tracks.csv"

    @property
    def grid_cell_count(self) -> int:
        return self.grid_x * self.grid_y


def is_robot(row: dict[str, Any]) -> bool:
    return "robot" in str(row.get("class_name", ""))


def is_ball(row: dict[str, Any]) -> bool:
    return str(row.get("class_name", "")) == "ball"


def has_known_team(row: dict[str, Any]) -> bool:
    return str(row.get("team", "")).lower() not in UNKNOWN_TEAMS


def usable_track(row: dict[str, Any], config: TacticalConfig) -> bool:
    if str(row.get("calibration_status", "")) != "rectified":
        return False
    if str(row.get("track_quality", "")) not in {"usable", "provisional"}:
        return False
    return float(row.get("confidence", 0.0) or 0.0) >= config.min_track_confidence


def euclidean_norm(a: dict[str, Any], b: dict[str, Any]) -> float:
    return math.hypot(float(a["x_norm"]) - float(b["x_norm"]), float(a["y_norm"]) - float(b["y_norm"]))


def grid_cells(config: TacticalConfig) -> list[dict[str, float | str]]:
    cells: list[dict[str, float | str]] = []
    for y_index in range(config.grid_y):
        y_norm = (y_index + 0.5) / config.grid_y
        for x_index in range(config.grid_x):
            x_norm = (x_index + 0.5) / config.grid_x
            cells.append(
                {
                    "x_norm": x_norm,
                    "y_norm": y_norm,
                    "zone": normalized_zone(x_norm, y_norm),
                }
            )
    return cells


def _by_clip_frame(rows: list[dict[str, Any]]) -> dict[tuple[str, int], list[dict[str, Any]]]:
    grouped: dict[tuple[str, int], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[(str(row["clip_id"]), int(row["frame"]))].append(row)
    return dict(sorted(grouped.items()))


def _best_ball(rows: list[dict[str, Any]], config: TacticalConfig) -> dict[str, Any] | None:
    balls = [row for row in rows if is_ball(row) and usable_track(row, config)]
    if not balls:
        return None
    return max(balls, key=lambda item: float(item.get("confidence", 0.0) or 0.0))


def _usable_robots(rows: list[dict[str, Any]], config: TacticalConfig) -> list[dict[str, Any]]:
    return [row for row in rows if is_robot(row) and usable_track(row, config)]


def _confidence(rows: list[dict[str, Any]]) -> float:
    if not rows:
        return 0.0
    values = []
    for row in rows:
        track_confidence = float(row.get("confidence", 0.0) or 0.0)
        calibration_confidence = float(row.get("calibration_confidence", 0.0) or 0.0)
        values.append(track_confidence * calibration_confidence)
    return round(sum(values) / len(values), 6)


def spatial_control_for_frame(
    clip_id: str,
    frame: int,
    rows: list[dict[str, Any]],
    config: TacticalConfig,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    robots = _usable_robots(rows, config)
    if not robots:
        return [], [], {
            "clip_id": clip_id,
            "frame": frame,
            "time_sec": 0.0,
            "robot_count": 0,
            "control_mode": "no_robots",
            "entropy": 0.0,
            "confidence": 0.0,
        }

    cells = grid_cells(config)
    known_team_mode = any(has_known_team(row) for row in robots)
    assignments: list[dict[str, Any]] = []
    by_robot: dict[str, dict[str, Any]] = {}
    for robot in robots:
        by_robot[str(robot["track_id"])] = {
            "track_id": str(robot["track_id"]),
            "class_name": str(robot.get("class_name", "")),
            "team": str(robot.get("team", "unknown") or "unknown"),
            "cell_count": 0,
            "x_sum": 0.0,
            "y_sum": 0.0,
            "zones": Counter(),
            "confidence_sum": 0.0,
        }

    for index, cell in enumerate(cells):
        owner = min(
            robots,
            key=lambda robot: math.hypot(float(robot["x_norm"]) - float(cell["x_norm"]), float(robot["y_norm"]) - float(cell["y_norm"])),
        )
        owner_id = str(owner["track_id"])
        state = by_robot[owner_id]
        state["cell_count"] += 1
        state["x_sum"] += float(cell["x_norm"])
        state["y_sum"] += float(cell["y_norm"])
        state["zones"][str(cell["zone"])] += 1
        state["confidence_sum"] += float(owner.get("confidence", 0.0) or 0.0)
        assignments.append(
            {
                "clip_id": clip_id,
                "frame": frame,
                "cell_id": index,
                "x_norm": round(float(cell["x_norm"]), 6),
                "y_norm": round(float(cell["y_norm"]), 6),
                "zone": cell["zone"],
                "owner_track_id": owner_id,
                "owner_team": owner.get("team", "unknown") or "unknown",
            }
        )

    total_cells = len(cells)
    time_sec = float(robots[0].get("time_sec", 0.0) or 0.0)
    control_mode = "team" if known_team_mode else "track_fallback"
    control_rows: list[dict[str, Any]] = []
    proportions: list[float] = []
    for state in by_robot.values():
        cell_count = int(state["cell_count"])
        if cell_count <= 0:
            continue
        proportion = cell_count / total_cells
        proportions.append(proportion)
        zones: Counter[str] = state["zones"]
        dominant_zone = zones.most_common(1)[0][0] if zones else "unknown"
        control_rows.append(
            {
                "clip_id": clip_id,
                "frame": frame,
                "time_sec": round(time_sec, 3),
                "track_id": state["track_id"],
                "class_name": state["class_name"],
                "team": state["team"],
                "cell_count": cell_count,
                "control_percent": round(100 * proportion, 6),
                "centroid_x_norm": round(float(state["x_sum"]) / cell_count, 6),
                "centroid_y_norm": round(float(state["y_sum"]) / cell_count, 6),
                "zone": dominant_zone,
                "control_mode": control_mode,
                "confidence": round(float(state["confidence_sum"]) / cell_count, 6),
                "notes": "team_assignment_available" if known_team_mode else "fallback_by_individual_robot",
            }
        )

    entropy = 0.0
    if len(proportions) > 1:
        entropy = -sum(p * math.log(p) for p in proportions if p > 0) / math.log(len(proportions))
    summary = {
        "clip_id": clip_id,
        "frame": frame,
        "time_sec": round(time_sec, 3),
        "robot_count": len(robots),
        "control_mode": control_mode,
        "entropy": round(entropy, 6),
        "confidence": _confidence(robots),
    }
    return control_rows, assignments, summary


def compute_spatial_control(
    rows: list[dict[str, Any]],
    config: TacticalConfig,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    control_rows: list[dict[str, Any]] = []
    assignments: list[dict[str, Any]] = []
    summaries: list[dict[str, Any]] = []
    for (clip_id, frame), frame_rows in _by_clip_frame(rows).items():
        frame_control, frame_assignments, summary = spatial_control_for_frame(clip_id, frame, frame_rows, config)
        control_rows.extend(frame_control)
        assignments.extend(frame_assignments)
        if frame_control:
            summaries.append(summary)
    return control_rows, assignments, summaries


def interaction_samples_for_frame(
    clip_id: str,
    frame: int,
    rows: list[dict[str, Any]],
    config: TacticalConfig,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    robots = _usable_robots(rows, config)
    ball = _best_ball(rows, config)
    if not robots or ball is None:
        return [], []

    time_sec = round(float(ball.get("time_sec", 0.0) or 0.0), 3)
    samples: list[dict[str, Any]] = []
    edge_events: list[dict[str, Any]] = []

    robot_distances = [(robot, euclidean_norm(robot, ball)) for robot in robots]
    owner, owner_distance = min(robot_distances, key=lambda item: item[1])
    owner_id = str(owner["track_id"])
    owner_is_candidate = owner_distance <= config.possession_distance_norm

    for robot, distance in robot_distances:
        reliability = "provisional" if distance <= config.pressure_distance_norm else "context"
        metric_type = "possession_candidate" if distance <= config.possession_distance_norm else "robot_ball_distance"
        confidence = _confidence([robot, ball])
        samples.append(
            {
                "clip_id": clip_id,
                "frame": frame,
                "time_sec": time_sec,
                "metric_type": metric_type,
                "primary_track_id": str(robot["track_id"]),
                "secondary_track_id": str(ball["track_id"]),
                "distance_norm": round(distance, 6),
                "zone": ball.get("zone", "unknown"),
                "confidence": confidence,
                "reliability": reliability,
                "notes": "nearest_ball_owner" if str(robot["track_id"]) == owner_id else "robot_to_ball_context",
            }
        )
        if distance <= config.pressure_distance_norm:
            edge_events.append(
                {
                    "clip_id": clip_id,
                    "frame": frame,
                    "time_sec": time_sec,
                    "source": str(robot["track_id"]),
                    "target": str(ball["track_id"]),
                    "edge_type": "possession_candidate" if distance <= config.possession_distance_norm else "ball_proximity",
                    "distance_norm": distance,
                    "confidence": confidence,
                    "reliability": reliability,
                }
            )

    if owner_is_candidate:
        for robot, distance_to_ball in robot_distances:
            robot_id = str(robot["track_id"])
            if robot_id == owner_id:
                continue
            pressure_distance = min(distance_to_ball, euclidean_norm(robot, owner))
            if pressure_distance <= config.pressure_distance_norm:
                confidence = _confidence([robot, owner, ball])
                samples.append(
                    {
                        "clip_id": clip_id,
                        "frame": frame,
                        "time_sec": time_sec,
                        "metric_type": "pressure_candidate",
                        "primary_track_id": robot_id,
                        "secondary_track_id": owner_id,
                        "distance_norm": round(pressure_distance, 6),
                        "zone": ball.get("zone", "unknown"),
                        "confidence": confidence,
                        "reliability": "provisional",
                        "notes": "team labels unknown; pressure is proximity-based",
                    }
                )
                edge_events.append(
                    {
                        "clip_id": clip_id,
                        "frame": frame,
                        "time_sec": time_sec,
                        "source": robot_id,
                        "target": owner_id,
                        "edge_type": "pressure_candidate",
                        "distance_norm": pressure_distance,
                        "confidence": confidence,
                        "reliability": "provisional",
                    }
                )

    for first, second in combinations(robots, 2):
        distance = euclidean_norm(first, second)
        if distance > config.robot_interaction_distance_norm:
            continue
        confidence = _confidence([first, second])
        samples.append(
            {
                "clip_id": clip_id,
                "frame": frame,
                "time_sec": time_sec,
                "metric_type": "robot_proximity",
                "primary_track_id": str(first["track_id"]),
                "secondary_track_id": str(second["track_id"]),
                "distance_norm": round(distance, 6),
                "zone": normalized_zone((float(first["x_norm"]) + float(second["x_norm"])) / 2, (float(first["y_norm"]) + float(second["y_norm"])) / 2),
                "confidence": confidence,
                "reliability": "provisional",
                "notes": "robots closer than normalized proximity threshold",
            }
        )
        edge_events.append(
            {
                "clip_id": clip_id,
                "frame": frame,
                "time_sec": time_sec,
                "source": str(first["track_id"]),
                "target": str(second["track_id"]),
                "edge_type": "robot_proximity",
                "distance_norm": distance,
                "confidence": confidence,
                "reliability": "provisional",
            }
        )

    close_to_ball = [(robot, distance) for robot, distance in robot_distances if distance <= config.dispute_distance_norm]
    if len(close_to_ball) >= 2:
        confidence = _confidence([ball] + [robot for robot, _ in close_to_ball])
        samples.append(
            {
                "clip_id": clip_id,
                "frame": frame,
                "time_sec": time_sec,
                "metric_type": "dispute_cluster",
                "primary_track_id": str(ball["track_id"]),
                "secondary_track_id": "|".join(str(robot["track_id"]) for robot, _ in close_to_ball),
                "distance_norm": round(sum(distance for _, distance in close_to_ball) / len(close_to_ball), 6),
                "zone": ball.get("zone", "unknown"),
                "confidence": confidence,
                "reliability": "provisional",
                "notes": "multiple robots inside ball dispute radius",
            }
        )
        for robot, distance in close_to_ball:
            edge_events.append(
                {
                    "clip_id": clip_id,
                    "frame": frame,
                    "time_sec": time_sec,
                    "source": str(robot["track_id"]),
                    "target": str(ball["track_id"]),
                    "edge_type": "dispute_cluster",
                    "distance_norm": distance,
                    "confidence": confidence,
                    "reliability": "provisional",
                }
            )
    return samples, edge_events


def compute_interactions(
    rows: list[dict[str, Any]],
    config: TacticalConfig,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    samples: list[dict[str, Any]] = []
    edge_events: list[dict[str, Any]] = []
    for (clip_id, frame), frame_rows in _by_clip_frame(rows).items():
        frame_samples, frame_edges = interaction_samples_for_frame(clip_id, frame, frame_rows, config)
        samples.extend(frame_samples)
        edge_events.extend(frame_edges)
    return samples, edge_events


def aggregate_interaction_edges(edge_events: list[dict[str, Any]], fps_by_clip: dict[str, float]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for event in edge_events:
        source = str(event["source"])
        target = str(event["target"])
        if event["edge_type"] in {"robot_proximity", "pressure_candidate"} and source > target:
            source, target = target, source
        grouped[(str(event["clip_id"]), source, target, str(event["edge_type"]))].append(event)

    rows: list[dict[str, Any]] = []
    for (clip_id, source, target, edge_type), events in sorted(grouped.items()):
        frames = sorted({int(event["frame"]) for event in events})
        fps = fps_by_clip.get(clip_id, 0.0)
        duration = len(frames) / fps if fps > 0 else 0.0
        mean_distance = sum(float(event["distance_norm"]) for event in events) / len(events)
        mean_confidence = sum(float(event["confidence"]) for event in events) / len(events)
        weight = mean_confidence * len(frames) / (1.0 + mean_distance)
        rows.append(
            {
                "clip_id": clip_id,
                "source": source,
                "target": target,
                "edge_type": edge_type,
                "frames": len(frames),
                "duration_sec": round(duration, 6),
                "frame_start": min(frames),
                "frame_end": max(frames),
                "mean_distance_norm": round(mean_distance, 6),
                "weight": round(weight, 6),
                "confidence": round(mean_confidence, 6),
                "reliability": "provisional",
                "evidence_frames": "|".join(str(frame) for frame in frames[:12]),
                "notes": "aggregated from normalized proximity samples",
            }
        )
    return rows


def build_interaction_graph(
    rows: list[dict[str, Any]],
    edge_rows: list[dict[str, Any]],
    interaction_samples: list[dict[str, Any]],
) -> dict[str, Any]:
    track_rows: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        if is_robot(row) or is_ball(row):
            track_rows[(str(row["clip_id"]), str(row["track_id"]))].append(row)

    nodes: list[dict[str, Any]] = []
    for (clip_id, track_id), items in sorted(track_rows.items()):
        zones = Counter(str(item.get("zone", "unknown")) for item in items)
        nodes.append(
            {
                "clip_id": clip_id,
                "node_id": track_id,
                "class_name": str(items[0].get("class_name", "")),
                "team": str(items[0].get("team", "unknown") or "unknown"),
                "observations": len(items),
                "frame_start": min(int(item["frame"]) for item in items),
                "frame_end": max(int(item["frame"]) for item in items),
                "dominant_zone": zones.most_common(1)[0][0] if zones else "unknown",
                "mean_confidence": round(sum(float(item.get("confidence", 0.0) or 0.0) for item in items) / len(items), 6),
            }
        )

    return {
        "rule_version": RULE_VERSION,
        "source": {
            "tracks": "level3_tracks.csv",
            "coordinate_system": "normalized_visible_field",
        },
        "summary": {
            "nodes": len(nodes),
            "edges": len(edge_rows),
            "interaction_samples": len(interaction_samples),
        },
        "nodes": nodes,
        "edges": edge_rows,
        "assumptions": [
            "Edges are proximity-based because team identity and physical contact remain provisional.",
            "Weights combine duration, confidence and normalized distance; they are comparative, not official tactical truth.",
        ],
    }


def aggregate_control_by_clip(control_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in control_rows:
        grouped[(str(row["clip_id"]), str(row["track_id"]))].append(row)

    results: list[dict[str, Any]] = []
    for (clip_id, track_id), rows in sorted(grouped.items()):
        values = [float(row["control_percent"]) for row in rows]
        results.append(
            {
                "clip_id": clip_id,
                "track_id": track_id,
                "class_name": str(rows[0]["class_name"]),
                "team": str(rows[0]["team"]),
                "frames": len(rows),
                "mean_control_percent": round(sum(values) / len(values), 6),
                "max_control_percent": round(max(values), 6),
                "dominant_zone": Counter(str(row["zone"]) for row in rows).most_common(1)[0][0],
                "control_mode": str(rows[0]["control_mode"]),
                "confidence": round(sum(float(row["confidence"]) for row in rows) / len(rows), 6),
            }
        )
    return results


def select_voronoi_frames(
    frame_summaries: list[dict[str, Any]],
    interaction_samples: list[dict[str, Any]],
    max_frames_per_clip: int = 4,
) -> list[dict[str, Any]]:
    by_clip: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for summary in frame_summaries:
        by_clip[str(summary["clip_id"])].append(summary)
    interactions_by_frame = Counter((str(row["clip_id"]), int(row["frame"])) for row in interaction_samples if row["metric_type"] != "robot_ball_distance")

    selected: list[dict[str, Any]] = []
    for clip_id, summaries in sorted(by_clip.items()):
        ordered = sorted(summaries, key=lambda item: int(item["frame"]))
        candidates = [ordered[0], ordered[len(ordered) // 2], ordered[-1]]
        if interactions_by_frame:
            best = max(ordered, key=lambda item: (interactions_by_frame[(clip_id, int(item["frame"]))], float(item["entropy"])))
            candidates.append(best)
        seen: set[int] = set()
        for item in candidates:
            frame = int(item["frame"])
            if frame in seen:
                continue
            seen.add(frame)
            selected.append(
                {
                    "clip_id": clip_id,
                    "frame": frame,
                    "time_sec": item["time_sec"],
                    "robot_count": item["robot_count"],
                    "control_mode": item["control_mode"],
                    "entropy": item["entropy"],
                    "interaction_signals": interactions_by_frame[(clip_id, frame)],
                    "selection_reason": "timeline_or_interaction_representative",
                    "confidence": item["confidence"],
                }
            )
            if len(seen) >= max_frames_per_clip:
                break
    return selected


def metric_row(
    clip_id: str,
    category: str,
    entity_type: str,
    entity_id: str,
    class_name: str,
    team: str,
    metric_name: str,
    value: float,
    unit: str,
    frame_start: int | None,
    frame_end: int | None,
    confidence: float,
    source: str,
    notes: str,
) -> dict[str, Any]:
    return {
        "clip_id": clip_id,
        "metric_category": category,
        "entity_type": entity_type,
        "entity_id": entity_id,
        "class_name": class_name,
        "team": team,
        "metric_name": metric_name,
        "value": round(float(value), 6),
        "unit": unit,
        "frame_start": frame_start if frame_start is not None else "",
        "frame_end": frame_end if frame_end is not None else "",
        "confidence": round(float(confidence), 6),
        "source": source,
        "notes": notes,
    }


def build_level3_metric_rows(
    rows: list[dict[str, Any]],
    control_rows: list[dict[str, Any]],
    control_aggregate: list[dict[str, Any]],
    frame_summaries: list[dict[str, Any]],
    interaction_samples: list[dict[str, Any]],
    edge_rows: list[dict[str, Any]],
    config: TacticalConfig,
) -> list[dict[str, Any]]:
    metric_rows: list[dict[str, Any]] = []
    by_clip_frames: dict[str, set[int]] = defaultdict(set)
    by_clip_tracks: dict[str, set[str]] = defaultdict(set)
    for row in rows:
        if is_robot(row) or is_ball(row):
            by_clip_frames[str(row["clip_id"])].add(int(row["frame"]))
            by_clip_tracks[str(row["clip_id"])].add(str(row["track_id"]))

    for clip_id in sorted(by_clip_frames):
        clip_frame_summaries = [row for row in frame_summaries if row["clip_id"] == clip_id]
        mean_entropy = sum(float(row["entropy"]) for row in clip_frame_summaries) / len(clip_frame_summaries) if clip_frame_summaries else 0.0
        confidence = sum(float(row["confidence"]) for row in clip_frame_summaries) / len(clip_frame_summaries) if clip_frame_summaries else 0.0
        frames = sorted(by_clip_frames[clip_id])
        metric_rows.extend(
            [
                metric_row(clip_id, "spatial_control", "clip", clip_id, "clip", "unknown", "frames_analyzed", len(frames), "frames", min(frames), max(frames), confidence, config.source_tracks, "rectified frames with robot or ball tracks"),
                metric_row(clip_id, "spatial_control", "clip", clip_id, "clip", "unknown", "grid_cells", config.grid_cell_count, "cells", min(frames), max(frames), confidence, config.source_tracks, "control grid resolution"),
                metric_row(clip_id, "spatial_control", "clip", clip_id, "clip", "unknown", "mean_control_entropy", mean_entropy, "ratio", min(frames), max(frames), confidence, config.source_tracks, "higher values mean more even robot spatial split"),
                metric_row(clip_id, "interaction", "clip", clip_id, "clip", "unknown", "interaction_samples", len([row for row in interaction_samples if row["clip_id"] == clip_id]), "samples", min(frames), max(frames), confidence, config.source_tracks, "proximity and pressure samples"),
                metric_row(clip_id, "interaction", "clip", clip_id, "clip", "unknown", "graph_edges", len([row for row in edge_rows if row["clip_id"] == clip_id]), "edges", min(frames), max(frames), confidence, config.source_tracks, "aggregated proximity graph edges"),
            ]
        )

    for item in control_aggregate:
        metric_rows.append(
            metric_row(
                item["clip_id"],
                "spatial_control",
                "track",
                item["track_id"],
                item["class_name"],
                item["team"],
                "mean_control_percent",
                float(item["mean_control_percent"]),
                "percent",
                None,
                None,
                float(item["confidence"]),
                config.source_tracks,
                f"{item['control_mode']}; dominant_zone={item['dominant_zone']}",
            )
        )
        metric_rows.append(
            metric_row(
                item["clip_id"],
                "voronoi",
                "track",
                item["track_id"],
                item["class_name"],
                item["team"],
                "mean_voronoi_area_percent",
                float(item["mean_control_percent"]),
                "percent",
                None,
                None,
                float(item["confidence"]),
                config.source_tracks,
                "grid-based Voronoi approximation clipped to normalized field",
            )
        )

    robot_ball_distances: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for sample in interaction_samples:
        if sample["metric_type"] in {"robot_ball_distance", "possession_candidate"}:
            robot_ball_distances[(str(sample["clip_id"]), str(sample["primary_track_id"]))].append(sample)
    for (clip_id, track_id), samples in sorted(robot_ball_distances.items()):
        distances = [float(sample["distance_norm"]) for sample in samples]
        frames = [int(sample["frame"]) for sample in samples]
        confidence = sum(float(sample["confidence"]) for sample in samples) / len(samples)
        metric_rows.append(
            metric_row(
                clip_id,
                "interaction",
                "track",
                track_id,
                "small_robot",
                "unknown",
                "mean_robot_ball_distance_norm",
                sum(distances) / len(distances),
                "normalized_field",
                min(frames),
                max(frames),
                confidence,
                config.source_tracks,
                "distance from robot to best ball track per frame",
            )
        )
    return metric_rows


def write_dict_csv(path: str | Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def write_level3_metrics_csv(path: str | Path, rows: list[dict[str, Any]]) -> None:
    write_csv_artifact(path, "level3_metrics.csv", rows)


def write_level3_metrics_json(
    path: str | Path,
    rows: list[dict[str, Any]],
    config: TacticalConfig,
    control_aggregate: list[dict[str, Any]],
    frame_summaries: list[dict[str, Any]],
    voronoi_frames: list[dict[str, Any]],
    interaction_samples: list[dict[str, Any]],
    edge_rows: list[dict[str, Any]],
) -> None:
    clips = sorted({str(row["clip_id"]) for row in rows})
    interaction_counts = Counter(str(row["metric_type"]) for row in interaction_samples)
    payload = {
        "rule_version": RULE_VERSION,
        "source": {
            "tracks": config.source_tracks,
            "coordinate_system": "normalized_visible_field",
            "grid": {"x": config.grid_x, "y": config.grid_y, "cells": config.grid_cell_count},
        },
        "summary": {
            "clips_analyzed": len(clips),
            "frames_analyzed": len(frame_summaries),
            "metrics_exported": len(rows),
            "control_tracks": len(control_aggregate),
            "interaction_samples": len(interaction_samples),
            "interaction_edges": len(edge_rows),
        },
        "spatial_control": {
            "aggregate_by_track": control_aggregate,
            "frame_summary_sample": frame_summaries[:12],
            "voronoi_representative_frames": voronoi_frames,
        },
        "interactions": {
            "counts_by_type": dict(sorted(interaction_counts.items())),
            "top_edges": sorted(edge_rows, key=lambda item: float(item["weight"]), reverse=True)[:12],
        },
        "pass_chains": {
            "status": "not_computed_in_activity_3",
            "next_stage": "Actividad 4 reutilizara posesion/interacciones.",
        },
        "highlights": {
            "status": "not_ranked_in_activity_3",
            "next_stage": "Actividad 4 combinara velocidad, presion y zona.",
        },
        "assumptions": [
            "Spatial control uses nearest-robot assignment over a normalized grid.",
            "Voronoi is approximated by the same clipped grid cells, avoiding heavy geometry dependencies.",
            "Teams are neutral/unknown in current tracks, so control falls back to individual robot ownership.",
        ],
        "limitations": [
            "Homography remains approximate and inherited from Activity 2.",
            "Pressure and possession are proximity candidates, not physical contact or official possession.",
            "Graph edge weights are comparative within this demo and should not be read as official tactical metrics.",
        ],
    }
    Path(path).write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")


def write_interaction_metrics(path: str | Path, rows: list[dict[str, Any]]) -> None:
    fieldnames = [
        "clip_id",
        "frame",
        "time_sec",
        "metric_type",
        "primary_track_id",
        "secondary_track_id",
        "distance_norm",
        "zone",
        "confidence",
        "reliability",
        "notes",
    ]
    write_dict_csv(path, rows, fieldnames)


def write_interaction_edges(path: str | Path, rows: list[dict[str, Any]]) -> None:
    fieldnames = [
        "clip_id",
        "source",
        "target",
        "edge_type",
        "frames",
        "duration_sec",
        "frame_start",
        "frame_end",
        "mean_distance_norm",
        "weight",
        "confidence",
        "reliability",
        "evidence_frames",
        "notes",
    ]
    write_dict_csv(path, rows, fieldnames)


def write_spatial_control_csv(path: str | Path, rows: list[dict[str, Any]]) -> None:
    fieldnames = [
        "clip_id",
        "frame",
        "time_sec",
        "track_id",
        "class_name",
        "team",
        "cell_count",
        "control_percent",
        "centroid_x_norm",
        "centroid_y_norm",
        "zone",
        "control_mode",
        "confidence",
        "notes",
    ]
    write_dict_csv(path, rows, fieldnames)


def write_voronoi_frames_csv(path: str | Path, rows: list[dict[str, Any]]) -> None:
    fieldnames = [
        "clip_id",
        "frame",
        "time_sec",
        "robot_count",
        "control_mode",
        "entropy",
        "interaction_signals",
        "selection_reason",
        "confidence",
    ]
    write_dict_csv(path, rows, fieldnames)


def compute_tactical_outputs(
    tracks_csv: str | Path,
    config: TacticalConfig | None = None,
) -> dict[str, Any]:
    tactical_config = config or TacticalConfig(source_tracks=str(tracks_csv))
    rows = read_level3_tracks(tracks_csv)
    fps_by_clip = _fps_by_clip(rows)
    control_rows, _, frame_summaries = compute_spatial_control(rows, tactical_config)
    control_aggregate = aggregate_control_by_clip(control_rows)
    interaction_samples, edge_events = compute_interactions(rows, tactical_config)
    edge_rows = aggregate_interaction_edges(edge_events, fps_by_clip)
    graph = build_interaction_graph(rows, edge_rows, interaction_samples)
    voronoi_frames = select_voronoi_frames(frame_summaries, interaction_samples)
    metric_rows = build_level3_metric_rows(
        rows,
        control_rows,
        control_aggregate,
        frame_summaries,
        interaction_samples,
        edge_rows,
        tactical_config,
    )
    return {
        "config": tactical_config,
        "tracks": rows,
        "control_rows": control_rows,
        "control_aggregate": control_aggregate,
        "frame_summaries": frame_summaries,
        "voronoi_frames": voronoi_frames,
        "interaction_samples": interaction_samples,
        "edge_rows": edge_rows,
        "graph": graph,
        "metric_rows": metric_rows,
    }


def _fps_by_clip(rows: list[dict[str, Any]]) -> dict[str, float]:
    by_clip: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_clip[str(row["clip_id"])].append(row)
    result: dict[str, float] = {}
    for clip_id, items in by_clip.items():
        ordered = sorted(items, key=lambda item: (int(item["frame"]), float(item.get("time_sec", 0.0) or 0.0)))
        frame_times: dict[int, float] = {}
        for item in ordered:
            frame_times.setdefault(int(item["frame"]), float(item.get("time_sec", 0.0) or 0.0))
        frames = sorted(frame_times)
        fps_values: list[float] = []
        for previous, current in zip(frames, frames[1:]):
            dt = frame_times[current] - frame_times[previous]
            if dt > 0 and current > previous:
                fps_values.append((current - previous) / dt)
        result[clip_id] = sum(fps_values) / len(fps_values) if fps_values else 0.0
    return result


def config_to_dict(config: TacticalConfig) -> dict[str, Any]:
    return asdict(config)
