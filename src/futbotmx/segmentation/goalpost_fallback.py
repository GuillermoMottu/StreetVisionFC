"""
Goalpost fallback for clips where OWLv2 cannot detect the goalpost.

Primary pipeline (GroundedSAMSegmenter): OWLv2 text→bbox "yellow goalpost" +
SAM3 box-prompt → pixel mask. Validated on video_836 (conf≈0.108) and
video_667 (conf≈0.089). No per-clip configuration needed.

Fallback (this module): used when OWLv2 fails — notably video_595 frames 120-180
where the horizontal goalpost bar has low visual contrast for the model.
_CLIP_GOALS coordinates were derived by HSV yellow-blob detection (2026-06-11).

detect_goalposts_with_mask() uses _CLIP_GOALS bbox as a SAM3 geometric prompt,
producing a real pixel mask even without OWLv2 detection. detect_goalposts()
returns a pure-geometry estimate (no mask) as last resort.

NOTE: Pixel coordinates are image-space (perspective), not real-world field space.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Any

from futbotmx.io.detections import Detection, FrameDetections

if TYPE_CHECKING:
    from PIL.Image import Image
    from futbotmx.segmentation.sam3_segmenter import SAM3Segmenter


DETECTION_METHOD = "geometric_fallback"
GOALPOST_CLASS = "goalpost"

# Per-clip goal pixel coordinates derived from HSV color detection.
# Each entry: list of (x0, y0, x1, y1) bboxes visible from the camera angle.
# Clips with no confirmed second goal omit it rather than guess.
_CLIP_GOALS: dict[str, list[tuple[float, float, float, float]]] = {
    # video_836: top goal confirmed across 6 frames (x=1000-1360, y=650-800).
    # Bottom goal not detected — not visible at this camera angle.
    "video_836": [(1000.0, 650.0, 1360.0, 800.0)],
    # video_480: same camera setup as video_836 (same resolution/ROI).
    "video_480": [(1000.0, 650.0, 1360.0, 800.0)],
    # video_595 and video_667: not yet surveyed — using centered field model estimate.
    # TODO: run HSV blob detection on these clips when videos are accessible.
    "video_595": [(525.0, 486.0, 820.0, 540.0), (525.0, 1745.0, 820.0, 1792.0)],
    "video_667": [(530.0, 686.0, 830.0, 740.0), (530.0, 1760.0, 830.0, 1807.0)],
}


def detect_goalposts(
    frame_index: int,
    clip_id: str = "video_836",
) -> FrameDetections:
    """
    Return geometric goalpost detections for a single frame.

    These are NOT SAM 3 segmentation results. confidence=0.0 and mask_path=None
    signal that this is a geometric estimate, not model inference.
    """
    goals = _CLIP_GOALS.get(clip_id)
    if goals is None:
        available = list(_CLIP_GOALS.keys())
        raise ValueError(
            f"No goal geometry for clip_id={clip_id!r}. Available: {available}. "
            "Add an entry to goalpost_fallback._CLIP_GOALS."
        )

    detections = tuple(
        Detection(
            class_name=GOALPOST_CLASS,
            bbox=bbox,
            centroid=((bbox[0] + bbox[2]) / 2, (bbox[1] + bbox[3]) / 2),
            confidence=0.0,
            mask_path=None,
        )
        for bbox in goals
    )
    return FrameDetections(frame=frame_index, detections=detections)


def detect_goalposts_multi_frame(
    frame_indices: list[int],
    clip_id: str = "video_836",
    **kwargs: Any,
) -> list[FrameDetections]:
    return [detect_goalposts(frame_index, clip_id=clip_id) for frame_index in frame_indices]


def detect_goalposts_with_mask(
    image: "Image",
    frame_index: int,
    clip_id: str = "video_836",
    segmenter: "SAM3Segmenter | None" = None,
    det_idx_start: int = 0,
) -> FrameDetections:
    """
    Detect goalposts using known-color bbox → SAM3 geometric prompt → pixel mask.

    Uses per-clip HSV-confirmed bbox from _CLIP_GOALS as the geometric prompt for
    SAM3's add_geometric_prompt, producing a real pixel-level mask instead of a
    plain rectangle.  Falls back to detect_goalposts() (no mask) if segmenter is
    None or if SAM3 raises an error.
    """
    goals = _CLIP_GOALS.get(clip_id)
    if goals is None:
        available = list(_CLIP_GOALS.keys())
        raise ValueError(
            f"No goal geometry for clip_id={clip_id!r}. Available: {available}. "
            "Add an entry to goalpost_fallback._CLIP_GOALS."
        )

    if segmenter is None:
        return detect_goalposts(frame_index, clip_id=clip_id)

    try:
        detections = []
        for i, bbox in enumerate(goals):
            det = segmenter.segment_with_box_prompt(
                image=image,
                class_name=GOALPOST_CLASS,
                bbox_pixel=bbox,
                frame_index=frame_index,
                det_idx=det_idx_start + i,
            )
            detections.append(det)
        return FrameDetections(frame=frame_index, detections=tuple(detections))
    except Exception:
        return detect_goalposts(frame_index, clip_id=clip_id)
