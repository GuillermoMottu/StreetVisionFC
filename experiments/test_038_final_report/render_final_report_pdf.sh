#!/usr/bin/env bash
set -euo pipefail

BROWSER="${BROWSER:-}"
if [ -z "$BROWSER" ]; then
  if command -v chromium >/dev/null 2>&1; then
    BROWSER="chromium"
  elif command -v chromium-browser >/dev/null 2>&1; then
    BROWSER="chromium-browser"
  elif command -v google-chrome >/dev/null 2>&1; then
    BROWSER="google-chrome"
  else
    echo "No se encontro chromium/chromium-browser/google-chrome en PATH" >&2
    exit 1
  fi
fi

mkdir -p "../../local_outputs/activity20"
"$BROWSER" --headless --disable-gpu "--print-to-pdf=../../local_outputs/activity20/futbotmx_final_report.pdf" final_report.html
echo "PDF local escrito en ../../local_outputs/activity20/futbotmx_final_report.pdf"
