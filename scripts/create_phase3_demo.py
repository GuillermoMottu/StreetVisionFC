"""
Phase 3 demo video — FutBotMX / StreetVisionFC.

Sections:
  1. Title card
  2. SAM 3 segmentation with pixel-level masks (frame 143)
  3. ByteTrack tracking (frames 120-180 slowed to 5fps subjectively)
  4. Events overlay
  5. Tactical heatmap + metrics summary

Output: outputs/videos/futbotmx_demo.mp4  (~40-50 seconds, 15fps, 680x904)

Usage:
    python scripts/create_phase3_demo.py \
        --video "/home/guillermo/Vídeos/CopaFutMX/17 Abril/video-836_singular_display.mov"
"""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
import sys

import cv2
import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

# ─── constants ────────────────────────────────────────────────────────────────
DEMO_FPS = 15
SCALE = 0.5
MASK_ALPHA = 0.45

CLASS_COLORS: dict[str, tuple[int, int, int]] = {
    "small_robot": (50, 220, 50),
    "robot":       (50, 220, 50),
    "ball":        (255, 160, 0),
    "green_soccer_field": (30, 80, 210),
    "goalpost":    (255, 255, 0),
}

MASKS_DIR = Path("experiments/current_evaluation/masks")
TRACKS_CSV = Path("experiments/test_003_tracking/video_836_real_tracking_120_180/tracks_bytetrack.csv")
EVENTS_JSON = Path("experiments/test_013_level2_events/video_836_real_events_120_180/level2_events.json")
METRICS_JSON = Path("experiments/test_012_level2_metrics/video_836_real_metrics_120_180/level2_metrics.json")
HEATMAP_PNG = Path("experiments/test_003_tracking/video_836_real_tracking_120_180/heatmap_bytetrack.png")
OUTPUT_PATH = Path("outputs/videos/futbotmx_demo.mp4")

SEG_FRAME = 143  # frame with pre-generated SAM3 masks


# ─── helpers ──────────────────────────────────────────────────────────────────

def scaled_size(w: int, h: int) -> tuple[int, int]:
    return int(w * SCALE), int(h * SCALE)


def scale_frame(bgr: np.ndarray, sw: int, sh: int) -> np.ndarray:
    return cv2.resize(bgr, (sw, sh), interpolation=cv2.INTER_LINEAR)


def add_banner(frame: np.ndarray, text: str, y_start: int = 0) -> np.ndarray:
    frame = frame.copy()
    h, w = frame.shape[:2]
    cv2.rectangle(frame, (0, y_start), (w, y_start + 34), (0, 0, 0), -1)
    cv2.putText(frame, text, (10, y_start + 22),
                cv2.FONT_HERSHEY_SIMPLEX, 0.65, (255, 255, 255), 1, cv2.LINE_AA)
    return frame


def add_section_header(frame: np.ndarray, title: str) -> np.ndarray:
    frame = frame.copy()
    h, w = frame.shape[:2]
    overlay = frame.copy()
    cv2.rectangle(overlay, (0, 0), (w, 42), (20, 20, 20), -1)
    cv2.addWeighted(overlay, 0.75, frame, 0.25, 0, frame)
    cv2.putText(frame, title, (12, 28),
                cv2.FONT_HERSHEY_SIMPLEX, 0.75, (255, 255, 255), 2, cv2.LINE_AA)
    return frame


def write_n(writer: cv2.VideoWriter, frame: np.ndarray, n: int) -> None:
    for _ in range(n):
        writer.write(frame)


def read_source_frame(cap: cv2.VideoCapture, idx: int) -> np.ndarray | None:
    cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
    ok, bgr = cap.read()
    return bgr if ok else None


def load_tracks(csv_path: Path) -> dict[int, list[dict]]:
    rows: dict[int, list[dict]] = {}
    with csv_path.open("r", newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            fi = int(float(row["frame"]))
            rows.setdefault(fi, []).append(row)
    return rows


def draw_track_row(frame: np.ndarray, row: dict, sw: int, sh: int, src_w: int, src_h: int) -> None:
    color = CLASS_COLORS.get(row["class_name"], (200, 200, 200))
    sx, sy = sw / src_w, sh / src_h
    x1 = int(float(row["bbox_x1"]) * sx)
    y1 = int(float(row["bbox_y1"]) * sy)
    x2 = int(float(row["bbox_x2"]) * sx)
    y2 = int(float(row["bbox_y2"]) * sy)
    cx = int(float(row["x"]) * sx)
    cy = int(float(row["y"]) * sy)
    cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
    cv2.circle(frame, (cx, cy), 3, color, -1)
    tid = row.get("track_id", "")
    cv2.putText(frame, tid, (x1, max(16, y1 - 4)),
                cv2.FONT_HERSHEY_SIMPLEX, 0.40, color, 1, cv2.LINE_AA)


# ─── sections ─────────────────────────────────────────────────────────────────

def section_title(writer: cv2.VideoWriter, sw: int, sh: int, seconds: float = 4.0) -> None:
    bg = np.zeros((sh, sw, 3), dtype=np.uint8)
    lines = [
        ("FutBotMX / StreetVisionFC", 0.85, (255, 255, 255), 180),
        ("Robot Soccer Computer Vision", 0.60, (180, 220, 180), 240),
        ("SAM 3 + ByteTrack + Eventos", 0.55, (180, 220, 180), 290),
        ("CopaFutMX  17 Abril 2024", 0.45, (150, 150, 150), 360),
        ("video_836  |  frames 120-180", 0.38, (120, 120, 120), 415),
    ]
    for text, scale, color, y in lines:
        cv2.putText(bg, text, (30, y), cv2.FONT_HERSHEY_SIMPLEX, scale, color, 1, cv2.LINE_AA)
    write_n(writer, bg, int(DEMO_FPS * seconds))


def section_segmentation(
    writer: cv2.VideoWriter,
    cap: cv2.VideoCapture,
    sw: int, sh: int, src_w: int, src_h: int,
    seconds: float = 14.0,
) -> None:
    bgr = read_source_frame(cap, SEG_FRAME)
    if bgr is None:
        return
    base = scale_frame(bgr, sw, sh).astype(np.float32)

    mask_files = sorted(MASKS_DIR.glob(f"frame_{SEG_FRAME:06d}_*.png"))
    overlaid = base.copy()

    for mask_path in mask_files:
        parts = mask_path.stem.split("_")
        # stem: frame_000143_<class>_<idx>
        class_name = "_".join(parts[2:-1])
        color = CLASS_COLORS.get(class_name, (200, 200, 200))
        mask_np = np.array(Image.open(mask_path).convert("L"))
        mask_scaled = cv2.resize(mask_np, (sw, sh), interpolation=cv2.INTER_NEAREST)
        binary = (mask_scaled > 127).astype(np.float32)
        for c_idx, c_val in enumerate(color):
            overlaid[:, :, c_idx] = np.where(
                binary > 0,
                overlaid[:, :, c_idx] * (1 - MASK_ALPHA) + c_val * MASK_ALPHA,
                overlaid[:, :, c_idx],
            )

        # bbox from mask bounds
        ys, xs = np.where(mask_scaled > 127)
        if xs.size > 0 and class_name != "green_soccer_field":
            x1, y1, x2, y2 = int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())
            cv2.rectangle(overlaid.astype(np.uint8), (x1, y1), (x2, y2),
                          color, 1)
            cv2.putText(overlaid.astype(np.uint8), class_name.replace("_", " "),
                        (x1 + 2, max(14, y1 - 4)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.38, color, 1, cv2.LINE_AA)

    result = np.clip(overlaid, 0, 255).astype(np.uint8)
    result = add_section_header(result, "SAM 3 | Segmentacion Pixel-Level (frame 143)")

    # add class legend
    legend_y = sh - 10
    for cls, col in [("robot", CLASS_COLORS["robot"]), ("ball", CLASS_COLORS["ball"]),
                     ("field", CLASS_COLORS["green_soccer_field"]), ("goalpost", CLASS_COLORS["goalpost"])]:
        cv2.circle(result, (20, legend_y), 6, col, -1)
        cv2.putText(result, cls, (30, legend_y + 4),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.35, (255, 255, 255), 1, cv2.LINE_AA)
        legend_y -= 20

    write_n(writer, result, int(DEMO_FPS * seconds))


def section_tracking(
    writer: cv2.VideoWriter,
    cap: cv2.VideoCapture,
    sw: int, sh: int, src_w: int, src_h: int,
    tracks: dict[int, list[dict]],
    repeat: int = 3,
) -> None:
    frame_range = range(120, 181)
    for fi in frame_range:
        bgr = read_source_frame(cap, fi)
        if bgr is None:
            continue
        frame = scale_frame(bgr, sw, sh)
        for row in tracks.get(fi, []):
            draw_track_row(frame, row, sw, sh, src_w, src_h)
        frame = add_section_header(frame, f"ByteTrack | Seguimiento  (frame {fi})")
        # small frame counter
        cv2.putText(frame, f"{fi}", (sw - 64, sh - 8),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.35, (180, 180, 180), 1)
        write_n(writer, frame, repeat)


def section_events(
    writer: cv2.VideoWriter,
    cap: cv2.VideoCapture,
    sw: int, sh: int, src_w: int, src_h: int,
    events: list[dict],
    hold_sec: float = 2.0,
) -> None:
    shown: set[str] = set()
    for evt in events[:6]:  # cap at 6 events to stay under 2 min
        etype = evt.get("event_type", "event")
        if etype in shown:
            continue
        shown.add(etype)
        fi = evt.get("frame_start", 120)
        bgr = read_source_frame(cap, fi)
        if bgr is None:
            continue
        frame = scale_frame(bgr, sw, sh)
        # highlight with tinted overlay
        tint = np.zeros_like(frame, dtype=np.float32)
        tint[:, :] = [0, 0, 40]
        frame = cv2.addWeighted(frame, 0.85, tint.astype(np.uint8), 0.15, 0)
        frame = add_section_header(frame, f"Evento: {etype.replace('_', ' ').title()}")
        # event details
        conf = evt.get("confidence", 0)
        robot = evt.get("primary_object_id", "")
        detail = f"{robot}  conf={conf:.2f}  t={evt.get('time_start_sec', 0):.2f}s"
        cv2.putText(frame, detail, (12, sh - 12),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.40, (200, 255, 200), 1, cv2.LINE_AA)
        write_n(writer, frame, int(DEMO_FPS * hold_sec))


def section_heatmap_metrics(
    writer: cv2.VideoWriter,
    sw: int, sh: int,
    metrics: dict,
    seconds: float = 10.0,
) -> None:
    canvas = np.zeros((sh, sw, 3), dtype=np.uint8)

    # left: heatmap
    if HEATMAP_PNG.exists():
        hm = cv2.imread(str(HEATMAP_PNG))
        if hm is not None:
            hm = cv2.resize(hm, (sw // 2, int(sh * 0.65)))
            canvas[42: 42 + hm.shape[0], :sw // 2] = hm

    # right: metrics text
    summary = metrics.get("summary", {})
    mx = sw // 2 + 12
    my = 60
    cv2.putText(canvas, "Metricas", (mx, my), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 1)
    my += 30
    kv_pairs = [
        ("Frames obs.", str(summary.get("observed_frames", "—"))),
        ("Tracks",      str(summary.get("track_count", "—"))),
        ("Posesion s",  f"{summary.get('possession_assigned_seconds', 0):.2f}s"),
        ("Umbral pos.", f"{summary.get('possession_threshold_px', 0):.0f}px"),
    ]
    poss = metrics.get("possession_by_robot", [])
    if poss:
        kv_pairs.append(("Robot ppal.", poss[0].get("robot_id", "—")))
        kv_pairs.append(("% posesion", f"{poss[0].get('percent_observed_time', 0):.1f}%"))

    for k, v in kv_pairs:
        cv2.putText(canvas, f"{k}:", (mx, my), cv2.FONT_HERSHEY_SIMPLEX, 0.38, (150, 150, 150), 1)
        cv2.putText(canvas, v, (mx + 110, my), cv2.FONT_HERSHEY_SIMPLEX, 0.40, (220, 255, 220), 1)
        my += 26

    canvas = add_section_header(canvas, "Visualizacion Tactica + Metricas")
    write_n(writer, canvas, int(DEMO_FPS * seconds))


# ─── main ─────────────────────────────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--video", required=True)
    parser.add_argument("--output", default=str(OUTPUT_PATH))
    args = parser.parse_args()

    cap = cv2.VideoCapture(args.video)
    if not cap.isOpened():
        print(f"ERROR: Cannot open {args.video}")
        return 1

    src_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    src_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    sw, sh = scaled_size(src_w, src_h)

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    writer = cv2.VideoWriter(str(out_path), cv2.VideoWriter_fourcc(*"mp4v"), DEMO_FPS, (sw, sh))
    if not writer.isOpened():
        print(f"ERROR: Cannot write to {out_path}")
        cap.release()
        return 1

    tracks = load_tracks(TRACKS_CSV) if TRACKS_CSV.exists() else {}
    events = json.loads(EVENTS_JSON.read_text()) if EVENTS_JSON.exists() else []
    metrics = json.loads(METRICS_JSON.read_text()) if METRICS_JSON.exists() else {}

    print(f"[1/5] Title card")
    section_title(writer, sw, sh, seconds=4.0)

    print(f"[2/5] Segmentation section (frame {SEG_FRAME})")
    section_segmentation(writer, cap, sw, sh, src_w, src_h, seconds=13.0)

    print(f"[3/5] Tracking section (frames 120-180, repeat=3)")
    section_tracking(writer, cap, sw, sh, src_w, src_h, tracks, repeat=3)

    print(f"[4/5] Events section ({len(events)} events)")
    section_events(writer, cap, sw, sh, src_w, src_h, events, hold_sec=2.5)

    print(f"[5/5] Heatmap + metrics")
    section_heatmap_metrics(writer, sw, sh, metrics, seconds=10.0)

    writer.release()
    cap.release()

    # verify duration with ffprobe
    duration_cmd = f'ffprobe -v quiet -show_entries format=duration -of csv=p=0 "{out_path}" 2>/dev/null'
    import subprocess
    result = subprocess.run(duration_cmd, shell=True, capture_output=True, text=True)
    duration = float(result.stdout.strip()) if result.stdout.strip() else None
    size_mb = out_path.stat().st_size / (1024 * 1024)

    print(f"\nOutput: {out_path}")
    print(f"Size:   {size_mb:.1f} MB")
    if duration:
        print(f"Duration: {duration:.1f}s {'[OK ≤120s]' if duration <= 120 else '[WARN >120s]'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
