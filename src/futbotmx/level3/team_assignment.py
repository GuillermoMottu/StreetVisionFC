from __future__ import annotations

import csv
import json
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path
from statistics import median
from typing import Any

from futbotmx.artifact_names import (
    LEGACY_TEAM_TRACKS_CSV,
    SPATIAL_TRACKS_CSV,
    TEAM_TRACKS_CSV,
    mirror_legacy_file,
)
from futbotmx.level3.schema import write_csv_artifact
from futbotmx.level3.spatial import read_spatial_tracks


RULE_VERSION = "team_assignment_v0.1"
UNKNOWN_TEAMS = {"", "neutral", "unknown", "none"}
TEAM_ASSIGNMENT_FIELDS = [
    "clip_id",
    "track_id",
    "class_name",
    "team",
    "confidence",
    "source",
    "frame_start",
    "frame_end",
    "frames",
    "median_x_norm",
    "median_y_norm",
    "dominant_zone",
    "notes",
]
STRATEGY_FIELDS = ["strategy", "status", "confidence", "source", "notes"]
VALIDATION_FIELDS = ["clip_id", "track_id", "status", "source", "notes"]
MANIFEST_FIELDS = ["asset_id", "asset_type", "path", "source_artifact", "is_versioned", "role", "notes"]


@dataclass(frozen=True)
class TeamAssignmentConfig:
    tracks_csv: str = "experiments/test_020_spatial_model/spatial_tracks.csv"
    manual_assignment_csv: str = ""
    output_dir: str = "experiments/test_031_team_assignment"
    fallback_split_axis: str = "x_norm"
    fallback_left_team: str = "team_left"
    fallback_right_team: str = "team_right"
    initial_window_frames: int = 8
    min_side_spread_norm: float = 0.12


def is_robot(row: dict[str, Any]) -> bool:
    return "robot" in str(row.get("class_name", ""))


def known_team(team: str) -> bool:
    return str(team).lower() not in UNKNOWN_TEAMS


def build_team_assignment_package(config: TeamAssignmentConfig) -> dict[str, Any]:
    output_dir = Path(config.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    tracks = read_spatial_tracks(config.tracks_csv)
    manual_rows = read_manual_assignments(config.manual_assignment_csv) if config.manual_assignment_csv else []
    summaries = robot_track_summaries(tracks, config)
    assignments, validation_rows = build_team_assignments(summaries, manual_rows, config)
    strategy_rows = evaluate_assignment_strategies(summaries, manual_rows, config)
    tracks_with_teams = apply_team_assignments(tracks, assignments)
    write_team_assignment_csv(output_dir / "team_assignment.csv", assignments)
    write_dict_csv(output_dir / "team_assignment_validation.csv", validation_rows, VALIDATION_FIELDS)
    write_dict_csv(output_dir / "strategy_evaluation.csv", strategy_rows, STRATEGY_FIELDS)
    write_csv_artifact(output_dir / TEAM_TRACKS_CSV, SPATIAL_TRACKS_CSV, tracks_with_teams)
    mirror_legacy_file(output_dir / TEAM_TRACKS_CSV, output_dir / LEGACY_TEAM_TRACKS_CSV)
    manifest_rows = write_team_assignment_manifest(output_dir / "team_assignment_manifest.csv", config)
    write_team_assignment_summary(output_dir / "summary.md", config, assignments, validation_rows, strategy_rows, manifest_rows)
    return {
        "config": config,
        "tracks": tracks,
        "tracks_with_teams": tracks_with_teams,
        "assignments": assignments,
        "validation_rows": validation_rows,
        "strategy_rows": strategy_rows,
        "manifest_rows": manifest_rows,
    }


def robot_track_summaries(rows: list[dict[str, Any]], config: TeamAssignmentConfig) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        if is_robot(row):
            grouped[(str(row["clip_id"]), str(row["track_id"]))].append(row)
    summaries: list[dict[str, Any]] = []
    for (clip_id, track_id), items in sorted(grouped.items()):
        ordered = sorted(items, key=lambda row: int(row["frame"]))
        first_frame = int(ordered[0]["frame"])
        initial = [row for row in ordered if int(row["frame"]) <= first_frame + max(0, config.initial_window_frames - 1)]
        xs = [float(row["x_norm"]) for row in ordered]
        ys = [float(row["y_norm"]) for row in ordered]
        initial_axis_values = [float(row[config.fallback_split_axis]) for row in initial if config.fallback_split_axis in row]
        zones = Counter(str(row.get("zone", "unknown")) for row in ordered)
        summaries.append(
            {
                "clip_id": clip_id,
                "track_id": track_id,
                "class_name": str(ordered[0].get("class_name", "")),
                "frame_start": first_frame,
                "frame_end": int(ordered[-1]["frame"]),
                "frames": len(ordered),
                "median_x_norm": round(float(median(xs)), 6),
                "median_y_norm": round(float(median(ys)), 6),
                "initial_axis_value": round(float(median(initial_axis_values)), 6) if initial_axis_values else round(float(median(xs)), 6),
                "dominant_zone": zones.most_common(1)[0][0] if zones else "unknown",
                "mean_confidence": round(sum(float(row.get("confidence", 0.0) or 0.0) for row in ordered) / len(ordered), 6),
            }
        )
    return summaries


def read_manual_assignments(path: str | Path) -> list[dict[str, str]]:
    with Path(path).open("r", newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def build_team_assignments(
    summaries: list[dict[str, Any]],
    manual_rows: list[dict[str, str]],
    config: TeamAssignmentConfig,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    summary_by_id = {(row["clip_id"], row["track_id"]): row for row in summaries}
    manual_by_id: dict[tuple[str, str], dict[str, str]] = {}
    validation_rows: list[dict[str, Any]] = []
    for row in manual_rows:
        key = (str(row.get("clip_id", "")), str(row.get("track_id", "")))
        if key not in summary_by_id:
            validation_rows.append(
                {
                    "clip_id": key[0],
                    "track_id": key[1],
                    "status": "fail",
                    "source": "manual_by_id",
                    "notes": "track_id not found in source tracks",
                }
            )
            continue
        if not known_team(str(row.get("team", ""))):
            validation_rows.append(
                {
                    "clip_id": key[0],
                    "track_id": key[1],
                    "status": "fail",
                    "source": "manual_by_id",
                    "notes": "manual team is empty/neutral/unknown",
                }
            )
            continue
        manual_by_id[key] = row
        validation_rows.append(
            {
                "clip_id": key[0],
                "track_id": key[1],
                "status": "pass",
                "source": "manual_by_id",
                "notes": "manual assignment accepted",
            }
        )

    clip_axis_values: dict[str, list[float]] = defaultdict(list)
    for summary in summaries:
        clip_axis_values[str(summary["clip_id"])].append(float(summary["initial_axis_value"]))

    assignments: list[dict[str, Any]] = []
    for summary in summaries:
        key = (str(summary["clip_id"]), str(summary["track_id"]))
        manual = manual_by_id.get(key)
        if manual:
            assignment = _assignment_from_manual(summary, manual)
        else:
            assignment = _assignment_from_initial_side(summary, clip_axis_values[str(summary["clip_id"])], config)
            validation_rows.append(
                {
                    "clip_id": summary["clip_id"],
                    "track_id": summary["track_id"],
                    "status": "pass",
                    "source": assignment["source"],
                    "notes": "fallback assignment generated from initial side",
                }
            )
        assignments.append(assignment)
    return assignments, validation_rows


def evaluate_assignment_strategies(
    summaries: list[dict[str, Any]],
    manual_rows: list[dict[str, str]],
    config: TeamAssignmentConfig,
) -> list[dict[str, Any]]:
    track_ids = {(row["clip_id"], row["track_id"]) for row in summaries}
    valid_manual = [
        row
        for row in manual_rows
        if (row.get("clip_id", ""), row.get("track_id", "")) in track_ids and known_team(str(row.get("team", "")))
    ]
    spread_values: list[float] = []
    by_clip: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for summary in summaries:
        by_clip[str(summary["clip_id"])].append(summary)
    for clip_rows in by_clip.values():
        values = [float(row["initial_axis_value"]) for row in clip_rows]
        if values:
            spread_values.append(max(values) - min(values))
    mean_spread = sum(spread_values) / len(spread_values) if spread_values else 0.0
    fallback_status = "available" if summaries else "unavailable"
    fallback_confidence = 0.64 if mean_spread >= config.min_side_spread_norm else 0.55
    return [
        {
            "strategy": "manual_by_id",
            "status": "available" if valid_manual else "editable_template",
            "confidence": 0.9 if valid_manual else 0.0,
            "source": config.manual_assignment_csv or "team_assignment.csv",
            "notes": f"{len(valid_manual)} valid manual rows; CSV can be edited by humans.",
        },
        {
            "strategy": "dominant_color",
            "status": "not_available",
            "confidence": 0.0,
            "source": config.tracks_csv,
            "notes": "Spatial tracks do not include robot crops or color histograms; color strategy is documented for future video/crop integration.",
        },
        {
            "strategy": "initial_side_fallback",
            "status": fallback_status,
            "confidence": round(fallback_confidence, 6),
            "source": config.tracks_csv,
            "notes": f"Split robots by initial {config.fallback_split_axis}; mean clip spread={mean_spread:.3f}.",
        },
    ]


def apply_team_assignments(rows: list[dict[str, Any]], assignments: list[dict[str, Any]]) -> list[dict[str, Any]]:
    team_by_id = {(str(row["clip_id"]), str(row["track_id"])): str(row["team"]) for row in assignments}
    result: list[dict[str, Any]] = []
    for row in rows:
        updated = dict(row)
        key = (str(row.get("clip_id", "")), str(row.get("track_id", "")))
        if is_robot(row) and key in team_by_id:
            updated["team"] = team_by_id[key]
            notes = str(updated.get("notes", ""))
            suffix = "team_assignment_applied"
            updated["notes"] = suffix if not notes else f"{notes}; {suffix}"
        result.append(updated)
    return result


def write_team_assignment_csv(path: str | Path, rows: list[dict[str, Any]]) -> None:
    write_dict_csv(path, rows, TEAM_ASSIGNMENT_FIELDS)


def write_dict_csv(path: str | Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def write_team_assignment_manifest(path: str | Path, config: TeamAssignmentConfig) -> list[dict[str, Any]]:
    rows = [
        _manifest_row("config", "yaml", "config.yaml", "configs/default.yaml", True, "configuration", "Configuration snapshot."),
        _manifest_row("team_assignment", "csv", "team_assignment.csv", config.tracks_csv, True, "editable_assignment", "Editable team assignment by track ID."),
        _manifest_row("team_assignment_validation", "csv", "team_assignment_validation.csv", "team_assignment.csv", True, "validation", "Validation of track IDs and team labels."),
        _manifest_row("strategy_evaluation", "csv", "strategy_evaluation.csv", config.tracks_csv, True, "strategy", "Manual/color/side strategy evaluation."),
        _manifest_row("tracks_with_teams", "csv", TEAM_TRACKS_CSV, f"{SPATIAL_TRACKS_CSV}|team_assignment.csv", True, "tracks", "Spatial tracks with approximate teams applied."),
        _manifest_row("summary", "md", "summary.md", "team_assignment.csv", True, "summary", "Team assignment summary."),
        _manifest_row("manifest", "csv", "team_assignment_manifest.csv", "team_assignment.csv", True, "manifest", "Team assignment artifact manifest."),
    ]
    if config.manual_assignment_csv:
        rows.append(_manifest_row("manual_input", "csv", config.manual_assignment_csv, config.manual_assignment_csv, True, "manual_input", "Human-edited assignment CSV input."))
    write_dict_csv(path, rows, MANIFEST_FIELDS)
    return rows


def write_team_assignment_summary(
    path: str | Path,
    config: TeamAssignmentConfig,
    assignments: list[dict[str, Any]],
    validation_rows: list[dict[str, Any]],
    strategy_rows: list[dict[str, Any]],
    manifest_rows: list[dict[str, Any]],
) -> None:
    team_counts = Counter(str(row["team"]) for row in assignments)
    source_counts = Counter(str(row["source"]) for row in assignments)
    validation_counts = Counter(str(row["status"]) for row in validation_rows)
    lines = [
        "# Asignacion de equipos",
        "",
        "## Resultado",
        "",
        "- Estado: `generado`.",
        f"- Regla: `{RULE_VERSION}`.",
        f"- Tracks fuente: `{config.tracks_csv}`.",
        f"- Robots asignados: `{len(assignments)}`.",
        f"- Archivo editable: `team_assignment.csv`.",
        f"- Tracks enriquecidos: `{TEAM_TRACKS_CSV}`.",
        "",
        "## Estrategias",
        "",
    ]
    for row in strategy_rows:
        lines.append(f"- `{row['strategy']}`: `{row['status']}`, confianza `{row['confidence']}`. {row['notes']}")
    lines.extend(["", "## Equipos", ""])
    for team, count in sorted(team_counts.items()):
        lines.append(f"- `{team}`: `{count}` tracks.")
    lines.extend(["", "## Fuentes", ""])
    for source, count in sorted(source_counts.items()):
        lines.append(f"- `{source}`: `{count}` tracks.")
    lines.extend(["", "## Validacion", ""])
    for status, count in sorted(validation_counts.items()):
        lines.append(f"- `{status}`: `{count}` filas.")
    lines.extend(
        [
            "",
            "## Uso tactico",
            "",
            "```bash",
            f".venv/bin/python scripts/run_tactical_metrics.py --tracks experiments/test_031_team_assignment/{TEAM_TRACKS_CSV} --experiment experiments/test_032_team_metrics",
            f".venv/bin/python scripts/run_advanced_events.py --tracks experiments/test_031_team_assignment/{TEAM_TRACKS_CSV} --interaction-metrics experiments/test_032_team_metrics/interaction_metrics.csv --interaction-edges experiments/test_032_team_metrics/interaction_edges.csv --experiment experiments/test_033_team_events",
            "```",
            "",
            "## Limitaciones",
            "",
            "- La asignacion por lado inicial es aproximada y editable; no sustituye revision humana ni deteccion visual de uniformes.",
            "- La estrategia de color queda documentada como no disponible porque los artefactos actuales no incluyen crops/histogramas por robot.",
            "- Si un clip tiene pocos robots o poco spread lateral, la confianza se mantiene conservadora.",
            "",
            "## Manifest",
            "",
            f"- Filas en `team_assignment_manifest.csv`: `{len(manifest_rows)}`.",
        ]
    )
    Path(path).write_text("\n".join(lines) + "\n", encoding="utf-8")


def config_to_dict(config: TeamAssignmentConfig) -> dict[str, Any]:
    return asdict(config)


def assignment_json_summary(assignments: list[dict[str, Any]], strategy_rows: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "rule_version": RULE_VERSION,
        "teams": dict(sorted(Counter(str(row["team"]) for row in assignments).items())),
        "sources": dict(sorted(Counter(str(row["source"]) for row in assignments).items())),
        "strategies": strategy_rows,
        "assumptions": [
            "Manual assignment by track ID is preferred when provided.",
            "Initial-side fallback approximates teams from the first observed robot positions.",
            "Dominant-color assignment is deferred until robot crops or video-derived color features are available.",
        ],
    }


def write_json_summary(path: str | Path, assignments: list[dict[str, Any]], strategy_rows: list[dict[str, Any]]) -> None:
    Path(path).write_text(json.dumps(assignment_json_summary(assignments, strategy_rows), indent=2, ensure_ascii=True) + "\n", encoding="utf-8")


def _assignment_from_manual(summary: dict[str, Any], manual: dict[str, str]) -> dict[str, Any]:
    row = _base_assignment(summary)
    row.update(
        {
            "team": str(manual.get("team", "")),
            "confidence": float(manual.get("confidence", 0.9) or 0.9),
            "source": "manual_by_id",
            "notes": str(manual.get("notes", "human editable assignment") or "human editable assignment"),
        }
    )
    return row


def _assignment_from_initial_side(summary: dict[str, Any], clip_axis_values: list[float], config: TeamAssignmentConfig) -> dict[str, Any]:
    row = _base_assignment(summary)
    axis_value = float(summary["initial_axis_value"])
    if len(clip_axis_values) <= 1:
        split = 0.5
        source = "initial_side_fallback_single_robot"
        base_confidence = 0.55
    else:
        split = float(median(clip_axis_values))
        spread = max(clip_axis_values) - min(clip_axis_values)
        source = "initial_side_fallback"
        base_confidence = 0.68 if spread >= config.min_side_spread_norm else 0.58
    team = config.fallback_left_team if axis_value <= split else config.fallback_right_team
    track_confidence = float(summary.get("mean_confidence", 0.0) or 0.0)
    row.update(
        {
            "team": team,
            "confidence": round(min(0.8, base_confidence * (0.75 + 0.25 * track_confidence)), 6),
            "source": source,
            "notes": f"fallback by initial {config.fallback_split_axis}; split={split:.3f}; value={axis_value:.3f}",
        }
    )
    return row


def _base_assignment(summary: dict[str, Any]) -> dict[str, Any]:
    return {
        "clip_id": summary["clip_id"],
        "track_id": summary["track_id"],
        "class_name": summary["class_name"],
        "team": "unknown",
        "confidence": 0.0,
        "source": "unassigned",
        "frame_start": summary["frame_start"],
        "frame_end": summary["frame_end"],
        "frames": summary["frames"],
        "median_x_norm": summary["median_x_norm"],
        "median_y_norm": summary["median_y_norm"],
        "dominant_zone": summary["dominant_zone"],
        "notes": "",
    }


def _manifest_row(asset_id: str, asset_type: str, path: str, source_artifact: str, is_versioned: bool, role: str, notes: str) -> dict[str, Any]:
    return {
        "asset_id": asset_id,
        "asset_type": asset_type,
        "path": path,
        "source_artifact": source_artifact,
        "is_versioned": str(is_versioned).lower(),
        "role": role,
        "notes": notes,
    }
