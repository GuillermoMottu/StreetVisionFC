from __future__ import annotations

import argparse
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from futbotmx.live_playback import DEFAULT_EXPERIMENT_DIR, run_smoke_test, serve_live_playback_app


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the FutBotMX live playback app.")
    parser.add_argument("--config", default="configs/default.yaml")
    parser.add_argument("--experiment", default=str(DEFAULT_EXPERIMENT_DIR))
    parser.add_argument("--clip-id", default="video_595")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8766)
    parser.add_argument("--smoke-test", action="store_true", help="Write lightweight playback evidence and exit.")
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[1]
    config_path = Path(args.config)
    output_dir = Path(args.experiment)
    if args.smoke_test:
        context = run_smoke_test(root, config_path, output_dir, clip_id=args.clip_id)
        summary = context["summary"]
        print(
            "Wrote live playback evidence to "
            f"{output_dir} ({summary['track_rows']} tracks, {summary['event_count']} events, "
            f"{summary['highlight_count']} highlights)"
        )
        return 0 if summary["validation_errors"] == 0 else 1
    serve_live_playback_app(root, config_path, output_dir, args.host, args.port, clip_id=args.clip_id)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
