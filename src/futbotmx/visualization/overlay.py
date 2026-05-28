from __future__ import annotations

import csv
from pathlib import Path

import cv2

from futbotmx.video_io import extract_frame


COLORS = {
    "ball": (0, 220, 255),
    "ally_robot": (0, 180, 80),
    "opponent_robot": (30, 80, 230),
}


def write_overlay_frame(video_path: str | Path, tracks_csv: str | Path, output_path: str | Path, frame_index: int) -> None:
    frame = extract_frame(video_path, frame_index)
    frame_rows = []
    with Path(tracks_csv).open("r", newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            if int(float(row["frame"])) == frame_index:
                frame_rows.append(row)

    for row in frame_rows:
        color = COLORS.get(row["class_name"], (255, 255, 255))
        x1 = int(float(row["bbox_x1"]))
        y1 = int(float(row["bbox_y1"]))
        x2 = int(float(row["bbox_x2"]))
        y2 = int(float(row["bbox_y2"]))
        cx = int(float(row["x"]))
        cy = int(float(row["y"]))
        cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
        cv2.circle(frame, (cx, cy), 3, color, -1)
        cv2.putText(frame, row["track_id"], (x1, max(15, y1 - 6)), cv2.FONT_HERSHEY_SIMPLEX, 0.45, color, 1)

    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(output), frame)
