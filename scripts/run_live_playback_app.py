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
    parser.add_argument("--video", default=None, help="Override the configured local video path.")
    parser.add_argument(
        "--inference-mode",
        choices=["precomputed", "sam3_sampling", "lightweight_detector"],
        default=None,
        help="Select the live playback inference mode.",
    )
    parser.add_argument("--sam3-stride", type=int, default=None, help="Frame stride for the SAM 3 sampling mode.")
    parser.add_argument("--lightweight-stride", type=int, default=None, help="Frame stride for the lightweight detector mode.")
    parser.add_argument("--allow-gpu", action="store_true", help="Allow GPU-gated experimental inference modes.")
    parser.add_argument("--gpu-profile", default=None, help="Hardware profile label, for example msi_gpu.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8766)
    parser.add_argument("--smoke-test", action="store_true", help="Write lightweight playback evidence and exit.")
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[1]
    config_path = Path(args.config)
    output_dir = Path(args.experiment)
    if args.smoke_test:
        context = run_smoke_test(
            root,
            config_path,
            output_dir,
            clip_id=args.clip_id,
            video_path=args.video,
            inference_mode=args.inference_mode,
            sam3_stride=args.sam3_stride,
            lightweight_stride=args.lightweight_stride,
            allow_gpu=args.allow_gpu if args.allow_gpu else None,
            gpu_profile=args.gpu_profile,
        )
        summary = context["summary"]
        print(
            "Wrote live playback evidence to "
            f"{output_dir} ({summary['track_rows']} tracks, {summary['event_count']} events, "
            f"{summary['highlight_count']} highlights)"
        )
        return 0 if summary["validation_errors"] == 0 else 1
    serve_live_playback_app(
        root,
        config_path,
        output_dir,
        args.host,
        args.port,
        clip_id=args.clip_id,
        video_path=args.video,
        inference_mode=args.inference_mode,
        sam3_stride=args.sam3_stride,
        lightweight_stride=args.lightweight_stride,
        allow_gpu=args.allow_gpu if args.allow_gpu else None,
        gpu_profile=args.gpu_profile,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
