from __future__ import annotations

import csv
import json
import math
import re
from collections import defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import matplotlib.image as mpimg
import matplotlib.pyplot as plt
import numpy as np

from futbotmx.level3.spatial import FieldModel, read_level3_tracks


RULE_VERSION = "level3_visualizations_v0.1"
ROBOT_COLORS = ["#1f77b4", "#d62728", "#2ca02c", "#9467bd", "#ff7f0e", "#17becf", "#8c564b", "#e377c2"]
EDGE_COLORS = {
    "possession_candidate": "#111111",
    "ball_proximity": "#4c78a8",
    "pressure_candidate": "#9467bd",
    "dispute_cluster": "#d62728",
    "robot_proximity": "#2ca02c",
}


@dataclass(frozen=True)
class Level3VisualizationConfig:
    tracks_csv: str = "experiments/test_020_level3_spatial_model/level3_tracks.csv"
    calibration_json: str = "experiments/test_020_level3_spatial_model/field_calibration.json"
    spatial_control_csv: str = "experiments/test_021_level3_tactical_metrics/spatial_control.csv"
    voronoi_frames_csv: str = "experiments/test_021_level3_tactical_metrics/voronoi_frames.csv"
    interaction_graph_json: str = "experiments/test_021_level3_tactical_metrics/interaction_graph.json"
    interaction_edges_csv: str = "experiments/test_021_level3_tactical_metrics/interaction_edges.csv"
    highlights_csv: str = "experiments/test_022_level3_advanced_events/level3_highlights.csv"
    events_json: str = "experiments/test_022_level3_advanced_events/level3_events.json"
    level2_root: str = "experiments/test_017_level2_closure"
    output_dir: str = "experiments/test_023_level3_visualizations"
    top_highlights: int = 4
    grid_x: int = 24
    grid_y: int = 16

    @property
    def grid_cell_count(self) -> int:
        return self.grid_x * self.grid_y


def read_csv_rows(path: str | Path) -> list[dict[str, str]]:
    with Path(path).open("r", newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def read_json(path: str | Path) -> Any:
    with Path(path).open("r", encoding="utf-8") as handle:
        return json.load(handle)


def write_csv_rows(path: str | Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def _is_robot(row: dict[str, Any]) -> bool:
    return "robot" in str(row.get("class_name", ""))


def _is_ball(row: dict[str, Any]) -> bool:
    return str(row.get("class_name", "")) == "ball"


def _usable(row: dict[str, Any]) -> bool:
    return str(row.get("calibration_status", "")) == "rectified" and str(row.get("track_quality", "")) in {"usable", "provisional"}


def _frame_rows(tracks: list[dict[str, Any]], clip_id: str, frame: int) -> list[dict[str, Any]]:
    exact = [row for row in tracks if str(row["clip_id"]) == clip_id and int(row["frame"]) == frame]
    if exact:
        return exact
    clip_rows = [row for row in tracks if str(row["clip_id"]) == clip_id]
    if not clip_rows:
        return []
    nearest_frame = min({int(row["frame"]) for row in clip_rows}, key=lambda item: abs(item - frame))
    return [row for row in clip_rows if int(row["frame"]) == nearest_frame]


def _clip_rows(tracks: list[dict[str, Any]], clip_id: str) -> list[dict[str, Any]]:
    return [row for row in tracks if str(row["clip_id"]) == clip_id]


def _grid_points(config: Level3VisualizationConfig) -> list[tuple[float, float]]:
    return [((x + 0.5) / config.grid_x, (y + 0.5) / config.grid_y) for y in range(config.grid_y) for x in range(config.grid_x)]


def _nearest_robot(point: tuple[float, float], robots: list[dict[str, Any]]) -> dict[str, Any] | None:
    if not robots:
        return None
    x, y = point
    return min(robots, key=lambda robot: math.hypot(float(robot["x_norm"]) - x, float(robot["y_norm"]) - y))


def _draw_pitch(ax: Any, title: str | None = None) -> None:
    model = FieldModel()
    ax.set_facecolor("#e9ffd8")
    ax.add_patch(plt.Rectangle((0, 0), 1, 1, fill=False, lw=1.8, ec="#00d25b"))
    for y in (1.0 / 3.0, 2.0 / 3.0, 0.5):
        ax.axhline(y, color="#b7f300", lw=0.8, ls="--" if y != 0.5 else "-")
    goal_start = 0.5 - model.goal_width_norm / 2
    goal_end = 0.5 + model.goal_width_norm / 2
    ax.plot([goal_start, goal_end], [0.0, 0.0], color="#b7f300", lw=3)
    ax.plot([goal_start, goal_end], [1.0, 1.0], color="#b7f300", lw=3)
    ax.set_xlim(-0.04, 1.04)
    ax.set_ylim(1.04, -0.04)
    ax.set_xlabel("x_norm")
    ax.set_ylabel("y_norm")
    ax.grid(alpha=0.16)
    ax.set_aspect("equal", adjustable="box")
    if title:
        ax.set_title(title)


def draw_voronoi_minimap(
    output_path: str | Path,
    tracks: list[dict[str, Any]],
    clip_id: str,
    frame: int,
    config: Level3VisualizationConfig,
    event_label: str = "",
) -> dict[str, Any]:
    rows = _frame_rows(tracks, clip_id, frame)
    robots = [row for row in rows if _is_robot(row) and _usable(row)]
    balls = [row for row in rows if _is_ball(row) and _usable(row)]
    robot_ids = sorted(str(row["track_id"]) for row in robots)
    color_by_robot = {track_id: ROBOT_COLORS[index % len(ROBOT_COLORS)] for index, track_id in enumerate(robot_ids)}

    fig, ax = plt.subplots(figsize=(5.2, 6.2))
    _draw_pitch(ax, f"Voronoi {clip_id} frame {frame}")
    if robots:
        xs: list[float] = []
        ys: list[float] = []
        colors: list[str] = []
        for point in _grid_points(config):
            owner = _nearest_robot(point, robots)
            if owner is None:
                continue
            xs.append(point[0])
            ys.append(point[1])
            colors.append(color_by_robot[str(owner["track_id"])])
        ax.scatter(xs, ys, c=colors, s=18, marker="s", alpha=0.28, linewidths=0)

    for robot in robots:
        color = color_by_robot[str(robot["track_id"])]
        ax.scatter([float(robot["x_norm"])], [float(robot["y_norm"])], color=color, s=55, edgecolor="#222222", linewidth=0.8)
        ax.text(float(robot["x_norm"]), float(robot["y_norm"]), str(robot["track_id"]).replace("_bt_", "_"), fontsize=7, color=color)
    for ball in balls:
        ax.scatter([float(ball["x_norm"])], [float(ball["y_norm"])], color="#111111", s=42, marker="o")
        ax.text(float(ball["x_norm"]), float(ball["y_norm"]), str(ball["track_id"]).replace("_bt_", "_"), fontsize=7, color="#111111")
    if event_label:
        ax.text(0.02, 1.025, event_label, fontsize=8)
    fig.tight_layout()
    fig.savefig(output_path, dpi=150)
    plt.close(fig)
    return {"clip_id": clip_id, "frame": frame, "robots": len(robots), "balls": len(balls), "path": Path(output_path).name}


def _load_calibration(path: str | Path) -> dict[str, Any]:
    payload = read_json(path)
    return payload.get("clips", {}) if isinstance(payload, dict) else {}


def _project_norm_to_image(homography: list[list[float]], x_norm: float, y_norm: float) -> tuple[float, float]:
    matrix = np.asarray(homography, dtype=float)
    inverse = np.linalg.inv(matrix)
    point = inverse @ np.asarray([x_norm, y_norm, 1.0], dtype=float)
    return float(point[0] / point[2]), float(point[1] / point[2])


def find_level2_overlay(level2_root: str | Path, clip_id: str, frame: int) -> Path | None:
    clip_dir = Path(level2_root) / clip_id
    candidates: list[tuple[int, Path]] = []
    for path in sorted(clip_dir.glob("overlay_*_frame_*.png")):
        match = re.search(r"_frame_(\d+)\.png$", path.name)
        if not match:
            continue
        candidates.append((int(match.group(1)), path))
    if not candidates:
        return None
    exact = [path for candidate_frame, path in candidates if candidate_frame == frame]
    if exact:
        return exact[0]
    candidate_frame, path = min(candidates, key=lambda item: abs(item[0] - frame))
    return path if abs(candidate_frame - frame) <= 8 else None


def draw_voronoi_original_overlay(
    output_path: str | Path,
    tracks: list[dict[str, Any]],
    clip_id: str,
    frame: int,
    calibration: dict[str, Any],
    overlay_path: Path,
    config: Level3VisualizationConfig,
) -> dict[str, Any]:
    homography = calibration.get("homography")
    if not homography:
        raise ValueError(f"Missing homography for {clip_id}")
    image = mpimg.imread(overlay_path)
    rows = _frame_rows(tracks, clip_id, frame)
    robots = [row for row in rows if _is_robot(row) and _usable(row)]
    robot_ids = sorted(str(row["track_id"]) for row in robots)
    color_by_robot = {track_id: ROBOT_COLORS[index % len(ROBOT_COLORS)] for index, track_id in enumerate(robot_ids)}

    fig, ax = plt.subplots(figsize=(4.5, 5.8))
    ax.imshow(image)
    ax.set_title(f"Voronoi proyectado {clip_id} frame {frame}")
    ax.set_axis_off()
    if robots:
        xs: list[float] = []
        ys: list[float] = []
        colors: list[str] = []
        for point in _grid_points(config):
            owner = _nearest_robot(point, robots)
            if owner is None:
                continue
            x_img, y_img = _project_norm_to_image(homography, point[0], point[1])
            xs.append(x_img)
            ys.append(y_img)
            colors.append(color_by_robot[str(owner["track_id"])])
        ax.scatter(xs, ys, c=colors, s=9, marker="s", alpha=0.24, linewidths=0)
    fig.tight_layout()
    fig.savefig(output_path, dpi=100)
    plt.close(fig)
    return {
        "clip_id": clip_id,
        "frame": frame,
        "path": Path(output_path).name,
        "source_overlay": overlay_path.as_posix(),
    }


def draw_interaction_graph(
    output_path: str | Path,
    graph: dict[str, Any],
    tracks: list[dict[str, Any]],
) -> dict[str, Any]:
    nodes = graph.get("nodes", [])
    edges = graph.get("edges", [])
    position_by_node = _node_positions(tracks)
    robot_color_by_key = {
        key: ROBOT_COLORS[index % len(ROBOT_COLORS)]
        for index, key in enumerate(sorted(key for key, rows in _tracks_by_node(tracks).items() if rows and _is_robot(rows[0])))
    }
    fig, ax = plt.subplots(figsize=(8, 6))
    _draw_pitch(ax, "Grafo de interaccion Nivel 3")
    max_frames = max([int(edge.get("frames", 1)) for edge in edges] or [1])
    for edge in edges:
        source_key = (str(edge["clip_id"]), str(edge["source"]))
        target_key = (str(edge["clip_id"]), str(edge["target"]))
        if source_key not in position_by_node or target_key not in position_by_node:
            continue
        sx, sy = position_by_node[source_key]
        tx, ty = position_by_node[target_key]
        edge_type = str(edge.get("edge_type", "unknown"))
        width = 0.8 + 4.2 * int(edge.get("frames", 1)) / max_frames
        ax.plot([sx, tx], [sy, ty], color=EDGE_COLORS.get(edge_type, "#777777"), linewidth=width, alpha=0.55)
        ax.text((sx + tx) / 2, (sy + ty) / 2, edge_type.replace("_", " "), fontsize=6, color=EDGE_COLORS.get(edge_type, "#555555"))
    for node in nodes:
        key = (str(node["clip_id"]), str(node["node_id"]))
        if key not in position_by_node:
            continue
        x, y = position_by_node[key]
        class_name = str(node.get("class_name", ""))
        color = "#111111" if class_name == "ball" else robot_color_by_key.get(key, "#1f77b4")
        marker = "o" if class_name == "ball" else "s"
        ax.scatter([x], [y], color=color, marker=marker, s=70, edgecolor="#222222", linewidth=0.8)
        ax.text(x, y, str(node["node_id"]).replace("_bt_", "_"), fontsize=7, color=color)
    fig.tight_layout()
    fig.savefig(output_path, dpi=150)
    plt.close(fig)
    return {"path": Path(output_path).name, "nodes": len(nodes), "edges": len(edges)}


def _node_positions(tracks: list[dict[str, Any]]) -> dict[tuple[str, str], tuple[float, float]]:
    grouped = _tracks_by_node(tracks)
    positions: dict[tuple[str, str], tuple[float, float]] = {}
    for key, rows in grouped.items():
        positions[key] = (
            sum(float(row["x_norm"]) for row in rows) / len(rows),
            sum(float(row["y_norm"]) for row in rows) / len(rows),
        )
    return positions


def _tracks_by_node(tracks: list[dict[str, Any]]) -> dict[tuple[str, str], list[dict[str, Any]]]:
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in tracks:
        if (_is_robot(row) or _is_ball(row)) and _usable(row):
            grouped[(str(row["clip_id"]), str(row["track_id"]))].append(row)
    return grouped


def draw_minimap_highlight(
    output_path: str | Path,
    tracks: list[dict[str, Any]],
    highlight: dict[str, str],
) -> dict[str, Any]:
    clip_id = str(highlight["clip_id"])
    frame_start = int(highlight["frame_start"])
    frame_end = int(highlight["frame_end"])
    clip_rows = _clip_rows(tracks, clip_id)
    frames = range(max(frame_start - 6, min(int(row["frame"]) for row in clip_rows)), frame_end + 7)
    trails: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in clip_rows:
        if int(row["frame"]) in frames and (_is_robot(row) or _is_ball(row)) and _usable(row):
            trails[str(row["track_id"])].append(row)
    fig, ax = plt.subplots(figsize=(5.2, 6.2))
    _draw_pitch(ax, f"Highlight rank {highlight['rank']} {clip_id}")
    ax.axhspan(0.0, 1.0 / 3.0, color="#f7f0d6", alpha=0.25)
    for index, (track_id, rows) in enumerate(sorted(trails.items())):
        ordered = sorted(rows, key=lambda row: int(row["frame"]))
        is_ball_track = any(_is_ball(row) for row in ordered)
        color = "#111111" if is_ball_track else ROBOT_COLORS[index % len(ROBOT_COLORS)]
        marker = "o" if is_ball_track else "."
        xs = [float(row["x_norm"]) for row in ordered]
        ys = [float(row["y_norm"]) for row in ordered]
        ax.plot(xs, ys, color=color, marker=marker, linewidth=1.5, markersize=3)
        ax.text(max(0.02, min(0.92, xs[-1])), max(0.03, min(0.97, ys[-1])), track_id.replace("_bt_", "_"), fontsize=7, color=color)
    ax.text(0.02, 1.025, f"frames {frame_start}-{frame_end} score {float(highlight['score']):.1f} conf {float(highlight['confidence']):.2f}", fontsize=8)
    fig.tight_layout()
    fig.savefig(output_path, dpi=150)
    plt.close(fig)
    return {"clip_id": clip_id, "frame_start": frame_start, "frame_end": frame_end, "path": Path(output_path).name}


def draw_storyboard(
    output_path: str | Path,
    highlights: list[dict[str, str]],
    minimap_assets: dict[str, Path],
    level2_root: str | Path,
    max_items: int = 3,
) -> list[dict[str, Any]]:
    selected = sorted(highlights, key=lambda row: int(row["rank"]))[:max_items]
    fig, axes = plt.subplots(len(selected), 3, figsize=(10, 3.2 * len(selected)), squeeze=False)
    manifest_rows: list[dict[str, Any]] = []
    for row_index, highlight in enumerate(selected):
        clip_id = str(highlight["clip_id"])
        frame = int(highlight["frame_start"])
        reference = find_level2_overlay(level2_root, clip_id, frame)
        minimap = minimap_assets.get(str(highlight["highlight_id"]))
        text = (
            f"Rank {highlight['rank']} | {clip_id}\n"
            f"Frames {highlight['frame_start']}-{highlight['frame_end']}\n"
            f"Score {float(highlight['score']):.1f} | Conf {float(highlight['confidence']):.2f}\n"
            f"{highlight['reason']}"
        )
        _draw_image_or_text(axes[row_index][0], reference, "Referencia frame Nivel 2")
        _draw_image_or_text(axes[row_index][1], minimap, "Mini-mapa highlight")
        axes[row_index][2].text(0.02, 0.95, text, va="top", fontsize=10, wrap=True)
        axes[row_index][2].set_axis_off()
        axes[row_index][2].set_title("Narrativa corta")
        manifest_rows.append(
            {
                "highlight_id": highlight["highlight_id"],
                "rank": highlight["rank"],
                "clip_id": clip_id,
                "frame_start": highlight["frame_start"],
                "frame_end": highlight["frame_end"],
                "reference_frame_path": reference.as_posix() if reference else "",
                "minimap_path": minimap.name if minimap else "",
                "notes": "Storyboard row combines Level 2 frame reference, Level 3 minimap and conservative text.",
            }
        )
    fig.tight_layout()
    fig.savefig(output_path, dpi=110)
    plt.close(fig)
    return manifest_rows


def _draw_image_or_text(ax: Any, image_path: Path | None, title: str) -> None:
    ax.set_title(title)
    ax.set_axis_off()
    if image_path and image_path.exists():
        ax.imshow(mpimg.imread(image_path))
    else:
        ax.text(0.5, 0.5, "sin imagen", ha="center", va="center")


def build_visualizations(config: Level3VisualizationConfig) -> dict[str, Any]:
    output_dir = Path(config.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    tracks = read_level3_tracks(config.tracks_csv)
    graph = read_json(config.interaction_graph_json)
    voronoi_frames = read_csv_rows(config.voronoi_frames_csv)
    highlights = read_csv_rows(config.highlights_csv)
    calibration_by_clip = _load_calibration(config.calibration_json)
    manifest: list[dict[str, Any]] = []

    for row in voronoi_frames:
        clip_id = str(row["clip_id"])
        frame = int(row["frame"])
        output = output_dir / f"voronoi_frame_{clip_id}_{frame}.png"
        result = draw_voronoi_minimap(output, tracks, clip_id, frame, config, event_label=f"entropy {float(row['entropy']):.2f}")
        manifest.append(_manifest_row(clip_id, f"voronoi_{clip_id}_{frame}", "png", result["path"], config.voronoi_frames_csv, frame, frame, "", True, "Voronoi minimap clipped to normalized field."))
        overlay = find_level2_overlay(config.level2_root, clip_id, frame)
        calibration = calibration_by_clip.get(clip_id, {})
        if overlay and calibration.get("homography"):
            original_output = output_dir / f"voronoi_original_frame_{clip_id}_{frame}.png"
            original_result = draw_voronoi_original_overlay(original_output, tracks, clip_id, frame, calibration, overlay, config)
            manifest.append(_manifest_row(clip_id, f"voronoi_original_{clip_id}_{frame}", "png", original_result["path"], overlay.as_posix(), frame, frame, "", True, "Projected onto existing Level 2 lightweight overlay."))

    graph_output = output_dir / "interaction_graph.png"
    graph_result = draw_interaction_graph(graph_output, graph, tracks)
    manifest.append(_manifest_row("multi_clip", "interaction_graph", "png", graph_result["path"], config.interaction_graph_json, "", "", "", True, "Edges styled by possession, dispute, pressure and proximity."))

    minimap_assets: dict[str, Path] = {}
    for highlight in sorted(highlights, key=lambda item: int(item["rank"]))[: config.top_highlights]:
        output = output_dir / f"minimap_highlight_rank_{int(highlight['rank']):02d}_{highlight['clip_id']}.png"
        result = draw_minimap_highlight(output, tracks, highlight)
        minimap_assets[str(highlight["highlight_id"])] = output
        manifest.append(_manifest_row(result["clip_id"], f"minimap_highlight_{highlight['rank']}", "png", result["path"], config.highlights_csv, result["frame_start"], result["frame_end"], highlight["highlight_id"], True, "Highlight minimap with trails, zone and event label."))

    storyboard_output = output_dir / "highlight_storyboard.png"
    storyboard_rows = draw_storyboard(storyboard_output, highlights, minimap_assets, config.level2_root)
    manifest.append(_manifest_row("multi_clip", "highlight_storyboard", "png", storyboard_output.name, config.highlights_csv, "", "", "", True, "Storyboard combines frame reference, minimap and text."))
    write_storyboard_manifest(output_dir / "highlight_storyboard_manifest.csv", storyboard_rows)
    manifest.append(_manifest_row("multi_clip", "highlight_storyboard_manifest", "csv", "highlight_storyboard_manifest.csv", config.highlights_csv, "", "", "", True, "Storyboard source manifest."))
    write_visualization_manifest(output_dir / "visualization_manifest.csv", manifest)
    return {
        "config": config,
        "manifest": manifest,
        "storyboard_rows": storyboard_rows,
        "voronoi_frames": voronoi_frames,
        "highlights": highlights,
    }


def _manifest_row(
    clip_id: str,
    asset_id: str,
    asset_type: str,
    path: str,
    source_artifact: str,
    frame_start: Any,
    frame_end: Any,
    event_id: str,
    is_versioned: bool,
    notes: str,
) -> dict[str, Any]:
    return {
        "clip_id": clip_id,
        "asset_id": asset_id,
        "asset_type": asset_type,
        "path": path,
        "source_artifact": source_artifact,
        "frame_start": frame_start,
        "frame_end": frame_end,
        "event_id": event_id,
        "is_versioned": str(is_versioned).lower(),
        "notes": notes,
    }


def write_visualization_manifest(path: str | Path, rows: list[dict[str, Any]]) -> None:
    fieldnames = ["clip_id", "asset_id", "asset_type", "path", "source_artifact", "frame_start", "frame_end", "event_id", "is_versioned", "notes"]
    write_csv_rows(path, rows, fieldnames)


def write_storyboard_manifest(path: str | Path, rows: list[dict[str, Any]]) -> None:
    fieldnames = ["highlight_id", "rank", "clip_id", "frame_start", "frame_end", "reference_frame_path", "minimap_path", "notes"]
    write_csv_rows(path, rows, fieldnames)


def config_to_dict(config: Level3VisualizationConfig) -> dict[str, Any]:
    return asdict(config)
