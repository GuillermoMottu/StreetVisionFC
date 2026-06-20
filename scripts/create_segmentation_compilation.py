"""
Compilation video showing SAM3+OWLv2 segmentation in action.

Uses the three new segmentation experiments:
  experiments/seg_video_692_400_700/
  experiments/seg_video_560_150_400/
  experiments/seg_video_853_900_1200/

Output: outputs/videos/segmentation_demo.mp4

Each clip is played at 20 fps display (source is ~60 fps → 3× slow motion)
so bounding boxes and masks are clearly visible.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parent.parent

CLIPS = [
    {
        "id": "video_692",
        "video": Path("/home/guillermo/Vídeos/CopaFutMX/17 Abril/video-692_singular_display.mov"),
        "detections": ROOT / "experiments/seg_video_692_400_700/detections.json",
        "masks_dir": ROOT / "experiments/seg_video_692_400_700/masks",
        "label": "video-692  |  frames 400–700",
    },
    {
        "id": "video_560",
        "video": Path("/home/guillermo/Vídeos/CopaFutMX/17 Abril/video-560_singular_display.mov"),
        "detections": ROOT / "experiments/seg_video_560_150_400/detections.json",
        "masks_dir": ROOT / "experiments/seg_video_560_150_400/masks",
        "label": "video-560  |  frames 150–400",
    },
    {
        "id": "video_853",
        "video": Path("/home/guillermo/Vídeos/CopaFutMX/17 Abril/video-853_singular_display.mov"),
        "detections": ROOT / "experiments/seg_video_853_900_1200/detections.json",
        "masks_dir": ROOT / "experiments/seg_video_853_900_1200/masks",
        "label": "video-853  |  frames 900–1200",
    },
]

W, H = 1280, 720
OUT_FPS = 30
DISPLAY_FPS = 20  # source is ~60 fps → ~3× slow motion

# BGR colors per class
COLORS = {
    "small_robot": (30, 200, 60),
    "robot": (30, 200, 60),
    "ball": (0, 165, 255),
    "yellow_goalpost": (0, 215, 255),
    "green_soccer_field": (255, 140, 0),
}
DEFAULT_COLOR = (200, 200, 200)


# ── helpers ───────────────────────────────────────────────────────────────────

def blank(color=(12, 18, 12)):
    return np.full((H, W, 3), color, dtype=np.uint8)


def put(img, text, x, y, scale=0.7, color=(255, 255, 255), thickness=1):
    cv2.putText(img, text, (x, y), cv2.FONT_HERSHEY_DUPLEX,
                scale, color, thickness, cv2.LINE_AA)


def put_centered(img, text, y, scale=1.0, color=(255, 255, 255), thickness=2):
    (tw, _), _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_DUPLEX, scale, thickness)
    cv2.putText(img, text, ((W - tw) // 2, y), cv2.FONT_HERSHEY_DUPLEX,
                scale, color, thickness, cv2.LINE_AA)


def fit_frame(frame, target_w, target_h):
    ih, iw = frame.shape[:2]
    scale = min(target_w / iw, target_h / ih)
    nw, nh = int(iw * scale), int(ih * scale)
    resized = cv2.resize(frame, (nw, nh), interpolation=cv2.INTER_AREA)
    canvas = np.zeros((target_h, target_w, 3), dtype=np.uint8)
    ox, oy = (target_w - nw) // 2, (target_h - nh) // 2
    canvas[oy:oy + nh, ox:ox + nw] = resized
    return canvas, (ox, oy, nw, nh)  # canvas + placement info for coordinate mapping


def scale_bbox(bbox, ox, oy, scale):
    x1, y1, x2, y2 = bbox
    return (int(x1 * scale + ox), int(y1 * scale + oy),
            int(x2 * scale + ox), int(y2 * scale + oy))


def load_detections(path):
    with open(path) as f:
        data = json.load(f)
    return {fr["frame"]: fr["detections"] for fr in data["frames"]}


def extract_frame(video_path, frame_index):
    cap = cv2.VideoCapture(str(video_path))
    cap.set(cv2.CAP_PROP_POS_FRAMES, frame_index)
    ok, frame = cap.read()
    cap.release()
    return frame if ok else None


def draw_mask_contour(canvas, mask_path, ox, oy, nw, nh, orig_w, orig_h, color):
    """Load a binary mask PNG and draw its contour on the canvas."""
    if not mask_path or not Path(mask_path).exists():
        return
    mask = cv2.imread(str(mask_path), cv2.IMREAD_GRAYSCALE)
    if mask is None:
        return
    scale_x = nw / orig_w
    scale_y = nh / orig_h
    mask_resized = cv2.resize(mask, (nw, nh), interpolation=cv2.INTER_NEAREST)
    contours, _ = cv2.findContours(mask_resized, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    shifted = [c + np.array([[[ox, oy]]]) for c in contours]
    cv2.drawContours(canvas, shifted, -1, color, 2)


def make_writer(path):
    path.parent.mkdir(parents=True, exist_ok=True)
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    return cv2.VideoWriter(str(path), fourcc, OUT_FPS, (W, H))


def write_static(writer, frame, duration_s):
    for _ in range(int(duration_s * OUT_FPS)):
        writer.write(frame)


# ── segments ──────────────────────────────────────────────────────────────────

def seg_title(writer):
    canvas = blank()
    cv2.rectangle(canvas, (0, 0), (W, 5), (30, 200, 60), -1)
    cv2.rectangle(canvas, (0, H - 5), (W, H), (30, 200, 60), -1)
    put_centered(canvas, "FutBotMX", 240, scale=3.0, color=(30, 200, 60), thickness=4)
    cv2.line(canvas, (W // 2 - 180, 268), (W // 2 + 180, 268), (0, 165, 255), 2)
    put_centered(canvas, "SAM3 + OWLv2  Segmentation Demo", 318, scale=1.0, color=(230, 230, 230), thickness=2)
    put_centered(canvas, "Copa FutMX  —  Mexico 2025", 368, scale=0.7, color=(130, 130, 130), thickness=1)

    legend_x, legend_y = W // 2 - 280, 430
    put(canvas, "Legend:", legend_x, legend_y, scale=0.6, color=(180, 180, 180))
    for i, (cls, col) in enumerate(COLORS.items()):
        if cls == "green_soccer_field":
            continue
        x = legend_x + i * 160
        cv2.rectangle(canvas, (x, legend_y + 14), (x + 18, legend_y + 30), col, -1)
        put(canvas, cls.replace("_", " "), x + 24, legend_y + 28, scale=0.5, color=col)

    for i in range(int(2.5 * OUT_FPS)):
        alpha = min(1.0, i / (0.4 * OUT_FPS))
        writer.write((canvas * alpha).astype(np.uint8))


def seg_clip_card(writer, label, clip_num, total_clips, duration_s=1.8):
    canvas = blank()
    cv2.rectangle(canvas, (0, 0), (W, 5), (0, 165, 255), -1)
    cv2.rectangle(canvas, (0, H - 5), (W, H), (0, 165, 255), -1)
    put_centered(canvas, f"Clip {clip_num} / {total_clips}", 290, scale=1.5,
                 color=(180, 180, 180), thickness=2)
    put_centered(canvas, label, 345, scale=0.85, color=(230, 230, 230), thickness=1)
    put_centered(canvas, "SAM3 segmentation with bounding boxes and masks",
                 390, scale=0.6, color=(100, 100, 100), thickness=1)
    write_static(writer, canvas, duration_s)


def seg_clip(writer, clip):
    dets_by_frame = load_detections(clip["detections"])
    frame_indices = sorted(dets_by_frame.keys())
    hold = max(1, round(OUT_FPS / DISPLAY_FPS))

    # Get original video dimensions once
    cap = cv2.VideoCapture(str(clip["video"]))
    orig_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    orig_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    cap.release()

    # Video panel: full width, leave 60px header
    panel_w, panel_h = W, H - 60
    scale_factor = min(panel_w / orig_w, panel_h / orig_h)

    total = len(frame_indices)
    for fidx, frame_num in enumerate(frame_indices):
        raw = extract_frame(clip["video"], frame_num)
        if raw is None:
            continue

        canvas = blank()

        # ── header bar ──────────────────────────────────────────────────────
        cv2.rectangle(canvas, (0, 0), (W, 55), (8, 14, 8), -1)
        put(canvas, clip["id"], 12, 28, scale=0.75, color=(30, 200, 60), thickness=2)
        put(canvas, clip["label"], 200, 28, scale=0.6, color=(160, 160, 160))
        put(canvas, f"frame {frame_num}", W - 200, 28, scale=0.6, color=(160, 160, 160))

        # progress bar
        prog = (fidx + 1) / total
        cv2.rectangle(canvas, (0, 50), (W, 55), (30, 40, 30), -1)
        cv2.rectangle(canvas, (0, 50), (int(W * prog), 55), (30, 200, 60), -1)

        # ── video frame ─────────────────────────────────────────────────────
        fitted, (ox, oy_off, nw, nh) = fit_frame(raw, panel_w, panel_h)
        oy_off += 60  # shift below header
        canvas[60:60 + panel_h, :] = fitted

        # real offset in full canvas coordinates
        real_oy = oy_off  # already accounts for 60px header via fit_frame placement

        # ── draw detections ─────────────────────────────────────────────────
        dets = dets_by_frame.get(frame_num, [])
        for det in dets:
            cls = det["class_name"]
            if cls == "green_soccer_field":
                continue
            color = COLORS.get(cls, DEFAULT_COLOR)
            conf = det["confidence"]
            x1, y1, x2, y2 = det["bbox"]

            # Map original coords → canvas coords
            sx1 = int(x1 * scale_factor + ox)
            sy1 = int(y1 * scale_factor + real_oy)
            sx2 = int(x2 * scale_factor + ox)
            sy2 = int(y2 * scale_factor + real_oy)

            # Mask contour
            if det.get("mask_path"):
                mask_full = Path(det["mask_path"])
                if not mask_full.is_absolute():
                    mask_full = ROOT / mask_full
                draw_mask_contour(canvas, mask_full, ox, real_oy, nw, nh,
                                  orig_w, orig_h, color)

            # Bounding box (thicker for visibility)
            cv2.rectangle(canvas, (sx1, sy1), (sx2, sy2), color, 2)

            # Label background + text
            label_txt = f"{cls.replace('_', ' ')} {conf:.2f}"
            (tw, th), _ = cv2.getTextSize(label_txt, cv2.FONT_HERSHEY_SIMPLEX, 0.48, 1)
            ly = max(sy1 - 4, real_oy + th + 2)
            cv2.rectangle(canvas, (sx1, ly - th - 4), (sx1 + tw + 4, ly), color, -1)
            cv2.putText(canvas, label_txt, (sx1 + 2, ly - 2),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.48, (10, 10, 10), 1, cv2.LINE_AA)

        # ── mini stats (bottom-right corner) ────────────────────────────────
        n_robots = sum(1 for d in dets if "robot" in d["class_name"])
        n_balls  = sum(1 for d in dets if "ball"  in d["class_name"])
        stats_x, stats_y = W - 190, H - 70
        cv2.rectangle(canvas, (stats_x - 8, stats_y - 20), (W - 8, H - 8), (8, 14, 8), -1)
        put(canvas, f"robots : {n_robots}", stats_x, stats_y,
            scale=0.55, color=COLORS["small_robot"])
        put(canvas, f"balls  : {n_balls}", stats_x, stats_y + 24,
            scale=0.55, color=COLORS["ball"])
        put(canvas, f"t = {frame_num / 59.94:.2f}s", stats_x, stats_y + 48,
            scale=0.50, color=(120, 120, 120))

        for _ in range(hold):
            writer.write(canvas)


def seg_outro(writer):
    canvas = blank()
    cv2.rectangle(canvas, (0, 0), (W, 5), (30, 200, 60), -1)
    cv2.rectangle(canvas, (0, H - 5), (W, H), (30, 200, 60), -1)
    put_centered(canvas, "Segmentation Complete", 230, scale=2.0,
                 color=(30, 200, 60), thickness=3)
    cv2.line(canvas, (W // 2 - 220, 258), (W // 2 + 220, 258), (0, 165, 255), 2)
    rows = [
        ("Model",    "SAM3 (segment-anything-model-3) + OWLv2"),
        ("Clips",    "3  (video-692, video-560, video-853)"),
        ("Frames",   "853 total  (301 + 251 + 301)"),
        ("NMS IoU",  "0.30  —  max 3 robots, 2 balls per frame"),
        ("Masks",    "~83% of detections include pixel-level mask"),
    ]
    y = 310
    for label, val in rows:
        put(canvas, f"{label}:", 300, y, scale=0.65, color=(120, 120, 120))
        put(canvas, val, 460, y, scale=0.65, color=(220, 220, 220))
        y += 34
    put_centered(canvas, "FutBotMX  —  Copa FutMX 2025", H - 44,
                 scale=0.65, color=(0, 165, 255), thickness=1)
    for i in range(int(3 * OUT_FPS)):
        alpha = min(1.0, i / (0.35 * OUT_FPS))
        writer.write((canvas * alpha).astype(np.uint8))


# ── main ──────────────────────────────────────────────────────────────────────

def main():
    out_dir = ROOT / "outputs/videos"
    tmp = out_dir / "_seg_raw.mp4"
    out = out_dir / "segmentation_demo.mp4"
    out_dir.mkdir(parents=True, exist_ok=True)

    writer = make_writer(tmp)

    print("[1/9] Title card…")
    seg_title(writer)

    for i, clip in enumerate(CLIPS, 1):
        print(f"[{i*2}/{len(CLIPS)*2+3}] Section card: {clip['id']}…")
        seg_clip_card(writer, clip["label"], i, len(CLIPS))
        print(f"[{i*2+1}/{len(CLIPS)*2+3}] Rendering clip: {clip['id']}…")
        seg_clip(writer, clip)

    print("[9/9] Outro…")
    seg_outro(writer)

    writer.release()
    print(f"\nRaw written: {tmp}")

    print("Re-encoding H.264…")
    r = subprocess.run(
        ["ffmpeg", "-y", "-i", str(tmp),
         "-vcodec", "libx264", "-crf", "18", "-preset", "fast",
         "-pix_fmt", "yuv420p", str(out)],
        capture_output=True, text=True,
    )
    tmp.unlink(missing_ok=True)
    if r.returncode != 0:
        print("ffmpeg error:", r.stderr[-400:])
        sys.exit(1)

    probe = subprocess.run(
        ["ffprobe", "-v", "quiet", "-show_entries", "format=duration",
         "-of", "csv=p=0", str(out)],
        capture_output=True, text=True,
    )
    duration = float(probe.stdout.strip() or 0)
    size_mb = out.stat().st_size / 1e6
    print(f"\nDone → {out}")
    print(f"Duration : {duration:.1f}s")
    print(f"Size     : {size_mb:.1f} MB")


if __name__ == "__main__":
    main()
