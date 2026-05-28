from __future__ import annotations

import csv
import math
from dataclasses import asdict, dataclass
from pathlib import Path

from futbotmx.io.detections import FrameDetections


@dataclass(frozen=True)
class TrackRow:
    frame: int
    track_id: str
    class_name: str
    x: float
    y: float
    bbox_x1: float
    bbox_y1: float
    bbox_x2: float
    bbox_y2: float
    confidence: float
    team: str = "unknown"


def _distance(a: tuple[float, float], b: tuple[float, float]) -> float:
    return math.hypot(a[0] - b[0], a[1] - b[1])


def _team_for_class(class_name: str) -> str:
    if class_name.startswith("ally"):
        return "ally"
    if class_name.startswith("opponent"):
        return "opponent"
    return "neutral"


def track_detections(
    frames: list[FrameDetections],
    max_distance_px: float = 80.0,
    max_lost_frames: int = 15,
) -> list[TrackRow]:
    active: dict[str, tuple[str, tuple[float, float], int]] = {}
    counters: dict[str, int] = {}
    rows: list[TrackRow] = []

    for frame in sorted(frames, key=lambda item: item.frame):
        used_track_ids: set[str] = set()
        for detection in frame.detections:
            candidates = [
                (track_id, _distance(detection.centroid, centroid))
                for track_id, (class_name, centroid, last_frame) in active.items()
                if class_name == detection.class_name
                and track_id not in used_track_ids
                and frame.frame - last_frame <= max_lost_frames
            ]
            track_id = None
            if candidates:
                best_id, best_distance = min(candidates, key=lambda item: item[1])
                if best_distance <= max_distance_px:
                    track_id = best_id

            if track_id is None:
                counters[detection.class_name] = counters.get(detection.class_name, 0) + 1
                track_id = f"{detection.class_name}_{counters[detection.class_name]:02d}"

            used_track_ids.add(track_id)
            active[track_id] = (detection.class_name, detection.centroid, frame.frame)
            x1, y1, x2, y2 = detection.bbox
            rows.append(
                TrackRow(
                    frame=frame.frame,
                    track_id=track_id,
                    class_name=detection.class_name,
                    x=detection.centroid[0],
                    y=detection.centroid[1],
                    bbox_x1=x1,
                    bbox_y1=y1,
                    bbox_x2=x2,
                    bbox_y2=y2,
                    confidence=detection.confidence,
                    team=_team_for_class(detection.class_name),
                )
            )
    return rows


def write_tracks_csv(rows: list[TrackRow], path: str | Path) -> None:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(asdict(rows[0]).keys()) if rows else list(TrackRow.__dataclass_fields__.keys())
    with output_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(asdict(row))
