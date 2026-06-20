from __future__ import annotations

import argparse
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from futbotmx.config import load_config
from futbotmx.io.detections import load_detections
from futbotmx.tracking import ByteTrackUnavailableError, run_bytetrack, track_detections, write_tracks_csv


def main() -> int:
    parser = argparse.ArgumentParser(description="Create tracks.csv from normalized detections.")
    parser.add_argument("--config", default="configs/default.yaml")
    parser.add_argument("--detections", required=True)
    parser.add_argument("--output", default="outputs/tracking/tracks.csv")
    parser.add_argument("--tracker", choices=["auto", "bytetrack", "simple"], default="auto")
    parser.add_argument("--fps", type=float, default=30.0)
    parser.add_argument("--max-distance-px", type=float, default=80.0)
    parser.add_argument("--max-lost-frames", type=int, default=15)
    parser.add_argument("--bytetrack-activation-threshold", type=float, default=None)
    parser.add_argument("--bytetrack-lost-buffer", type=int, default=None)
    parser.add_argument("--bytetrack-matching-threshold", type=float, default=None)
    args = parser.parse_args()

    frames = load_detections(args.detections)
    config = load_config(args.config)
    tracking_config = config.get("tracking", {})
    bytetrack_config = tracking_config.get("bytetrack", {}) if isinstance(tracking_config, dict) else {}
    configured_tracker = str(tracking_config.get("method", "simple")) if isinstance(tracking_config, dict) else "simple"
    tracker = configured_tracker if args.tracker == "auto" else args.tracker

    rows = []
    tracker_used = "simple"
    if tracker == "bytetrack":
        try:
            rows = run_bytetrack(
                frames,
                frame_rate=args.fps,
                track_activation_threshold=float(
                    args.bytetrack_activation_threshold
                    if args.bytetrack_activation_threshold is not None
                    else bytetrack_config.get("track_activation_threshold", 0.25)
                ),
                lost_track_buffer=int(
                    args.bytetrack_lost_buffer
                    if args.bytetrack_lost_buffer is not None
                    else bytetrack_config.get("lost_track_buffer", 30)
                ),
                minimum_matching_threshold=float(
                    args.bytetrack_matching_threshold
                    if args.bytetrack_matching_threshold is not None
                    else bytetrack_config.get("minimum_matching_threshold", 0.8)
                ),
            )
            tracker_used = "bytetrack"
        except ByteTrackUnavailableError as exc:
            print(f"WARN: ByteTrack unavailable ({exc}); falling back to simple centroid tracker.", file=sys.stderr)
            rows = track_detections(frames, max_distance_px=args.max_distance_px, max_lost_frames=args.max_lost_frames)
    else:
        rows = track_detections(frames, max_distance_px=args.max_distance_px, max_lost_frames=args.max_lost_frames)

    write_tracks_csv(rows, args.output)
    print(f"Wrote {len(rows)} track rows to {args.output} using {tracker_used}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
