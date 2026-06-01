from __future__ import annotations

import argparse
import csv
from pathlib import Path
import sys

import cv2

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from futbotmx.visualization.overlay import COLORS
from futbotmx.video_io import inspect_video


def rows_by_frame(tracks_csv: str | Path) -> dict[int, list[dict[str, str]]]:
    result: dict[int, list[dict[str, str]]] = {}
    with Path(tracks_csv).open("r", newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            frame = int(float(row["frame"]))
            result.setdefault(frame, []).append(row)
    return result


def draw_tracks(frame, frame_rows: list[dict[str, str]], frame_index: int) -> None:
    cv2.putText(frame, f"Frame {frame_index}", (24, 42), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 255), 2)
    for row in frame_rows:
        color = COLORS.get(row["class_name"], (255, 255, 255))
        x1 = int(float(row["bbox_x1"]))
        y1 = int(float(row["bbox_y1"]))
        x2 = int(float(row["bbox_x2"]))
        y2 = int(float(row["bbox_y2"]))
        cx = int(float(row["x"]))
        cy = int(float(row["y"]))
        cv2.rectangle(frame, (x1, y1), (x2, y2), color, 3)
        cv2.circle(frame, (cx, cy), 4, color, -1)
        cv2.putText(frame, row["track_id"], (x1, max(20, y1 - 8)), cv2.FONT_HERSHEY_SIMPLEX, 0.55, color, 2)


def write_summary(path: Path, video_path: str, tracks_csv: str, output: str, start_frame: int, end_frame: int, fps: float) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "# Demo local Nivel 1\n\n"
        "## Estado\n\n"
        "Demo MP4 generado localmente y no versionado por Git.\n\n"
        "## Configuracion\n\n"
        f"- Video fuente: `{video_path}`\n"
        f"- Tracks: `{tracks_csv}`\n"
        f"- Frames: `{start_frame}-{end_frame}`\n"
        f"- FPS demo: `{fps}`\n"
        f"- Salida local: `{output}`\n\n"
        "## Comando\n\n"
        "```bash\n"
        "python scripts/create_demo_video.py \\\n"
        f"  --video \"{video_path}\" \\\n"
        f"  --tracks {tracks_csv} \\\n"
        f"  --output {output} \\\n"
        f"  --summary {path} \\\n"
        f"  --start-frame {start_frame} --end-frame {end_frame} --fps {fps:g}\n"
        "```\n\n"
        "## Politica Git\n\n"
        "El archivo `.mp4` queda fuera de Git por `.gitignore`; este resumen documenta como regenerarlo.\n",
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Create a local annotated demo video from tracks.")
    parser.add_argument("--video", required=True)
    parser.add_argument("--tracks", required=True)
    parser.add_argument("--output", default="outputs/videos/level1_demo_video_836_120_180.mp4")
    parser.add_argument("--summary", default="experiments/evidence_level1/demo_local.md")
    parser.add_argument("--start-frame", type=int, default=120)
    parser.add_argument("--end-frame", type=int, default=180)
    parser.add_argument("--fps", type=float, default=15.0)
    args = parser.parse_args()

    metadata = inspect_video(args.video)
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    frame_rows = rows_by_frame(args.tracks)
    capture = cv2.VideoCapture(str(args.video))
    writer = cv2.VideoWriter(
        str(output_path),
        cv2.VideoWriter_fourcc(*"mp4v"),
        args.fps,
        (metadata.width, metadata.height),
    )
    try:
        if not capture.isOpened():
            raise ValueError(f"Could not open video: {args.video}")
        if not writer.isOpened():
            raise ValueError(f"Could not write demo video: {output_path}")
        for frame_index in range(args.start_frame, args.end_frame + 1):
            capture.set(cv2.CAP_PROP_POS_FRAMES, frame_index)
            ok, frame = capture.read()
            if not ok:
                continue
            draw_tracks(frame, frame_rows.get(frame_index, []), frame_index)
            writer.write(frame)
    finally:
        capture.release()
        writer.release()

    write_summary(
        Path(args.summary),
        args.video,
        args.tracks,
        str(output_path),
        args.start_frame,
        args.end_frame,
        args.fps,
    )
    print(f"Wrote local demo video to {output_path}")
    print(f"Wrote demo summary to {args.summary}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
