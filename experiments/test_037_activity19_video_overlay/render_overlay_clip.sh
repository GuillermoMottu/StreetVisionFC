#!/usr/bin/env bash
set -euo pipefail

if ! command -v ffmpeg >/dev/null 2>&1; then
  echo "ffmpeg no esta instalado o no esta en PATH" >&2
  exit 1
fi

mkdir -p ../../local_outputs/activity19
ffmpeg -y -f concat -safe 0 -i video_overlay_ffmpeg_inputs.txt -vf "scale=1280:720:force_original_aspect_ratio=decrease,pad=1280:720:(ow-iw)/2:(oh-ih)/2,fps=30" -c:v libx264 -pix_fmt yuv420p ../../local_outputs/activity19/video_595_overlay_clip.mp4
