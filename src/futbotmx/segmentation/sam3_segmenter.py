from __future__ import annotations

from pathlib import Path

from futbotmx.io.detections import FrameDetections


class SAM3UnavailableError(RuntimeError):
    """Raised when SAM 3 has not been installed on the GPU machine."""


class SAM3Segmenter:
    def __init__(self, checkpoint_path: str | None = None) -> None:
        self.checkpoint_path = checkpoint_path

    def segment_video(self, video_path: str | Path, frame_indices: list[int]) -> list[FrameDetections]:
        raise SAM3UnavailableError(
            "SAM 3 inference must be installed and validated on the MSI laptop. "
            "This desktop wrapper defines the interface but does not run heavy inference."
        )
