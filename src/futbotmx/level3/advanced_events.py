from __future__ import annotations

import csv
import json
import math
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt

from futbotmx.artifact_names import ADVANCED_EVENTS_JSON, HIGHLIGHTS_CSV, SPATIAL_TRACKS_CSV
from futbotmx.level3.schema import write_csv_artifact
from futbotmx.level3.spatial import FieldModel, read_spatial_tracks


RULE_VERSION = "advanced_events_v0.2"
UNKNOWN_TEAMS = {"", "neutral", "unknown", "none"}


@dataclass(frozen=True)
class AdvancedEventsConfig:
    tracks_csv: str = "experiments/test_020_spatial_model/spatial_tracks.csv"
    interaction_metrics_csv: str = "experiments/test_021_tactical_metrics/interaction_metrics.csv"
    interaction_edges_csv: str = "experiments/test_021_tactical_metrics/interaction_edges.csv"
    level2_root: str = "experiments/test_017_level2_closure"
    highlight_top_n: int = 6
    primary_clip: str = "video_595"
    max_pass_gap_frames: int = 12
    highlight_window_frames: int = 2
    ball_speed_reference_norm_per_sec: float = 0.35
    pressure_weight: float = 18.0
    possession_weight: float = 10.0
    critical_zone_weight: float = 12.0
    confidence_weight: float = 20.0


def read_csv_rows(path: str | Path) -> list[dict[str, str]]:
    with Path(path).open("r", newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def read_json(path: str | Path) -> Any:
    with Path(path).open("r", encoding="utf-8") as handle:
        return json.load(handle)


def write_json(path: str | Path, payload: Any) -> None:
    Path(path).write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")


def _is_ball(row: dict[str, Any]) -> bool:
    return str(row.get("class_name", "")) == "ball"


def _is_robot(row: dict[str, Any]) -> bool:
    return "robot" in str(row.get("class_name", ""))


def _known_team(team: str) -> bool:
    return team.lower() not in UNKNOWN_TEAMS


def _time(row: dict[str, Any]) -> float:
    return round(float(row.get("time_sec", 0.0) or 0.0), 3)


def _distance(a: dict[str, Any], b: dict[str, Any]) -> float:
    return math.hypot(float(a["x_norm"]) - float(b["x_norm"]), float(a["y_norm"]) - float(b["y_norm"]))


def _by_clip(rows: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[str(row["clip_id"])].append(row)
    return dict(sorted(grouped.items()))


def _by_clip_frame(rows: list[dict[str, Any]]) -> dict[tuple[str, int], list[dict[str, Any]]]:
    grouped: dict[tuple[str, int], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[(str(row["clip_id"]), int(row["frame"]))].append(row)
    return dict(sorted(grouped.items()))


def ball_speed_segments(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        if _is_ball(row) and str(row.get("calibration_status", "")) == "rectified":
            grouped[(str(row["clip_id"]), str(row["track_id"]))].append(row)

    segments: list[dict[str, Any]] = []
    for (clip_id, ball_id), items in sorted(grouped.items()):
        ordered = sorted(items, key=lambda item: int(item["frame"]))
        for previous, current in zip(ordered, ordered[1:]):
            dt = float(current.get("time_sec", 0.0) or 0.0) - float(previous.get("time_sec", 0.0) or 0.0)
            if dt <= 0:
                continue
            distance = _distance(previous, current)
            confidence = (
                float(previous.get("confidence", 0.0) or 0.0)
                + float(current.get("confidence", 0.0) or 0.0)
                + float(previous.get("calibration_confidence", 0.0) or 0.0)
                + float(current.get("calibration_confidence", 0.0) or 0.0)
            ) / 4
            segments.append(
                {
                    "clip_id": clip_id,
                    "ball_id": ball_id,
                    "frame_start": int(previous["frame"]),
                    "frame_end": int(current["frame"]),
                    "time_start_sec": _time(previous),
                    "time_end_sec": _time(current),
                    "speed_norm_per_sec": distance / dt,
                    "distance_norm": distance,
                    "zone": str(current.get("zone", "unknown")),
                    "position_start": {"x_norm": float(previous["x_norm"]), "y_norm": float(previous["y_norm"])},
                    "position_end": {"x_norm": float(current["x_norm"]), "y_norm": float(current["y_norm"])},
                    "confidence": round(confidence, 6),
                }
            )
    return segments


def possession_segments(interaction_rows: list[dict[str, str]], config: AdvancedEventsConfig) -> list[dict[str, Any]]:
    candidates = [
        row
        for row in interaction_rows
        if row.get("metric_type") == "possession_candidate" and row.get("primary_track_id") and row.get("secondary_track_id")
    ]
    by_clip: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in candidates:
        by_clip[str(row["clip_id"])].append(row)

    segments: list[dict[str, Any]] = []
    for clip_id, rows in sorted(by_clip.items()):
        ordered = sorted(rows, key=lambda item: int(item["frame"]))
        active: dict[str, Any] | None = None

        def flush() -> None:
            nonlocal active
            if active is None:
                return
            frames = active["frames"]
            active["frame_start"] = min(frames)
            active["frame_end"] = max(frames)
            active["frames"] = len(set(frames))
            active["time_start_sec"] = min(active["times"])
            active["time_end_sec"] = max(active["times"])
            active["mean_distance_norm"] = active["distance_sum"] / active["frames"]
            active["confidence"] = active["confidence_sum"] / active["frames"]
            active["reliability"] = "provisional" if active["frames"] >= 3 else "dudoso"
            del active["distance_sum"]
            del active["confidence_sum"]
            del active["times"]
            segments.append(active)
            active = None

        for row in ordered:
            frame = int(row["frame"])
            owner = str(row["primary_track_id"])
            ball_id = str(row["secondary_track_id"])
            if active is None:
                active = _new_possession_segment(clip_id, owner, ball_id, row)
                continue
            gap = frame - max(active["frames"])
            if owner != active["primary_track_id"] or ball_id != active["ball_id"] or gap > config.max_pass_gap_frames:
                flush()
                active = _new_possession_segment(clip_id, owner, ball_id, row)
                continue
            active["frames"].append(frame)
            active["times"].append(float(row.get("time_sec", 0.0) or 0.0))
            active["distance_sum"] += float(row.get("distance_norm", 0.0) or 0.0)
            active["confidence_sum"] += float(row.get("confidence", 0.0) or 0.0)
            active["zones"].append(str(row.get("zone", "unknown")))
        flush()

    for index, segment in enumerate(segments, start=1):
        zones = Counter(segment.pop("zones", []))
        segment["segment_id"] = f"possession_seg_{index:06d}"
        segment["zone"] = zones.most_common(1)[0][0] if zones else "unknown"
    return segments


def load_level2_possession_segments(level2_root: str | Path, clips: list[str]) -> list[dict[str, Any]]:
    segments: list[dict[str, Any]] = []
    root = Path(level2_root)
    for clip_id in clips:
        metrics_path = root / clip_id / "level2_metrics.json"
        if not metrics_path.exists():
            continue
        metrics = read_json(metrics_path)
        for index, item in enumerate(metrics.get("possession_timeline", []) if isinstance(metrics, dict) else [], start=1):
            segments.append(
                {
                    "clip_id": clip_id,
                    "primary_track_id": str(item.get("robot_id", "")),
                    "ball_id": str(item.get("ball_id", "ball_bt_01")),
                    "team": str(item.get("team", "unknown") or "unknown"),
                    "frame_start": int(item.get("frame_start", 0)),
                    "frame_end": int(item.get("frame_end", 0)),
                    "frames": max(1, int(item.get("frame_end", 0)) - int(item.get("frame_start", 0)) + 1),
                    "time_start_sec": float(item.get("time_start_sec", 0.0) or 0.0),
                    "time_end_sec": float(item.get("time_end_sec", 0.0) or 0.0),
                    "mean_distance_norm": "",
                    "confidence": 0.55,
                    "reliability": "provisional",
                    "segment_id": f"level2_possession_{clip_id}_{index:04d}",
                    "zone": "unknown",
                }
            )
    return segments


def _new_possession_segment(clip_id: str, owner: str, ball_id: str, row: dict[str, str]) -> dict[str, Any]:
    return {
        "clip_id": clip_id,
        "primary_track_id": owner,
        "ball_id": ball_id,
        "team": "unknown",
        "frames": [int(row["frame"])],
        "times": [float(row.get("time_sec", 0.0) or 0.0)],
        "distance_sum": float(row.get("distance_norm", 0.0) or 0.0),
        "confidence_sum": float(row.get("confidence", 0.0) or 0.0),
        "zones": [str(row.get("zone", "unknown"))],
    }


def build_pass_chain_events(possessions: list[dict[str, Any]], rows: list[dict[str, Any]], config: AdvancedEventsConfig) -> list[dict[str, Any]]:
    teams_by_track: dict[tuple[str, str], str] = {}
    for row in rows:
        if _is_robot(row):
            teams_by_track[(str(row["clip_id"]), str(row["track_id"]))] = str(row.get("team", "unknown") or "unknown")

    by_clip: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for segment in possessions:
        by_clip[str(segment["clip_id"])].append(segment)

    events: list[dict[str, Any]] = []
    event_index = 1
    for clip_id, clip_segments in sorted(by_clip.items()):
        ordered = sorted(clip_segments, key=lambda item: int(item["frame_start"]))
        chains: list[list[dict[str, Any]]] = []
        active: list[dict[str, Any]] = []
        for previous, current in zip(ordered, ordered[1:]):
            previous_team = teams_by_track.get((clip_id, str(previous["primary_track_id"])), "unknown")
            current_team = teams_by_track.get((clip_id, str(current["primary_track_id"])), "unknown")
            same_team_known = _known_team(previous_team) and previous_team == current_team
            changed_owner = previous["primary_track_id"] != current["primary_track_id"]
            close_gap = int(current["frame_start"]) - int(previous["frame_end"]) <= config.max_pass_gap_frames
            if changed_owner and close_gap and same_team_known:
                if not active:
                    active = [previous]
                active.append(current)
            elif active:
                chains.append(active)
                active = []
        if active:
            chains.append(active)

        if chains:
            for chain in chains:
                chain_team = teams_by_track.get((clip_id, str(chain[0]["primary_track_id"])), "unknown")
                events.append(_pass_chain_event(event_index, clip_id, chain, "same_team_chain", "provisional", chain_team))
                event_index += 1
            continue

        if ordered:
            representative = _longest_segment(ordered)
            team = teams_by_track.get((clip_id, str(representative["primary_track_id"])), "unknown")
            if _known_team(team):
                events.append(_pass_chain_event(event_index, clip_id, [representative], "posesion_con_equipo_sin_cadena", "provisional", team))
            else:
                events.append(_pass_chain_event(event_index, clip_id, [representative], "dudoso_sin_equipo", "dudoso", "unknown"))
            event_index += 1
    return events


def _longest_segment(segments: list[dict[str, Any]]) -> dict[str, Any]:
    return max(segments, key=lambda item: (int(item.get("frames", 0)), float(item.get("confidence", 0.0))))


def _pass_chain_event(index: int, clip_id: str, chain: list[dict[str, Any]], subtype: str, reliability: str, team: str) -> dict[str, Any]:
    start = chain[0]
    end = chain[-1]
    confidence = sum(float(item.get("confidence", 0.0)) for item in chain) / len(chain)
    robot_ids = [str(item["primary_track_id"]) for item in chain]
    if subtype == "same_team_chain":
        narrative = f"Secuencia compatible con cadena de pase candidata para equipo aproximado `{team}`."
    elif subtype == "posesion_con_equipo_sin_cadena":
        narrative = f"Posesion candidata asociada a equipo aproximado `{team}`; no hay cambio de dueno suficiente para declararla pase."
    else:
        narrative = "Secuencia de posesion candidata; falta equipo confiable para declararla pase."
    return {
        "event_id": f"lvl3_evt_{index:06d}",
        "event_type": "pass_chain",
        "event_subtype": subtype,
        "clip_id": clip_id,
        "frame_start": int(start["frame_start"]),
        "frame_end": int(end["frame_end"]),
        "time_start_sec": round(float(start["time_start_sec"]), 3),
        "time_end_sec": round(float(end["time_end_sec"]), 3),
        "team": team if _known_team(team) else "unknown",
        "primary_object_id": robot_ids[0],
        "secondary_object_ids": robot_ids[1:],
        "ball_id": str(start.get("ball_id", "ball_bt_01")),
        "zone": str(start.get("zone", "unknown")),
        "position_start": None,
        "position_end": None,
        "confidence": round(confidence * (0.65 if subtype == "dudoso_sin_equipo" else 1.0), 6),
        "reliability": reliability,
        "highlight_score": 0.0,
        "source_event_ids": [str(item["segment_id"]) for item in chain],
        "interaction_edges": [],
        "spatial_context": {
            "segments": len(chain),
            "robots": robot_ids,
            "reason": _pass_chain_reason(subtype),
        },
        "narrative": narrative,
        "rule_version": RULE_VERSION,
        "evidence": {
            "source": "interaction_metrics.csv",
            "notes": "Pass chain logic is conservative; team labels are approximate when available.",
        },
    }


def _pass_chain_reason(subtype: str) -> str:
    if subtype == "same_team_chain":
        return "same_team_owner_changes"
    if subtype == "posesion_con_equipo_sin_cadena":
        return "known_team_without_owner_change_chain"
    return "no_same_team_change_detected"


def build_highlight_events(
    tracks: list[dict[str, Any]],
    speed_segments: list[dict[str, Any]],
    interaction_rows: list[dict[str, str]],
    edge_rows: list[dict[str, str]],
    level2_events_by_clip: dict[str, list[dict[str, Any]]],
    config: AdvancedEventsConfig,
    start_index: int,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    interaction_index = _interaction_index(interaction_rows)
    edge_index = _edge_index(edge_rows)
    teams_by_track = _teams_by_track(tracks)
    events: list[dict[str, Any]] = []
    highlight_rows: list[dict[str, Any]] = []

    for segment in speed_segments:
        score, reason_parts, confidence, reliability = score_highlight(segment, interaction_index, edge_index, level2_events_by_clip, config)
        primary_track_id, secondary_ids = _highlight_primary_ids(segment, interaction_index)
        team = teams_by_track.get((str(segment["clip_id"]), primary_track_id), "unknown")
        event_id = f"lvl3_evt_{start_index + len(events):06d}"
        narrative = _highlight_narrative(segment, score, reason_parts, reliability, team)
        source_event_ids = _matching_level2_event_ids(segment, level2_events_by_clip)
        event = {
            "event_id": event_id,
            "event_type": "advanced_highlight",
            "event_subtype": "speed_pressure_zone",
            "clip_id": segment["clip_id"],
            "frame_start": int(segment["frame_start"]),
            "frame_end": int(segment["frame_end"]),
            "time_start_sec": segment["time_start_sec"],
            "time_end_sec": segment["time_end_sec"],
            "team": team if _known_team(team) else "unknown",
            "primary_object_id": primary_track_id,
            "secondary_object_ids": secondary_ids,
            "ball_id": segment["ball_id"],
            "zone": segment["zone"],
            "position_start": segment["position_start"],
            "position_end": segment["position_end"],
            "confidence": confidence,
            "reliability": reliability,
            "highlight_score": score,
            "source_event_ids": source_event_ids,
            "interaction_edges": _matching_edges(segment, edge_index),
            "spatial_context": {
                "speed_norm_per_sec": round(float(segment["speed_norm_per_sec"]), 6),
                "distance_norm": round(float(segment["distance_norm"]), 6),
                "reason": reason_parts,
            },
            "narrative": narrative,
            "rule_version": RULE_VERSION,
            "evidence": {
                "source": f"{SPATIAL_TRACKS_CSV}|interaction_metrics.csv|contextual_events.json",
                "notes": "Advanced highlight score uses normalized ball speed, proximity pressure, zone and confidence.",
            },
        }
        events.append(event)

    ranked = sorted(events, key=lambda item: (-float(item["highlight_score"]), str(item["clip_id"]), int(item["frame_start"])))
    for rank, event in enumerate(ranked, start=1):
        highlight_rows.append(
            {
                "clip_id": event["clip_id"],
                "highlight_id": event["event_id"],
                "rank": rank,
                "score": event["highlight_score"],
                "event_type": event["event_type"],
                "frame_start": event["frame_start"],
                "frame_end": event["frame_end"],
                "time_start_sec": event["time_start_sec"],
                "time_end_sec": event["time_end_sec"],
                "primary_track_id": event["primary_object_id"],
                "secondary_track_ids": "|".join(str(item) for item in event["secondary_object_ids"]),
                "zone": event["zone"],
                "confidence": event["confidence"],
                "reliability": event["reliability"],
                "reason": "; ".join(event["spatial_context"]["reason"]),
                "source_event_ids": "|".join(str(item) for item in event["source_event_ids"]),
            }
        )
    return ranked, highlight_rows


def score_highlight(
    segment: dict[str, Any],
    interaction_index: dict[tuple[str, int], list[dict[str, str]]],
    edge_index: dict[str, list[dict[str, str]]],
    level2_events_by_clip: dict[str, list[dict[str, Any]]],
    config: AdvancedEventsConfig,
) -> tuple[float, list[str], float, str]:
    speed_score = min(1.0, float(segment["speed_norm_per_sec"]) / config.ball_speed_reference_norm_per_sec) * 45.0
    reason_parts = [f"velocidad_norm={float(segment['speed_norm_per_sec']):.3f}"]
    frame_keys = _frame_window_keys(str(segment["clip_id"]), int(segment["frame_start"]), int(segment["frame_end"]), config.highlight_window_frames)
    interactions = [row for key in frame_keys for row in interaction_index.get(key, [])]
    types = Counter(row.get("metric_type", "") for row in interactions)
    pressure_score = min(1.0, (types.get("pressure_candidate", 0) + types.get("dispute_cluster", 0)) / 2.0) * config.pressure_weight
    if pressure_score:
        reason_parts.append("presion_o_disputa")
    possession_score = min(1.0, types.get("possession_candidate", 0) / 2.0) * config.possession_weight
    if possession_score:
        reason_parts.append("posesion_candidata")
    zone = str(segment.get("zone", "unknown"))
    zone_score = config.critical_zone_weight if zone in {"defensive_third", "attacking_third"} else config.critical_zone_weight * 0.4
    reason_parts.append(f"zona={zone}")
    level2_bonus = 8.0 if _matching_level2_event_ids(segment, level2_events_by_clip) else 0.0
    if level2_bonus:
        reason_parts.append("respaldo_level2")
    confidence = min(0.99, max(0.05, float(segment["confidence"]) + 0.06 * bool(interactions)))
    confidence_score = confidence * config.confidence_weight
    penalty = 18.0 if confidence < 0.45 else 0.0
    score = max(0.0, speed_score + pressure_score + possession_score + zone_score + level2_bonus + confidence_score - penalty)
    reliability = "provisional" if confidence >= 0.55 and score >= 30 else "dudoso"
    return round(score, 6), reason_parts, round(confidence, 6), reliability


def _interaction_index(rows: list[dict[str, str]]) -> dict[tuple[str, int], list[dict[str, str]]]:
    grouped: dict[tuple[str, int], list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        grouped[(str(row["clip_id"]), int(row["frame"]))].append(row)
    return grouped


def _edge_index(rows: list[dict[str, str]]) -> dict[str, list[dict[str, str]]]:
    grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        grouped[str(row["clip_id"])].append(row)
    return grouped


def _frame_window_keys(clip_id: str, frame_start: int, frame_end: int, radius: int) -> list[tuple[str, int]]:
    return [(clip_id, frame) for frame in range(frame_start - radius, frame_end + radius + 1)]


def _matching_level2_event_ids(segment: dict[str, Any], level2_events_by_clip: dict[str, list[dict[str, Any]]]) -> list[str]:
    result: list[str] = []
    for event in level2_events_by_clip.get(str(segment["clip_id"]), []):
        if int(event.get("frame_start", -1)) <= int(segment["frame_end"]) and int(event.get("frame_end", -1)) >= int(segment["frame_start"]):
            result.append(str(event.get("event_id", "")))
    return [item for item in result if item]


def _matching_edges(segment: dict[str, Any], edge_index: dict[str, list[dict[str, str]]]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    frame_start = int(segment["frame_start"])
    frame_end = int(segment["frame_end"])
    for edge in edge_index.get(str(segment["clip_id"]), []):
        if int(edge.get("frame_start", -1)) <= frame_end and int(edge.get("frame_end", -1)) >= frame_start:
            result.append(
                {
                    "source": edge.get("source", ""),
                    "target": edge.get("target", ""),
                    "edge_type": edge.get("edge_type", ""),
                    "weight": float(edge.get("weight", 0.0) or 0.0),
                }
            )
    return result[:6]


def _highlight_primary_ids(segment: dict[str, Any], interaction_index: dict[tuple[str, int], list[dict[str, str]]]) -> tuple[str, list[str]]:
    frame_key = (str(segment["clip_id"]), int(segment["frame_start"]))
    interactions = interaction_index.get(frame_key, [])
    for row in interactions:
        if row.get("metric_type") == "possession_candidate":
            return str(row.get("primary_track_id", "")), [str(segment["ball_id"])]
    return str(segment["ball_id"]), []


def _highlight_narrative(segment: dict[str, Any], score: float, reason_parts: list[str], reliability: str, team: str = "unknown") -> str:
    team_text = f" para equipo aproximado {team}" if _known_team(team) else ""
    return (
        f"Highlight {reliability}{team_text}: movimiento rapido del balon en frames "
        f"{segment['frame_start']}-{segment['frame_end']} con score {score:.1f}; "
        f"motivos: {', '.join(reason_parts)}."
    )


def _teams_by_track(tracks: list[dict[str, Any]]) -> dict[tuple[str, str], str]:
    result: dict[tuple[str, str], str] = {}
    for row in tracks:
        if _is_robot(row):
            result[(str(row["clip_id"]), str(row["track_id"]))] = str(row.get("team", "unknown") or "unknown")
    return result


def write_level3_events(path: str | Path, events: list[dict[str, Any]]) -> None:
    write_json(path, events)


def write_level3_highlights(path: str | Path, rows: list[dict[str, Any]]) -> None:
    write_csv_artifact(path, HIGHLIGHTS_CSV, rows)


def write_narrative(path: str | Path, events: list[dict[str, Any]], highlight_rows: list[dict[str, Any]], config: AdvancedEventsConfig) -> None:
    top_highlights = sorted(highlight_rows, key=lambda item: int(item["rank"]))[: config.highlight_top_n]
    pass_events = [event for event in events if event["event_type"] == "pass_chain"]
    lines = [
        "# Narrativa de eventos avanzados",
        "",
        f"Clip principal: `{config.primary_clip}`.",
        "",
        "## Resumen",
        "",
        f"- Eventos avanzados generados: `{len(events)}`.",
        f"- Highlights rankeados: `{len(highlight_rows)}`.",
        f"- Cadenas de pase candidatas/dudosas: `{len(pass_events)}`.",
        "",
        "## Highlights",
        "",
    ]
    for row in top_highlights:
        lines.append(
            f"- Rank `{row['rank']}` `{row['clip_id']}` frames `{row['frame_start']}-{row['frame_end']}`: "
            f"score `{row['score']}`, confianza `{row['confidence']}`, motivo: {row['reason']}."
        )
    lines.extend(["", "## Cadenas De Pase", ""])
    for event in pass_events:
        lines.append(
            f"- `{event['clip_id']}` `{event['event_subtype']}` frames `{event['frame_start']}-{event['frame_end']}`: "
            f"{event['narrative']}"
        )
    lines.extend(
        [
            "",
            "## Limitaciones",
            "",
            "- La narrativa usa lenguaje conservador: no afirma goles, faltas, reglas oficiales ni pases confirmados sin equipo confiable.",
            "- Los highlights combinan velocidad normalizada, proximidad, zona y confianza; siguen siendo candidatos para revision humana.",
            "- Las cadenas de pase usan etiquetas de equipo aproximadas cuando existen; si el equipo es `neutral` o `unknown`, quedan marcadas como dudosas.",
        ]
    )
    Path(path).write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_overlay_validation(
    path: str | Path,
    output_dir: Path,
    tracks: list[dict[str, Any]],
    highlight_rows: list[dict[str, Any]],
    max_rows: int = 6,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    lookup = _by_clip_frame(tracks)
    for highlight in sorted(highlight_rows, key=lambda item: int(item["rank"]))[:max_rows]:
        asset_name = f"overlay_highlight_{int(highlight['rank']):02d}_{highlight['clip_id']}_frame_{highlight['frame_start']}.png"
        asset_path = output_dir / asset_name
        draw_highlight_overlay(asset_path, lookup, highlight)
        rows.append(
            {
                "clip_id": highlight["clip_id"],
                "highlight_id": highlight["highlight_id"],
                "rank": highlight["rank"],
                "frame_start": highlight["frame_start"],
                "frame_end": highlight["frame_end"],
                "asset_path": asset_name,
                "confidence": highlight["confidence"],
                "status": "generated",
                "notes": "Minimap validation overlay with IDs, short ball/robot trace and event label.",
            }
        )
    fieldnames = ["clip_id", "highlight_id", "rank", "frame_start", "frame_end", "asset_path", "confidence", "status", "notes"]
    with Path(path).open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    return rows


def draw_highlight_overlay(path: str | Path, lookup: dict[tuple[str, int], list[dict[str, Any]]], highlight: dict[str, Any]) -> None:
    clip_id = str(highlight["clip_id"])
    frame_start = int(highlight["frame_start"])
    frame_end = int(highlight["frame_end"])
    frames = range(max(0, frame_start - 4), frame_end + 5)
    points: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for frame in frames:
        for row in lookup.get((clip_id, frame), []):
            if _is_ball(row) or _is_robot(row):
                points[str(row["track_id"])].append(row)

    fig, ax = plt.subplots(figsize=(5, 6))
    _draw_pitch(ax)
    palette = ["#111111", "#1f77b4", "#d62728", "#2ca02c", "#9467bd", "#ff7f0e"]
    for index, (track_id, items) in enumerate(sorted(points.items())):
        ordered = sorted(items, key=lambda item: int(item["frame"]))
        color = "#111111" if any(_is_ball(item) for item in ordered) else palette[index % len(palette)]
        marker = "o" if color == "#111111" else "."
        xs = [float(item["x_norm"]) for item in ordered]
        ys = [float(item["y_norm"]) for item in ordered]
        ax.plot(xs, ys, color=color, marker=marker, linewidth=1.5, markersize=3)
        ax.text(max(0.02, min(0.92, xs[-1])), max(0.03, min(0.97, ys[-1])), track_id.replace("_bt_", "_"), fontsize=7, color=color)
    ax.set_title(f"{highlight['highlight_id']} rank {highlight['rank']} score {float(highlight['score']):.1f}")
    ax.text(0.02, 1.03, f"{clip_id} frames {frame_start}-{frame_end} conf {float(highlight['confidence']):.2f}", fontsize=8)
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def _draw_pitch(ax: Any) -> None:
    model = FieldModel()
    ax.set_facecolor("#e9ffd8")
    ax.add_patch(plt.Rectangle((0, 0), 1, 1, fill=False, lw=1.6, ec="#00d25b"))
    for y in (1.0 / 3.0, 2.0 / 3.0, 0.5):
        ax.axhline(y, color="#b7f300", lw=0.8, ls="--" if y != 0.5 else "-")
    goal_start = 0.5 - model.goal_width_norm / 2
    goal_end = 0.5 + model.goal_width_norm / 2
    ax.plot([goal_start, goal_end], [0.0, 0.0], color="#b7f300", lw=3)
    ax.plot([goal_start, goal_end], [1.0, 1.0], color="#b7f300", lw=3)
    ax.set_xlim(-0.04, 1.04)
    ax.set_ylim(1.04, -0.08)
    ax.set_xlabel("x_norm")
    ax.set_ylabel("y_norm")
    ax.grid(alpha=0.18)
    ax.set_aspect("equal", adjustable="box")


def load_level2_events(level2_root: str | Path, clips: list[str]) -> dict[str, list[dict[str, Any]]]:
    result: dict[str, list[dict[str, Any]]] = {}
    root = Path(level2_root)
    for clip_id in clips:
        path = root / clip_id / "level2_events.json"
        result[clip_id] = read_json(path) if path.exists() else []
    return result


def build_advanced_events(config: AdvancedEventsConfig) -> dict[str, Any]:
    tracks = read_spatial_tracks(config.tracks_csv)
    interaction_rows = read_csv_rows(config.interaction_metrics_csv)
    edge_rows = read_csv_rows(config.interaction_edges_csv)
    clips = sorted(_by_clip(tracks))
    level2_events = load_level2_events(config.level2_root, clips)
    level2_possessions = load_level2_possession_segments(config.level2_root, clips)
    speeds = ball_speed_segments(tracks)
    fallback_possessions = possession_segments(interaction_rows, config)
    possessions = level2_possessions if level2_possessions else fallback_possessions
    pass_events = build_pass_chain_events(possessions, tracks, config)
    highlight_events, highlight_rows = build_highlight_events(
        tracks,
        speeds,
        interaction_rows,
        edge_rows,
        level2_events,
        config,
        start_index=len(pass_events) + 1,
    )
    events = pass_events + highlight_events
    return {
        "config": config,
        "tracks": tracks,
        "interaction_rows": interaction_rows,
        "edge_rows": edge_rows,
        "level2_events": level2_events,
        "level2_possession_segments": level2_possessions,
        "fallback_possession_segments": fallback_possessions,
        "ball_speed_segments": speeds,
        "possession_segments": possessions,
        "events": events,
        "highlight_rows": highlight_rows,
    }


def config_to_dict(config: AdvancedEventsConfig) -> dict[str, Any]:
    return asdict(config)
