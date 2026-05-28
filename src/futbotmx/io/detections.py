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
