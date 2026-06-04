from __future__ import annotations

import csv
from pathlib import Path
from typing import Any


TRACK_NUMERIC_FIELDS = ("frame", "x", "y", "bbox_x1", "bbox_y1", "bbox_x2", "bbox_y2", "confidence")


def read_tracks_csv(path: str | Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with Path(path).open("r", newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            for key in TRACK_NUMERIC_FIELDS:
                if key in row and row[key] != "":
                    row[key] = float(row[key])
            row["frame"] = int(row["frame"])
            row.setdefault("team", "unknown")
            rows.append(row)
    return rows
