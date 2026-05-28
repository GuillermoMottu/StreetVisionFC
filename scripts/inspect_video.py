from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from futbotmx.config import load_config
from futbotmx.video_io import inspect_video


def main() -> int:
    parser = argparse.ArgumentParser(description="Inspect local video metadata.")
    parser.add_argument("--config", default="configs/default.yaml")
    parser.add_argument("--video", default=None)
    parser.add_argument("--output", default=None)
    args = parser.parse_args()

    config = load_config(args.config)
    video_path = args.video or config["video"]["input_path"]
    metadata = inspect_video(video_path)
    payload = metadata.to_dict()
    print(json.dumps(payload, indent=2))
    if args.output:
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
