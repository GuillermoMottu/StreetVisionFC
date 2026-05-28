from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
import sys

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from futbotmx.video_io import inspect_video


def make_video(path: Path, frames: int = 12, size: tuple[int, int] = (160, 90), fps: float = 15.0) -> None:
    writer = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"mp4v"), fps, size)
    if not writer.isOpened():
        raise RuntimeError("Could not create synthetic video")
    for index in range(frames):
        frame = np.zeros((size[1], size[0], 3), dtype=np.uint8)
        cv2.circle(frame, (20 + index * 4, 45), 6, (0, 255, 255), -1)
        writer.write(frame)
    writer.release()


class VideoIOTests(unittest.TestCase):
    def test_inspect_video_returns_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            video_path = Path(tmp) / "sample.mp4"
            make_video(video_path)

            metadata = inspect_video(video_path)

            self.assertEqual(metadata.width, 160)
            self.assertEqual(metadata.height, 90)
            self.assertEqual(metadata.frame_count, 12)
            self.assertGreater(metadata.duration_sec, 0)


if __name__ == "__main__":
    unittest.main()
