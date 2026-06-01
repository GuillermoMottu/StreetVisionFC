from __future__ import annotations

import argparse
import csv
from collections import Counter
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from futbotmx.io.detections import deduplicate_detections, load_detections, save_detections


def parse_top_k(values: list[str] | None) -> dict[str, int]:
    result: dict[str, int] = {}
    for value in values or []:
        if "=" not in value:
            raise ValueError("--top-k values must use class_name=count")
        class_name, count_text = value.split("=", 1)
        result[class_name.strip()] = int(count_text)
    return result


def count_by_class(frames) -> Counter[str]:
    counts: Counter[str] = Counter()
    for frame in frames:
        counts.update(detection.class_name for detection in frame.detections)
    return counts


def write_metrics(before, after, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    before_counts = count_by_class(before)
    after_counts = count_by_class(after)
    class_names = sorted(set(before_counts) | set(after_counts))
    with output_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["class_name", "before", "after", "removed"],
            lineterminator="\n",
        )
        writer.writeheader()
        for class_name in class_names:
            before_count = before_counts[class_name]
            after_count = after_counts[class_name]
            writer.writerow(
                {
                    "class_name": class_name,
                    "before": before_count,
                    "after": after_count,
                    "removed": before_count - after_count,
                }
            )


def main() -> int:
    parser = argparse.ArgumentParser(description="Clean detections with per-class NMS and optional top-k.")
    parser.add_argument("--detections", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--metrics", default=None)
    parser.add_argument("--iou-threshold", type=float, default=0.6)
    parser.add_argument("--top-k", action="append", default=None, help="Per-class limit, e.g. ball=1")
    args = parser.parse_args()

    frames = load_detections(args.detections)
    top_k = parse_top_k(args.top_k)
    cleaned = deduplicate_detections(frames, iou_threshold=args.iou_threshold, top_k_by_class=top_k)
    save_detections(cleaned, args.output)
    if args.metrics:
        write_metrics(frames, cleaned, Path(args.metrics))

    removed = sum(len(frame.detections) for frame in frames) - sum(len(frame.detections) for frame in cleaned)
    print(f"Wrote cleaned detections to {args.output}")
    print(f"Removed detections: {removed}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
