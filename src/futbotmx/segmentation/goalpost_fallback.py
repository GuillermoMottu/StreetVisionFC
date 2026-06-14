"""
Geometric goalpost fallback for FutBotMX.

SAM 3 cannot reliably detect robot-soccer goalposts with any tested text prompt
(confirmed: 0 detections across 6 frames at threshold=0.1 for 5 prompts).
This module provides a calibration-based geometric approximation as an explicit
fallback — NOT equivalent to SAM 3 pixel-level segmentation.

The goal positions are derived from the existing field_calibration.json spatial
model, which defines goals at y_norm=0 (top) and y_norm=1 (bottom), centered
horizontally at x_norm=0.39–0.61 (22% of field width).
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from futbotmx.io.detections import Detection, FrameDetections


DETECTION_METHOD = "geometric_fallback"
GOALPOST_CLASS = "goalpost"

# Default field model goal parameters (from field_calibration.json)
_DEFAULT_GOAL_X_NORM_START = 0.39
_DEFAULT_GOAL_X_NORM_END = 0.61
_GOAL_HEIGHT_NORM = 0.04  # estimated ~4% of field height per goalpost strip


@dataclass(frozen=True)
class ClipGeometry:
    """Image coordinates of the visible field rectangle for one clip."""
    image_width: int
    image_height: int
    field_x_min: float
    field_y_min: float
    field_x_max: float
    field_y_max: float


# Per-clip geometry derived from existing calibration experiments.
# video_836 uses the same camera/ROI as video_667 (confirmed in default.yaml).
_CLIP_GEOMETRY: dict[str, ClipGeometry] = {
    "video_595": ClipGeometry(1344, 1792, 2.2, 486.5, 1342.6, 1788.5),
    "video_667": ClipGeometry(1360, 1808, 3.8, 685.8, 1360.0, 1807.0),
    "video_836": ClipGeometry(1360, 1808, 0.0, 620.0, 1360.0, 1808.0),
    "video_480": ClipGeometry(1360, 1808, 0.0, 620.0, 1360.0, 1808.0),
}


def detect_goalposts(
    frame_index: int,
    clip_id: str = "video_836",
    goal_x_start_norm: float = _DEFAULT_GOAL_X_NORM_START,
    goal_x_end_norm: float = _DEFAULT_GOAL_X_NORM_END,
    goal_height_norm: float = _GOAL_HEIGHT_NORM,
) -> FrameDetections:
    """
    Return geometric goalpost detections for a single frame.

    These are NOT SAM 3 segmentation results. They are bounding-box estimates
    derived from the spatial calibration model. mask_path is always None
    because no pixel-level mask is available.

    Returns two detections: top_goal and bottom_goal.
    """
    geom = _CLIP_GEOMETRY.get(clip_id)
    if geom is None:
        available = list(_CLIP_GEOMETRY.keys())
        raise ValueError(
            f"No geometry for clip_id={clip_id!r}. Available: {available}. "
            "Add an entry to goalpost_fallback._CLIP_GEOMETRY."
        )

    field_w = geom.field_x_max - geom.field_x_min
    field_h = geom.field_y_max - geom.field_y_min

    gx0 = geom.field_x_min + goal_x_start_norm * field_w
    gx1 = geom.field_x_min + goal_x_end_norm * field_w
    goal_h_px = goal_height_norm * field_h

    top_goal = Detection(
        class_name=GOALPOST_CLASS,
        bbox=(gx0, geom.field_y_min, gx1, geom.field_y_min + goal_h_px),
        centroid=((gx0 + gx1) / 2, geom.field_y_min + goal_h_px / 2),
        confidence=0.0,  # 0.0 signals "not from model inference"
        mask_path=None,
    )
    bottom_goal = Detection(
        class_name=GOALPOST_CLASS,
        bbox=(gx0, geom.field_y_max - goal_h_px, gx1, geom.field_y_max),
        centroid=((gx0 + gx1) / 2, geom.field_y_max - goal_h_px / 2),
        confidence=0.0,
        mask_path=None,
    )

    return FrameDetections(frame=frame_index, detections=(top_goal, bottom_goal))


def detect_goalposts_multi_frame(
    frame_indices: list[int],
    clip_id: str = "video_836",
    **kwargs: Any,
) -> list[FrameDetections]:
    return [
        detect_goalposts(frame_index, clip_id=clip_id, **kwargs)
        for frame_index in frame_indices
    ]
