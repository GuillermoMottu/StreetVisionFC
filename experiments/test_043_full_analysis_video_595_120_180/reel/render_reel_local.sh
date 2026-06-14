#!/usr/bin/env bash
set -euo pipefail
mkdir -p ../../../local_outputs/full_analysis
ffmpeg -y -f concat -safe 0 -i reel_ffmpeg_inputs.txt -vf "scale=1280:720:force_original_aspect_ratio=decrease,pad=1280:720:(ow-iw)/2:(oh-ih)/2,fps=30" -c:v libx264 -pix_fmt yuv420p ../../../local_outputs/full_analysis/video_595_120_180_reel.mp4
