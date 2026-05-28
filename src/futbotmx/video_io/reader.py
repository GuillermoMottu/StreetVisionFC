from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path

import cv2


@dataclass(frozen=True)
class VideoMetadata:
    path: str
    fps: float
    width: int
    height: int
    frame_count: int
    duration_sec: float

    def to_dict(self) -> dict[str, float | int | str]:
        return asdict(self)


def inspect_video(path: str | Path) -> VideoMetadata:
    video_path = Path(path)
    if not video_path.exists():
        raise FileNotFoundError(f"Video not found: {video_path}")

    capture = cv2.VideoCapture(str(video_path))
    try:
        if not capture.isOpened():
            raise ValueError(f"Could not open video: {video_path}")

        fps = float(capture.get(cv2.CAP_PROP_FPS) or 0.0)
        frame_count = int(capture.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
        width = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
        height = int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)
        duration_sec = frame_count / fps if fps > 0 else 0.0
        return VideoMetadata(
            path=str(video_path),
            fps=fps,
            width=width,
            height=height,
            frame_count=frame_count,
            duration_sec=duration_sec,
        )
    finally:
        capture.release()


def extract_frame(path: str | Path, frame_index: int):
    video_path = Path(path)
    capture = cv2.VideoCapture(str(video_path))
    try:
        if not capture.isOpened():
            raise ValueError(f"Could not open video: {video_path}")
        capture.set(cv2.CAP_PROP_POS_FRAMES, frame_index)
        ok, frame = capture.read()
        if not ok:
            raise ValueError(f"Could not read frame {frame_index} from {video_path}")
        return frame
    finally:
        capture.release()
