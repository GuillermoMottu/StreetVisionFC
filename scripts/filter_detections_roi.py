from __future__ import annotations

import argparse
from collections import Counter
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from futbotmx.io.detections import filter_detections_by_roi, load_detections, save_detections


def _count_by_class(frames) -> Counter[str]:
    counts: Counter[str] = Counter()
    for frame in frames:
        counts.update(detection.class_name for detection in frame.detections)
    return counts


def main() -> int:
    parser = argparse.ArgumentParser(description="Filter normalized detections by a rectangular field ROI.")
    parser.add_argument("--detections", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument(
        "--roi",
        nargs=4,
        type=float,
        metavar=("X1", "Y1", "X2", "Y2"),
        required=True,
        help="Field ROI in pixels. Detections are kept when their centroid is inside it.",
    )
    args = parser.parse_args()

    frames = load_detections(args.detections)
    filtered = filter_detections_by_roi(frames, tuple(args.roi))
    save_detections(filtered, args.output)

    before = _count_by_class(frames)
    after = _count_by_class(filtered)
    removed_total = sum(before.values()) - sum(after.values())
    print(f"Wrote filtered detections to {args.output}")
    print(f"ROI: {tuple(args.roi)}")
    print(f"Removed detections: {removed_total}")
    for class_name in sorted(before):
        print(f"- {class_name}: {before[class_name]} -> {after[class_name]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
