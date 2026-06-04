from __future__ import annotations

from collections import defaultdict

import numpy as np

from futbotmx.io.detections import FrameDetections

from .simple_tracker import TrackRow, team_for_class


class ByteTrackUnavailableError(RuntimeError):
    pass


def run_bytetrack(
    frames: list[FrameDetections],
    frame_rate: float,
    track_activation_threshold: float = 0.25,
    lost_track_buffer: int = 30,
    minimum_matching_threshold: float = 0.8,
) -> list[TrackRow]:
    try:
        import supervision as sv
    except ImportError as exc:
        raise ByteTrackUnavailableError("supervision is not installed; ByteTrack is unavailable") from exc

    class_names = sorted({detection.class_name for frame in frames for detection in frame.detections})
    trackers = {
        class_name: sv.ByteTrack(
            track_activation_threshold=track_activation_threshold,
            lost_track_buffer=lost_track_buffer,
            minimum_matching_threshold=minimum_matching_threshold,
            frame_rate=frame_rate,
            minimum_consecutive_frames=1,
        )
        for class_name in class_names
    }
    rows: list[TrackRow] = []
    for frame in sorted(frames, key=lambda item: item.frame):
        detections_by_class: dict[str, list] = defaultdict(list)
        for detection in frame.detections:
            detections_by_class[detection.class_name].append(detection)

        for class_name in class_names:
            detections = detections_by_class[class_name]
            if detections:
                xyxy = np.array([detection.bbox for detection in detections], dtype=float)
                confidence = np.array([detection.confidence for detection in detections], dtype=float)
                class_id = np.zeros(len(detections), dtype=int)
            else:
                xyxy = np.empty((0, 4), dtype=float)
                confidence = np.empty((0,), dtype=float)
                class_id = np.empty((0,), dtype=int)

            sv_detections = sv.Detections(xyxy=xyxy, confidence=confidence, class_id=class_id)
            tracked = trackers[class_name].update_with_detections(sv_detections)
            if tracked.tracker_id is None:
                continue

            for index, tracker_id in enumerate(tracked.tracker_id):
                x1, y1, x2, y2 = (float(value) for value in tracked.xyxy[index])
                rows.append(
                    TrackRow(
                        frame=frame.frame,
                        track_id=f"{class_name}_bt_{int(tracker_id):02d}",
                        class_name=class_name,
                        x=(x1 + x2) / 2,
                        y=(y1 + y2) / 2,
                        bbox_x1=x1,
                        bbox_y1=y1,
                        bbox_x2=x2,
                        bbox_y2=y2,
                        confidence=float(tracked.confidence[index]) if tracked.confidence is not None else 1.0,
                        team=team_for_class(class_name),
                    )
                )
    return rows
