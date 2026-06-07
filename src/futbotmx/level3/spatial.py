from __future__ import annotations

import csv
import json
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

import matplotlib.pyplot as plt
import numpy as np

from futbotmx.level3.schema import write_csv_artifact


RULE_VERSION = "level3_spatial_model_v0.1"
FIELD_POINT_LABELS = ("top_left", "top_right", "bottom_right", "bottom_left")
FIELD_POINTS = ((0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0))


@dataclass(frozen=True)
class FieldModel:
    x_min: float = 0.0
    x_max: float = 1.0
    y_min: float = 0.0
    y_max: float = 1.0
    goal_width_norm: float = 0.22
    zone_axis: str = "y"
    origin: str = "top_left_visible_field"
    direction: str = "x_norm left_to_right, y_norm top_to_bottom"

    def to_dict(self) -> dict[str, Any]:
        return {
            "coordinate_system": {
                "origin": self.origin,
                "direction": self.direction,
                "units": "normalized_visible_field",
                "x_norm_range": [self.x_min, self.x_max],
                "y_norm_range": [self.y_min, self.y_max],
                "level2_zone_axis": self.zone_axis,
            },
            "relative_dimensions": {
                "field_width_x_norm": self.x_max - self.x_min,
                "field_length_y_norm": self.y_max - self.y_min,
                "goal_width_norm": self.goal_width_norm,
            },
            "goals": [
                {
                    "goal_id": "top_goal",
                    "line_y_norm": self.y_min,
                    "x_norm_start": 0.5 - self.goal_width_norm / 2,
                    "x_norm_end": 0.5 + self.goal_width_norm / 2,
                },
                {
                    "goal_id": "bottom_goal",
                    "line_y_norm": self.y_max,
                    "x_norm_start": 0.5 - self.goal_width_norm / 2,
                    "x_norm_end": 0.5 + self.goal_width_norm / 2,
                },
            ],
            "tactical_zones": [
                {"zone": "defensive_third", "y_norm_min": 0.0, "y_norm_max": 1.0 / 3.0},
                {"zone": "middle_third", "y_norm_min": 1.0 / 3.0, "y_norm_max": 2.0 / 3.0},
                {"zone": "attacking_third", "y_norm_min": 2.0 / 3.0, "y_norm_max": 1.0},
            ],
        }


@dataclass(frozen=True)
class ClipSpatialSpec:
    clip_id: str
    width: int
    height: int
    fps: float
    role: str = "candidate"


@dataclass(frozen=True)
class ClipCalibration:
    clip_id: str
    calibration_id: str
    method: str
    status: str
    confidence: float
    image_width: int
    image_height: int
    image_points: tuple[tuple[float, float], ...]
    field_points: tuple[tuple[float, float], ...]
    homography: tuple[tuple[float, float], ...] | None
    notes: str

    @property
    def usable(self) -> bool:
        return self.status == "usable" and self.homography is not None

    def to_dict(self) -> dict[str, Any]:
        payload = {
            "clip_id": self.clip_id,
            "calibration_id": self.calibration_id,
            "method": self.method,
            "status": self.status,
            "confidence": round(float(self.confidence), 6),
            "image_size": {"width": self.image_width, "height": self.image_height},
            "image_points": [
                {"label": label, "x": round(point[0], 6), "y": round(point[1], 6)}
                for label, point in zip(FIELD_POINT_LABELS, self.image_points)
            ],
            "field_points": [
                {"label": label, "x_norm": point[0], "y_norm": point[1]}
                for label, point in zip(FIELD_POINT_LABELS, self.field_points)
            ],
            "homography": self.homography,
            "fallback": {
                "method": "image_extent_normalization",
                "status": "available_when_homography_unusable",
            },
            "manual_calibration": {
                "supported": True,
                "instruction": "Replace image_points with four reviewed field corners in top_left/top_right/bottom_right/bottom_left order.",
            },
            "assumptions": [
                "Visible green field bbox approximates the playable area for Level 3 demo coordinates.",
                "x_norm follows image left-to-right and y_norm follows image top-to-bottom to preserve Level 2 zone_axis direction.",
            ],
            "limitations": [
                "Perspective and lens distortion are not fully solved by the bbox seed.",
                "Team side/orientation is still unknown, so zones are tactical thirds rather than official attacking direction.",
            ],
            "notes": self.notes,
        }
        return payload


def solve_homography(
    image_points: Iterable[tuple[float, float]],
    field_points: Iterable[tuple[float, float]],
) -> tuple[tuple[float, float], ...]:
    src = list(image_points)
    dst = list(field_points)
    if len(src) != len(dst) or len(src) < 4:
        raise ValueError("Homography requires at least four paired points")

    rows: list[list[float]] = []
    for (x, y), (u, v) in zip(src, dst):
        rows.append([-x, -y, -1.0, 0.0, 0.0, 0.0, u * x, u * y, u])
        rows.append([0.0, 0.0, 0.0, -x, -y, -1.0, v * x, v * y, v])

    matrix = np.asarray(rows, dtype=float)
    _, _, vh = np.linalg.svd(matrix)
    homography = vh[-1].reshape((3, 3))
    if abs(homography[2, 2]) > 1e-12:
        homography = homography / homography[2, 2]
    return tuple(tuple(float(value) for value in row) for row in homography)


def apply_homography_point(
    homography: tuple[tuple[float, float], ...],
    x: float,
    y: float,
) -> tuple[float, float]:
    matrix = np.asarray(homography, dtype=float)
    point = np.asarray([float(x), float(y), 1.0], dtype=float)
    transformed = matrix @ point
    if abs(float(transformed[2])) <= 1e-12:
        raise ValueError("Homography produced a point at infinity")
    return float(transformed[0] / transformed[2]), float(transformed[1] / transformed[2])


def normalized_zone(x_norm: float, y_norm: float, zone_axis: str = "y") -> str:
    position = y_norm if zone_axis == "y" else x_norm
    if position < 1.0 / 3.0:
        return "defensive_third"
    if position < 2.0 / 3.0:
        return "middle_third"
    return "attacking_third"


def read_level3_tracks(path: str | Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with Path(path).open("r", newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            for key in ("frame", "time_sec", "x", "y", "bbox_x1", "bbox_y1", "bbox_x2", "bbox_y2", "confidence", "x_norm", "y_norm"):
                if key in row and row[key] != "":
                    row[key] = float(row[key])
            if "frame" in row:
                row["frame"] = int(row["frame"])
            rows.append(row)
    return rows


def _clip(value: float, lower: float = 0.0, upper: float = 1.0) -> float:
    return max(lower, min(upper, value))


def _median(values: list[float]) -> float:
    return float(np.median(np.asarray(values, dtype=float)))


def polygon_area(points: Iterable[tuple[float, float]]) -> float:
    coords = list(points)
    if len(coords) < 3:
        return 0.0
    area = 0.0
    for index, (x1, y1) in enumerate(coords):
        x2, y2 = coords[(index + 1) % len(coords)]
        area += x1 * y2 - x2 * y1
    return abs(area) / 2.0


def estimate_manual_calibration_confidence(
    image_points: Iterable[tuple[float, float]],
    spec: ClipSpatialSpec,
    min_field_coverage: float = 0.35,
) -> float:
    points = list(image_points)
    if len(points) < 4:
        return 0.0
    width = max(1.0, float(spec.width))
    height = max(1.0, float(spec.height))
    coverage = polygon_area(points[:4]) / max(1.0, width * height)
    inside = sum(1 for x, y in points[:4] if 0.0 <= x <= width and 0.0 <= y <= height) / 4.0
    xs = [point[0] for point in points[:4]]
    ys = [point[1] for point in points[:4]]
    spread_x = (max(xs) - min(xs)) / width
    spread_y = (max(ys) - min(ys)) / height
    coverage_score = min(1.0, coverage / max(min_field_coverage, 1e-6))
    spread_score = min(1.0, (spread_x + spread_y) / 1.25)
    confidence = 0.15 + 0.45 * coverage_score + 0.25 * inside + 0.15 * spread_score
    if inside < 1.0:
        confidence *= 0.75
    return round(max(0.0, min(0.95, confidence)), 6)


def _field_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [row for row in rows if str(row.get("class_name", "")) == "green_soccer_field"]


def _bbox_from_field_rows(rows: list[dict[str, Any]], spec: ClipSpatialSpec) -> tuple[float, float, float, float] | None:
    field_rows = _field_rows(rows)
    if not field_rows:
        return None
    x1 = _clip(_median([float(row["bbox_x1"]) for row in field_rows]), 0.0, float(spec.width))
    y1 = _clip(_median([float(row["bbox_y1"]) for row in field_rows]), 0.0, float(spec.height))
    x2 = _clip(_median([float(row["bbox_x2"]) for row in field_rows]), 0.0, float(spec.width))
    y2 = _clip(_median([float(row["bbox_y2"]) for row in field_rows]), 0.0, float(spec.height))
    if x2 <= x1 or y2 <= y1:
        return None
    return x1, y1, x2, y2


def build_calibration_from_tracks(
    clip_id: str,
    rows: list[dict[str, Any]],
    spec: ClipSpatialSpec,
    min_field_confidence: float = 0.55,
    min_field_coverage: float = 0.35,
) -> ClipCalibration:
    bbox = _bbox_from_field_rows(rows, spec)
    field_rows = _field_rows(rows)
    if bbox is None or not field_rows:
        return ClipCalibration(
            clip_id=clip_id,
            calibration_id=f"{clip_id}_fallback_v0.1",
            method="fallback_no_field_bbox",
            status="fallback",
            confidence=0.0,
            image_width=spec.width,
            image_height=spec.height,
            image_points=(),
            field_points=FIELD_POINTS,
            homography=None,
            notes="No green_soccer_field bbox was available; rows will use image extent fallback.",
        )

    x1, y1, x2, y2 = bbox
    image_points = ((x1, y1), (x2, y1), (x2, y2), (x1, y2))
    homography = solve_homography(image_points, FIELD_POINTS)
    mean_confidence = sum(float(row.get("confidence", 0.0)) for row in field_rows) / len(field_rows)
    coverage = ((x2 - x1) * (y2 - y1)) / max(1.0, float(spec.width * spec.height))
    confidence = max(0.0, min(0.99, 0.7 * mean_confidence + 0.3 * min(1.0, coverage / max(min_field_coverage, 1e-6))))
    status = "usable" if mean_confidence >= min_field_confidence and coverage >= min_field_coverage else "fallback"
    method = "field_bbox_homography_seed" if status == "usable" else "field_bbox_below_threshold"
    notes = (
        f"Median green field bbox from {len(field_rows)} rows; "
        f"mean confidence {mean_confidence:.3f}, image coverage {coverage:.3f}."
    )
    return ClipCalibration(
        clip_id=clip_id,
        calibration_id=f"{clip_id}_field_bbox_homography_v0.1",
        method=method,
        status=status,
        confidence=round(confidence, 6),
        image_width=spec.width,
        image_height=spec.height,
        image_points=image_points,
        field_points=FIELD_POINTS,
        homography=homography if status == "usable" else None,
        notes=notes,
    )


def transform_point_with_calibration(
    x: float,
    y: float,
    calibration: ClipCalibration,
    edge_tolerance: float = 0.08,
) -> tuple[float, float, str]:
    if calibration.usable and calibration.homography is not None:
        x_norm, y_norm = apply_homography_point(calibration.homography, x, y)
        if -edge_tolerance <= x_norm <= 1.0 + edge_tolerance and -edge_tolerance <= y_norm <= 1.0 + edge_tolerance:
            status = "rectified"
        else:
            status = "rectified_out_of_bounds"
        return _clip(x_norm), _clip(y_norm), status

    x_norm = _clip(float(x) / max(1.0, float(calibration.image_width)))
    y_norm = _clip(float(y) / max(1.0, float(calibration.image_height)))
    return x_norm, y_norm, "fallback_image_normalized"


def track_quality(row: dict[str, Any], calibration_status: str) -> str:
    class_name = str(row.get("class_name", ""))
    confidence = float(row.get("confidence", 0.0) or 0.0)
    if class_name == "green_soccer_field":
        return "field_reference"
    if calibration_status != "rectified":
        return "low"
    if confidence >= 0.8:
        return "usable"
    if confidence >= 0.5:
        return "provisional"
    return "low_confidence"


def rectify_track_rows(
    clip_id: str,
    rows: list[dict[str, Any]],
    spec: ClipSpatialSpec,
    calibration: ClipCalibration,
    field_model: FieldModel | None = None,
) -> list[dict[str, Any]]:
    model = field_model or FieldModel()
    result: list[dict[str, Any]] = []
    for row in rows:
        x = float(row.get("x", 0.0) or 0.0)
        y = float(row.get("y", 0.0) or 0.0)
        x_norm, y_norm, calibration_status = transform_point_with_calibration(x, y, calibration)
        quality = track_quality(row, calibration_status)
        notes = "green field reference row" if str(row.get("class_name", "")) == "green_soccer_field" else ""
        if calibration_status != "rectified":
            notes = "unreliable transform; fallback or clipped normalized point"
        result.append(
            {
                "clip_id": clip_id,
                "frame": int(row["frame"]),
                "time_sec": round(int(row["frame"]) / spec.fps, 3) if spec.fps > 0 else 0.0,
                "track_id": row.get("track_id", ""),
                "source_track_id": row.get("track_id", ""),
                "class_name": row.get("class_name", ""),
                "team": row.get("team", "unknown") or "unknown",
                "x": round(x, 6),
                "y": round(y, 6),
                "bbox_x1": round(float(row.get("bbox_x1", 0.0) or 0.0), 6),
                "bbox_y1": round(float(row.get("bbox_y1", 0.0) or 0.0), 6),
                "bbox_x2": round(float(row.get("bbox_x2", 0.0) or 0.0), 6),
                "bbox_y2": round(float(row.get("bbox_y2", 0.0) or 0.0), 6),
                "confidence": round(float(row.get("confidence", 0.0) or 0.0), 6),
                "x_norm": round(x_norm, 6),
                "y_norm": round(y_norm, 6),
                "zone": normalized_zone(x_norm, y_norm, model.zone_axis),
                "calibration_id": calibration.calibration_id,
                "calibration_status": calibration_status,
                "calibration_confidence": round(calibration.confidence, 6),
                "track_quality": quality,
                "notes": notes,
            }
        )
    return result


def write_calibration_json(
    path: str | Path,
    field_model: FieldModel,
    calibrations: Iterable[ClipCalibration],
) -> None:
    payload = {
        "rule_version": RULE_VERSION,
        "field_model": field_model.to_dict(),
        "clips": {calibration.clip_id: calibration.to_dict() for calibration in calibrations},
    }
    Path(path).write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")


def write_level3_tracks(path: str | Path, rows: list[dict[str, Any]]) -> None:
    write_csv_artifact(path, "level3_tracks.csv", rows)


def summarize_rectified_tracks(rows: list[dict[str, Any]], calibrations: dict[str, ClipCalibration]) -> list[dict[str, Any]]:
    by_clip: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_clip[str(row["clip_id"])].append(row)

    summaries: list[dict[str, Any]] = []
    for clip_id, clip_rows in sorted(by_clip.items()):
        calibration = calibrations[clip_id]
        statuses = Counter(str(row["calibration_status"]) for row in clip_rows)
        qualities = Counter(str(row["track_quality"]) for row in clip_rows)
        xs = [float(row["x_norm"]) for row in clip_rows]
        ys = [float(row["y_norm"]) for row in clip_rows]
        summaries.append(
            {
                "clip_id": clip_id,
                "rows": len(clip_rows),
                "frames": len({int(row["frame"]) for row in clip_rows}),
                "tracks": len({str(row["track_id"]) for row in clip_rows}),
                "classes": "|".join(sorted({str(row["class_name"]) for row in clip_rows})),
                "calibration_id": calibration.calibration_id,
                "calibration_status": calibration.status,
                "calibration_confidence": round(calibration.confidence, 6),
                "rectified_rows": statuses.get("rectified", 0),
                "fallback_rows": sum(count for status, count in statuses.items() if status.startswith("fallback")),
                "out_of_bounds_rows": statuses.get("rectified_out_of_bounds", 0),
                "usable_rows": qualities.get("usable", 0),
                "provisional_rows": qualities.get("provisional", 0),
                "x_norm_min": round(min(xs), 6) if xs else "",
                "x_norm_max": round(max(xs), 6) if xs else "",
                "y_norm_min": round(min(ys), 6) if ys else "",
                "y_norm_max": round(max(ys), 6) if ys else "",
            }
        )
    return summaries


def write_spatial_validation_csv(path: str | Path, rows: list[dict[str, Any]]) -> None:
    fieldnames = [
        "clip_id",
        "rows",
        "frames",
        "tracks",
        "classes",
        "calibration_id",
        "calibration_status",
        "calibration_confidence",
        "rectified_rows",
        "fallback_rows",
        "out_of_bounds_rows",
        "usable_rows",
        "provisional_rows",
        "x_norm_min",
        "x_norm_max",
        "y_norm_min",
        "y_norm_max",
    ]
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def compare_calibrations(
    automatic_calibrations: dict[str, ClipCalibration],
    selected_calibrations: dict[str, ClipCalibration],
    manual_clip_ids: Iterable[str] = (),
) -> list[dict[str, Any]]:
    manual_set = set(manual_clip_ids)
    rows: list[dict[str, Any]] = []
    for clip_id in sorted(selected_calibrations):
        selected = selected_calibrations[clip_id]
        automatic = automatic_calibrations.get(clip_id)
        deltas = _corner_deltas(automatic, selected) if automatic else []
        rows.append(
            {
                "clip_id": clip_id,
                "method_used": "manual" if clip_id in manual_set else "automatic",
                "selected_calibration_id": selected.calibration_id,
                "selected_method": selected.method,
                "selected_status": selected.status,
                "selected_confidence": round(selected.confidence, 6),
                "automatic_calibration_id": automatic.calibration_id if automatic else "",
                "automatic_method": automatic.method if automatic else "",
                "automatic_status": automatic.status if automatic else "",
                "automatic_confidence": round(automatic.confidence, 6) if automatic else "",
                "corner_mean_delta_px": round(sum(deltas) / len(deltas), 6) if deltas else "",
                "corner_max_delta_px": round(max(deltas), 6) if deltas else "",
                "manual_points": len(selected.image_points) if clip_id in manual_set else 0,
                "notes": "manual calibration overrides automatic seed" if clip_id in manual_set else "automatic calibration used",
            }
        )
    return rows


def write_calibration_comparison_csv(path: str | Path, rows: list[dict[str, Any]]) -> None:
    fieldnames = [
        "clip_id",
        "method_used",
        "selected_calibration_id",
        "selected_method",
        "selected_status",
        "selected_confidence",
        "automatic_calibration_id",
        "automatic_method",
        "automatic_status",
        "automatic_confidence",
        "corner_mean_delta_px",
        "corner_max_delta_px",
        "manual_points",
        "notes",
    ]
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def _corner_deltas(reference: ClipCalibration | None, candidate: ClipCalibration) -> list[float]:
    if reference is None or len(reference.image_points) < 4 or len(candidate.image_points) < 4:
        return []
    return [
        float(np.hypot(candidate_point[0] - reference_point[0], candidate_point[1] - reference_point[1]))
        for reference_point, candidate_point in zip(reference.image_points[:4], candidate.image_points[:4])
    ]


def draw_minimap_base(path: str | Path, field_model: FieldModel | None = None, title: str = "Mini-mapa base Nivel 3") -> None:
    model = field_model or FieldModel()
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(5, 7))
    _draw_pitch(ax, model)
    ax.set_title(title)
    fig.tight_layout()
    fig.savefig(output, dpi=160)
    plt.close(fig)


def draw_minimap_tracks(
    rows: list[dict[str, Any]],
    path: str | Path,
    field_model: FieldModel | None = None,
    max_labels_per_clip: int = 12,
) -> None:
    model = field_model or FieldModel()
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    by_clip: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_clip[str(row["clip_id"])].append(row)

    clip_ids = sorted(by_clip)
    if not clip_ids:
        draw_minimap_base(output, model, title="Mini-mapa Nivel 3 sin tracks")
        return

    fig_width = max(5.0, 5.0 * len(clip_ids))
    fig, axes = plt.subplots(1, len(clip_ids), figsize=(fig_width, 7), squeeze=False)
    palette = ["#1f77b4", "#d62728", "#2ca02c", "#9467bd", "#ff7f0e", "#17becf", "#8c564b", "#e377c2"]
    for index, clip_id in enumerate(clip_ids):
        ax = axes[0][index]
        _draw_pitch(ax, model)
        ax.set_title(f"{clip_id} tracks rectificados")
        clip_rows = [row for row in by_clip[clip_id] if str(row.get("class_name", "")) != "green_soccer_field"]
        tracks = sorted({str(row["track_id"]) for row in clip_rows})
        for track_index, track_id in enumerate(tracks):
            track_rows = sorted((row for row in clip_rows if str(row["track_id"]) == track_id), key=lambda item: int(item["frame"]))
            if not track_rows:
                continue
            class_name = str(track_rows[0].get("class_name", ""))
            if class_name == "ball":
                color = "#111111"
                marker = "o"
                linewidth = 2.0
                markersize = 3.5
            else:
                color = palette[track_index % len(palette)]
                marker = "."
                linewidth = 1.3
                markersize = 2.5
            xs = [float(row["x_norm"]) for row in track_rows]
            ys = [float(row["y_norm"]) for row in track_rows]
            ax.plot(xs, ys, color=color, linewidth=linewidth, marker=marker, markersize=markersize, label=track_id)
            if track_index < max_labels_per_clip:
                label_x = _clip(xs[-1], 0.02, 0.92)
                label_y = _clip(ys[-1], 0.03, 0.97)
                ax.text(label_x, label_y, track_id.replace("_bt_", "_"), fontsize=6, color=color)
    fig.tight_layout(pad=1.1)
    fig.savefig(output, dpi=160)
    plt.close(fig)


def _draw_pitch(ax: Any, model: FieldModel) -> None:
    ax.set_facecolor("#e9f4ea")
    ax.add_patch(plt.Rectangle((model.x_min, model.y_min), model.x_max - model.x_min, model.y_max - model.y_min, fill=False, lw=1.8, ec="#2f6f4f"))
    for y in (1.0 / 3.0, 2.0 / 3.0, 0.5):
        ax.axhline(y, color="#7aa37d", lw=0.8, ls="--" if y != 0.5 else "-")
    goal_start = 0.5 - model.goal_width_norm / 2
    goal_end = 0.5 + model.goal_width_norm / 2
    ax.plot([goal_start, goal_end], [0.0, 0.0], color="#2f6f4f", lw=3)
    ax.plot([goal_start, goal_end], [1.0, 1.0], color="#2f6f4f", lw=3)
    ax.scatter([0.5], [0.5], s=18, color="#2f6f4f")
    ax.set_xlim(-0.04, 1.04)
    ax.set_ylim(1.04, -0.04)
    ax.set_xlabel("x_norm")
    ax.set_ylabel("y_norm")
    ax.grid(alpha=0.18)
    ax.set_aspect("equal", adjustable="box")
