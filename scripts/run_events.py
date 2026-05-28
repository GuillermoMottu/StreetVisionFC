from __future__ import annotations

import argparse
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from futbotmx.config import load_config
from futbotmx.events import detect_level1_events, write_events_json


def main() -> int:
    parser = argparse.ArgumentParser(description="Detect Level 1 FutBotMX events from tracks.csv.")
    parser.add_argument("--config", default="configs/default.yaml")
    parser.add_argument("--tracks", required=True)
    parser.add_argument("--output", default="outputs/events/events.json")
    parser.add_argument("--fps", type=float, default=30.0)
    parser.add_argument("--field-width", type=float, default=640)
    parser.add_argument("--field-height", type=float, default=360)
    args = parser.parse_args()

    config = load_config(args.config)
    events = detect_level1_events(
        args.tracks,
        fps=args.fps,
        field_width=args.field_width,
        field_height=args.field_height,
        config=config.get("events", {}),
    )
    write_events_json(events, args.output)
    print(f"Wrote {len(events)} events to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
