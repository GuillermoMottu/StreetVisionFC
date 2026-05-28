from __future__ import annotations

import argparse
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from futbotmx.visualization import write_heatmap, write_overlay_frame


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate lightweight FutBotMX visualizations.")
    parser.add_argument("--tracks", required=True)
    parser.add_argument("--heatmap", default="outputs/visualizations/heatmap.png")
    parser.add_argument("--width", type=int, default=640)
    parser.add_argument("--height", type=int, default=360)
    parser.add_argument("--video", default=None)
    parser.add_argument("--overlay", default=None)
    parser.add_argument("--frame", type=int, default=0)
    args = parser.parse_args()

    write_heatmap(args.tracks, args.heatmap, args.width, args.height)
    print(f"Wrote heatmap to {args.heatmap}")
    if args.video and args.overlay:
        write_overlay_frame(args.video, args.tracks, args.overlay, args.frame)
        print(f"Wrote overlay to {args.overlay}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
