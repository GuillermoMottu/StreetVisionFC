from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class Detection:
    class_name: str
    bbox: tuple[float, float, float, float]
    centroid: tuple[float, float]
    confidence: float = 1.0
    mask_path: str | None = None

    @classmethod
    def from_mapping(cls, data: dict[str, Any]) -> "Detection":
        bbox = tuple(float(value) for value in data["bbox"])
        centroid = tuple(float(value) for value in data["centroid"])
        if len(bbox) != 4:
            raise ValueError("bbox must contain 4 values")
        if len(centroid) != 2:
            raise ValueError("centroid must contain 2 values")
        return cls(
            class_name=str(data["class_name"]),
            bbox=bbox,
            centroid=centroid,
            confidence=float(data.get("confidence", 1.0)),
            mask_path=data.get("mask_path"),
        )


@dataclass(frozen=True)
class FrameDetections:
    frame: int
    detections: tuple[Detection, ...]

    @classmethod
    def from_mapping(cls, data: dict[str, Any]) -> "FrameDetections":
        return cls(
            frame=int(data["frame"]),
            detections=tuple(Detection.from_mapping(item) for item in data.get("detections", [])),
        )


def filter_detections_by_roi(
    frames: list[FrameDetections],
    roi: tuple[float, float, float, float],
) -> list[FrameDetections]:
    """Keep detections whose centroid is inside an axis-aligned ROI."""
    x1, y1, x2, y2 = roi
    if x2 < x1 or y2 < y1:
        raise ValueError("roi must be ordered as x1 y1 x2 y2")

    filtered_frames: list[FrameDetections] = []
    for frame in frames:
        kept = tuple(
            detection
            for detection in frame.detections
            if x1 <= detection.centroid[0] <= x2 and y1 <= detection.centroid[1] <= y2
        )
        filtered_frames.append(FrameDetections(frame=frame.frame, detections=kept))
    return filtered_frames


def bbox_iou(first: tuple[float, float, float, float], second: tuple[float, float, float, float]) -> float:
    x1 = max(first[0], second[0])
    y1 = max(first[1], second[1])
    x2 = min(first[2], second[2])
    y2 = min(first[3], second[3])
    intersection_width = max(0.0, x2 - x1)
    intersection_height = max(0.0, y2 - y1)
    intersection = intersection_width * intersection_height
    if intersection == 0:
        return 0.0

    first_area = max(0.0, first[2] - first[0]) * max(0.0, first[3] - first[1])
    second_area = max(0.0, second[2] - second[0]) * max(0.0, second[3] - second[1])
    union = first_area + second_area - intersection
    return intersection / union if union > 0 else 0.0


def deduplicate_detections(
    frames: list[FrameDetections],
    iou_threshold: float = 0.6,
    top_k_by_class: dict[str, int] | None = None,
) -> list[FrameDetections]:
    """Apply per-frame/per-class NMS and optional top-k selection."""
    if not 0 <= iou_threshold <= 1:
        raise ValueError("iou_threshold must be between 0 and 1")

    top_k_by_class = top_k_by_class or {}
    cleaned_frames: list[FrameDetections] = []
    for frame in frames:
        by_class: dict[str, list[Detection]] = {}
        for detection in frame.detections:
            by_class.setdefault(detection.class_name, []).append(detection)

        kept: list[Detection] = []
        for class_name in sorted(by_class):
            candidates = sorted(by_class[class_name], key=lambda item: item.confidence, reverse=True)
            class_kept: list[Detection] = []
            for candidate in candidates:
                if all(bbox_iou(candidate.bbox, existing.bbox) < iou_threshold for existing in class_kept):
                    class_kept.append(candidate)
            limit = top_k_by_class.get(class_name)
            if limit is not None:
                class_kept = class_kept[: max(0, limit)]
            kept.extend(class_kept)

        cleaned_frames.append(
            FrameDetections(
                frame=frame.frame,
                detections=tuple(sorted(kept, key=lambda item: (item.class_name, -item.confidence))),
            )
        )
    return cleaned_frames


def load_detections(path: str | Path) -> list[FrameDetections]:
    input_path = Path(path)
    with input_path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if isinstance(payload, dict):
        payload = payload.get("frames", [payload])
    return [FrameDetections.from_mapping(item) for item in payload]


def save_detections(frames: list[FrameDetections], path: str | Path) -> None:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "frames": [
            {
                "frame": frame.frame,
                "detections": [asdict(detection) for detection in frame.detections],
            }
            for frame in frames
        ]
    }
    with output_path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)
