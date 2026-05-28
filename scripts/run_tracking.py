from __future__ import annotations

import argparse
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from futbotmx.io.detections import load_detections
from futbotmx.tracking import track_detections, write_tracks_csv


def main() -> int:
    parser = argparse.ArgumentParser(description="Create tracks.csv from normalized detections.")
    parser.add_argument("--detections", required=True)
    parser.add_argument("--output", default="outputs/tracking/tracks.csv")
    parser.add_argument("--max-distance-px", type=float, default=80.0)
    args = parser.parse_args()

    frames = load_detections(args.detections)
    rows = track_detections(frames, max_distance_px=args.max_distance_px)
    write_tracks_csv(rows, args.output)
    print(f"Wrote {len(rows)} track rows to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
