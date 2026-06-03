from __future__ import annotations

import csv
import json
from collections import Counter
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt


def read_tracks_csv(path: str | Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with Path(path).open("r", newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            for key in ("frame", "x", "y", "confidence"):
                if key in row and row[key] != "":
                    row[key] = float(row[key])
            row["frame"] = int(row["frame"])
            rows.append(row)
    return rows


def _load_json(path: str | Path) -> Any:
    with Path(path).open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _matches_class(row: dict[str, Any], class_name: str | None) -> bool:
    if class_name is None:
        return True
    row_class = str(row["class_name"])
    if class_name == "robot":
        return "robot" in row_class
    return row_class == class_name


def _write_empty_plot(output_path: str | Path, title: str) -> None:
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(8, 3))
    ax.text(0.5, 0.5, "sin datos", ha="center", va="center")
    ax.set_title(title)
    ax.set_axis_off()
    fig.tight_layout()
    fig.savefig(output, dpi=140)
    plt.close(fig)


def write_filtered_heatmap(
    tracks_csv: str | Path,
    output_path: str | Path,
    width: int,
    height: int,
    class_name: str | None = None,
    track_id: str | None = None,
    title: str | None = None,
) -> int:
    rows = read_tracks_csv(tracks_csv)
    filtered = [
        row
        for row in rows
        if _matches_class(row, class_name) and (track_id is None or str(row["track_id"]) == track_id)
    ]
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    label = title or f"Heatmap {track_id or class_name or 'all'}"
    if not filtered:
        _write_empty_plot(output, label)
        return 0

    xs = [float(row["x"]) for row in filtered]
    ys = [float(row["y"]) for row in filtered]
    fig, ax = plt.subplots(figsize=(7, 7))
    hist = ax.hist2d(xs, ys, bins=28, range=[[0, width], [0, height]], cmap="magma")
    ax.invert_yaxis()
    ax.set_title(label)
    ax.set_xlabel("x")
    ax.set_ylabel("y")
    fig.colorbar(hist[3], ax=ax, label="posiciones")
    fig.tight_layout()
    fig.savefig(output, dpi=140)
    plt.close(fig)
    return len(filtered)


def write_event_timeline(events_json: str | Path, output_path: str | Path) -> int:
    events = _load_json(events_json)
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    if not events:
        _write_empty_plot(output, "Timeline de eventos Nivel 2")
        return 0

    reliability_color = {
        "confiable": "#2ca25f",
        "provisional": "#f0ad00",
        "descartado": "#777777",
    }
    y_labels = sorted({str(event["event_type"]) for event in events})
    y_index = {label: index for index, label in enumerate(y_labels)}
    fig_height = max(3.0, 0.7 * len(y_labels) + 1.8)
    fig, ax = plt.subplots(figsize=(10, fig_height))
    for event in events:
        start = float(event["time_start_sec"])
        end = float(event["time_end_sec"])
        width = max(end - start, 0.01)
        y = y_index[str(event["event_type"])]
        reliability = str(event.get("reliability", "provisional"))
        ax.barh(
            y,
            width,
            left=start,
            height=0.45,
            color=reliability_color.get(reliability, "#777777"),
            edgecolor="#222222",
            linewidth=0.8,
        )
        ax.text(start + width / 2, y, str(event["event_id"]).replace("lvl2_", ""), ha="center", va="center", fontsize=7)
    ax.set_yticks(range(len(y_labels)))
    ax.set_yticklabels(y_labels)
    ax.set_xlabel("tiempo (s)")
    ax.set_title("Timeline de eventos Nivel 2")
    ax.grid(axis="x", alpha=0.25)
    fig.tight_layout()
    fig.savefig(output, dpi=140)
    plt.close(fig)
    return len(events)


def write_possession_timeline(metrics_json: str | Path, output_path: str | Path) -> int:
    data = _load_json(metrics_json)
    intervals = data.get("possession_timeline", [])
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    if not intervals:
        _write_empty_plot(output, "Timeline de posesion Nivel 2")
        return 0

    robot_ids = sorted({str(item["robot_id"]) for item in intervals})
    y_index = {robot_id: index for index, robot_id in enumerate(robot_ids)}
    fig_height = max(3.0, 0.7 * len(robot_ids) + 1.8)
    fig, ax = plt.subplots(figsize=(10, fig_height))
    for item in intervals:
        start = float(item["time_start_sec"])
        end = float(item["time_end_sec"])
        width = max(float(item.get("duration_sec", end - start)), 0.01)
        robot_id = str(item["robot_id"])
        y = y_index[robot_id]
        ax.barh(y, width, left=start, height=0.45, color="#3182bd", edgecolor="#1b4f72", linewidth=0.8)
        ax.text(start + width / 2, y, f"{float(item['mean_ball_distance_px']):.0f}px", ha="center", va="center", fontsize=7)
    ax.set_yticks(range(len(robot_ids)))
    ax.set_yticklabels(robot_ids)
    ax.set_xlabel("tiempo (s)")
    ax.set_title("Timeline de posesion Nivel 2")
    ax.grid(axis="x", alpha=0.25)
    fig.tight_layout()
    fig.savefig(output, dpi=140)
    plt.close(fig)
    return len(intervals)


def build_heatmap_specs(tracks_csv: str | Path) -> list[dict[str, str]]:
    rows = read_tracks_csv(tracks_csv)
    classes = sorted({str(row["class_name"]) for row in rows})
    specs: list[dict[str, str]] = []
    for class_name in classes:
        if class_name == "ball" or "robot" in class_name:
            specs.append({"kind": "class", "id": class_name, "filename": f"heatmap_class_{class_name}.png"})
    for track_id in sorted({str(row["track_id"]) for row in rows}):
        safe_id = track_id.replace("/", "_")
        specs.append({"kind": "track", "id": track_id, "filename": f"heatmap_track_{safe_id}.png"})
    return specs


def write_manifest(path: str | Path, rows: list[dict[str, Any]]) -> None:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(rows[0].keys()) if rows else ["artifact", "type", "path", "rows"]
    with output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def summarize_visual_inputs(events_json: str | Path, metrics_json: str | Path) -> dict[str, Any]:
    events = _load_json(events_json)
    metrics = _load_json(metrics_json)
    event_counts = Counter(str(event["event_type"]) for event in events)
    reliability_counts = Counter(str(event.get("reliability", "unknown")) for event in events)
    return {
        "event_counts": dict(sorted(event_counts.items())),
        "reliability_counts": dict(sorted(reliability_counts.items())),
        "possession_intervals": len(metrics.get("possession_timeline", [])),
        "track_count": metrics.get("summary", {}).get("track_count", 0),
        "observed_frames": metrics.get("summary", {}).get("observed_frames", 0),
    }
