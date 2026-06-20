"""
Create a 40+ second demo compilation video showing FutBotMX analysis in action.

Uses completed experiments:
  - test_043_full_analysis_video_595_120_180  (full level3 analysis)
  - test_044_full_analysis_video_836_120_180  (tracking only)

Output: outputs/videos/demo_compilation.mp4
"""

from __future__ import annotations

import csv
import subprocess
import sys
import tempfile
from pathlib import Path

import cv2
import numpy as np

# ── paths ──────────────────────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parent.parent
EXP_595 = ROOT / "experiments/test_043_full_analysis_video_595_120_180"
EXP_836 = ROOT / "experiments/test_044_full_analysis_video_836_120_180"
VIDEO_595 = Path("/home/guillermo/Vídeos/CopaFutMX/17 Abril/video-595_singular_display.mov")
VIDEO_836 = Path("/home/guillermo/Vídeos/CopaFutMX/17 Abril/video-836_singular_display.mov")
OUT_DIR = ROOT / "outputs/videos"
OUT_PATH = OUT_DIR / "demo_compilation.mp4"

# ── output spec ────────────────────────────────────────────────────────────────
W, H = 1280, 720
FPS = 30

# ── colors (BGR) ──────────────────────────────────────────────────────────────
BG_DARK = (18, 25, 18)
GREEN_ACCENT = (60, 180, 60)
GOLD_ACCENT = (0, 195, 215)
WHITE = (255, 255, 255)
GRAY = (160, 160, 160)
RED_ACCENT = (60, 80, 220)

TRACK_COLORS = {
    "ball": (0, 220, 255),
    "small_robot": (0, 200, 80),
    "robot": (0, 200, 80),
    "yellow_goalpost": (0, 200, 255),
    "ally_robot": (0, 200, 80),
    "opponent_robot": (40, 80, 230),
}


# ── helpers ───────────────────────────────────────────────────────────────────

def blank(color: tuple[int, int, int] = BG_DARK) -> np.ndarray:
    canvas = np.full((H, W, 3), color, dtype=np.uint8)
    return canvas


def put(img: np.ndarray, text: str, x: int, y: int,
        scale: float = 1.0, color: tuple = WHITE, thickness: int = 2,
        font: int = cv2.FONT_HERSHEY_DUPLEX) -> None:
    cv2.putText(img, text, (x, y), font, scale, color, thickness, cv2.LINE_AA)


def put_centered(img: np.ndarray, text: str, y: int, scale: float = 1.0,
                 color: tuple = WHITE, thickness: int = 2) -> None:
    (tw, th), _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_DUPLEX, scale, thickness)
    x = (W - tw) // 2
    cv2.putText(img, text, (x, y), cv2.FONT_HERSHEY_DUPLEX, scale, color, thickness, cv2.LINE_AA)


def hline(img: np.ndarray, y: int, x0: int = 0, x1: int = W,
          color: tuple = GREEN_ACCENT, thickness: int = 2) -> None:
    cv2.line(img, (x0, y), (x1, y), color, thickness)


def load_image_fit(path: Path, target_w: int, target_h: int, pad_color: tuple = BG_DARK) -> np.ndarray:
    """Load image and fit inside target_w×target_h with letterbox."""
    img = cv2.imread(str(path))
    if img is None:
        canvas = np.full((target_h, target_w, 3), pad_color, dtype=np.uint8)
        return canvas
    ih, iw = img.shape[:2]
    scale = min(target_w / iw, target_h / ih)
    nw, nh = int(iw * scale), int(ih * scale)
    resized = cv2.resize(img, (nw, nh), interpolation=cv2.INTER_AREA)
    canvas = np.full((target_h, target_w, 3), pad_color, dtype=np.uint8)
    ox, oy = (target_w - nw) // 2, (target_h - nh) // 2
    canvas[oy:oy + nh, ox:ox + nw] = resized
    return canvas


def load_tracks(csv_path: Path) -> dict[int, list[dict]]:
    """Load tracks CSV into {frame: [row, ...]}."""
    result: dict[int, list[dict]] = {}
    with csv_path.open(newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            f = int(float(row["frame"]))
            result.setdefault(f, []).append(row)
    return result


def extract_frame(video_path: Path, frame_index: int) -> np.ndarray | None:
    cap = cv2.VideoCapture(str(video_path))
    cap.set(cv2.CAP_PROP_POS_FRAMES, frame_index)
    ok, frame = cap.read()
    cap.release()
    return frame if ok else None


def annotate_frame(frame: np.ndarray, tracks: list[dict]) -> np.ndarray:
    img = frame.copy()
    for row in tracks:
        cls = row.get("class_name", "")
        color = TRACK_COLORS.get(cls, WHITE)
        x1, y1 = int(float(row["bbox_x1"])), int(float(row["bbox_y1"]))
        x2, y2 = int(float(row["bbox_x2"])), int(float(row["bbox_y2"]))
        cx, cy = int(float(row["x"])), int(float(row["y"]))
        cv2.rectangle(img, (x1, y1), (x2, y2), color, 3)
        cv2.circle(img, (cx, cy), 5, color, -1)
        label = row.get("track_id", cls)
        cv2.putText(img, label, (x1, max(20, y1 - 8)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, color, 2, cv2.LINE_AA)
    return img


def fit_video_frame(frame: np.ndarray, target_w: int, target_h: int) -> np.ndarray:
    ih, iw = frame.shape[:2]
    scale = min(target_w / iw, target_h / ih)
    nw, nh = int(iw * scale), int(ih * scale)
    resized = cv2.resize(frame, (nw, nh), interpolation=cv2.INTER_AREA)
    canvas = np.full((target_h, target_w, 3), BG_DARK, dtype=np.uint8)
    ox, oy = (target_w - nw) // 2, (target_h - nh) // 2
    canvas[oy:oy + nh, ox:ox + nw] = resized
    return canvas


# ── writers ───────────────────────────────────────────────────────────────────

def make_writer(path: Path) -> cv2.VideoWriter:
    path.parent.mkdir(parents=True, exist_ok=True)
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    return cv2.VideoWriter(str(path), fourcc, FPS, (W, H))


def write_static(writer: cv2.VideoWriter, frame: np.ndarray, duration_s: float) -> None:
    n = int(duration_s * FPS)
    for _ in range(n):
        writer.write(frame)


# ── segment builders ──────────────────────────────────────────────────────────

def seg_title(writer: cv2.VideoWriter) -> None:
    """Opening title card, 3 seconds."""
    for i in range(int(3 * FPS)):
        canvas = blank()
        # top accent bar
        cv2.rectangle(canvas, (0, 0), (W, 6), GREEN_ACCENT, -1)
        # logo area
        put_centered(canvas, "FutBotMX", 240, scale=3.2, color=GREEN_ACCENT, thickness=4)
        hline(canvas, 280, x0=W // 2 - 200, x1=W // 2 + 200, color=GOLD_ACCENT)
        put_centered(canvas, "AI Football Analysis System", 330, scale=1.1, color=WHITE, thickness=2)
        put_centered(canvas, "Copa FutMX  |  Mexico 2025", 390, scale=0.75, color=GRAY, thickness=1)
        # bottom bar
        cv2.rectangle(canvas, (0, H - 6), (W, H), GREEN_ACCENT, -1)
        # fade-in first 0.5s
        alpha = min(1.0, i / (0.5 * FPS))
        canvas = (canvas * alpha).astype(np.uint8)
        writer.write(canvas)


def seg_section_card(writer: cv2.VideoWriter, title: str, subtitle: str, clip_tag: str,
                     duration_s: float = 2.0) -> None:
    """Section transition card."""
    canvas = blank()
    cv2.rectangle(canvas, (0, 0), (W, 6), GOLD_ACCENT, -1)
    cv2.rectangle(canvas, (0, H - 6), (W, H), GOLD_ACCENT, -1)
    put_centered(canvas, title, 300, scale=1.9, color=WHITE, thickness=3)
    put_centered(canvas, subtitle, 360, scale=0.95, color=GRAY, thickness=1)
    put_centered(canvas, clip_tag, 420, scale=0.7, color=GREEN_ACCENT, thickness=1)
    write_static(writer, canvas, duration_s)


def seg_video_overlay(writer: cv2.VideoWriter, video_path: Path, tracks_by_frame: dict,
                      frame_start: int, frame_end: int, display_fps: float,
                      clip_id: str, show_raw_first: bool = True) -> None:
    """
    Animated analysis segment.
    Left panel: annotated video frame (~540px wide)
    Right panel: analysis metadata panel (740px wide)
    Plays frames at display_fps (slow motion effect).
    """
    vid_panel_w = 540
    info_panel_w = W - vid_panel_w

    frames = list(range(frame_start, frame_end + 1))
    hold_frames = max(1, int(FPS / display_fps))

    # Optional: show raw video first (0.5 seconds)
    if show_raw_first:
        raw_frame = extract_frame(video_path, frame_start)
        if raw_frame is not None:
            for _ in range(int(0.5 * FPS)):
                canvas = blank()
                vid = fit_video_frame(raw_frame, vid_panel_w, H)
                canvas[:, :vid_panel_w] = vid
                # divider
                cv2.line(canvas, (vid_panel_w, 0), (vid_panel_w, H), GRAY, 1)
                # right panel: "RAW VIDEO" label
                put(canvas, "RAW VIDEO", vid_panel_w + 20, 60,
                    scale=1.0, color=GOLD_ACCENT, thickness=2)
                put(canvas, clip_id, vid_panel_w + 20, 100,
                    scale=0.65, color=GRAY, thickness=1)
                writer.write(canvas)

    for fidx, frame_num in enumerate(frames):
        raw = extract_frame(video_path, frame_num)
        if raw is None:
            continue
        frame_tracks = tracks_by_frame.get(frame_num, [])
        annotated = annotate_frame(raw, frame_tracks)
        vid = fit_video_frame(annotated, vid_panel_w, H)

        canvas = blank()
        canvas[:, :vid_panel_w] = vid
        cv2.line(canvas, (vid_panel_w, 0), (vid_panel_w, H), GREEN_ACCENT, 2)

        # ── right panel content ──────────────────────────────────────
        rx = vid_panel_w + 20
        put(canvas, "FutBotMX ANALYSIS", rx, 50, scale=0.85, color=GREEN_ACCENT, thickness=2)
        put(canvas, clip_id, rx, 80, scale=0.6, color=GRAY, thickness=1)
        hline(canvas, 95, x0=vid_panel_w + 10, x1=W - 10, color=GREEN_ACCENT, thickness=1)

        # progress bar
        prog = (fidx + 1) / len(frames)
        bar_y, bar_h = 110, 14
        bar_x0, bar_x1 = rx, W - 20
        cv2.rectangle(canvas, (bar_x0, bar_y), (bar_x1, bar_y + bar_h), (40, 50, 40), -1)
        cv2.rectangle(canvas, (bar_x0, bar_y), (bar_x0 + int((bar_x1 - bar_x0) * prog), bar_y + bar_h),
                      GREEN_ACCENT, -1)

        put(canvas, f"Frame {frame_num} / {frame_end}", rx, 148, scale=0.6, color=WHITE, thickness=1)
        put(canvas, f"Progress: {prog * 100:.0f}%", rx + 300, 148, scale=0.6, color=GRAY, thickness=1)

        hline(canvas, 165, x0=vid_panel_w + 10, x1=W - 10, color=(40, 55, 40), thickness=1)

        # detected objects
        put(canvas, "DETECTED OBJECTS", rx, 195, scale=0.65, color=GOLD_ACCENT, thickness=1)
        y_off = 225
        robots = [r for r in frame_tracks if "robot" in r.get("class_name", "")]
        balls = [r for r in frame_tracks if "ball" in r.get("class_name", "")]
        goals = [r for r in frame_tracks if "goalpost" in r.get("class_name", "")]

        dot_x = rx + 12
        put(canvas, f"Robots : {len(robots):2d}", rx, y_off, scale=0.65,
            color=TRACK_COLORS["small_robot"], thickness=1)
        y_off += 32
        put(canvas, f"Ball   : {len(balls):2d}", rx, y_off, scale=0.65,
            color=TRACK_COLORS["ball"], thickness=1)
        y_off += 32
        put(canvas, f"Goals  : {len(goals):2d}", rx, y_off, scale=0.65,
            color=TRACK_COLORS["yellow_goalpost"], thickness=1)
        y_off += 32

        hline(canvas, y_off + 5, x0=vid_panel_w + 10, x1=W - 10, color=(40, 55, 40), thickness=1)

        # track list (max 8)
        put(canvas, "ACTIVE TRACKS", rx, y_off + 30, scale=0.6, color=GOLD_ACCENT, thickness=1)
        ty = y_off + 60
        for row in frame_tracks[:8]:
            cls = row.get("class_name", "")
            tid = row.get("track_id", "")
            conf = float(row.get("confidence", 0))
            col = TRACK_COLORS.get(cls, WHITE)
            cv2.circle(canvas, (rx + 5, ty - 6), 4, col, -1)
            put(canvas, f"{tid}  [{conf:.2f}]", rx + 16, ty,
                scale=0.5, color=WHITE, thickness=1)
            ty += 22

        # timestamp
        ts = frame_num / 59.94
        put(canvas, f"t = {ts:.2f}s", rx, H - 30, scale=0.55, color=GRAY, thickness=1)

        for _ in range(hold_frames):
            writer.write(canvas)


def seg_static_image(writer: cv2.VideoWriter, image_path: Path,
                     title: str, subtitle: str, duration_s: float) -> None:
    """Show a static analysis image with title overlay."""
    img = load_image_fit(image_path, W - 40, H - 100)
    canvas = blank()
    # place image centered vertically below title area
    canvas[80:80 + img.shape[0], 20:20 + img.shape[1]] = img

    # title bar
    cv2.rectangle(canvas, (0, 0), (W, 72), (10, 18, 10), -1)
    put(canvas, title, 20, 42, scale=0.9, color=GREEN_ACCENT, thickness=2)
    put(canvas, subtitle, W - 400, 42, scale=0.65, color=GRAY, thickness=1)
    hline(canvas, 72, color=GREEN_ACCENT, thickness=2)

    write_static(writer, canvas, duration_s)


def seg_highlight_grid(writer: cv2.VideoWriter, image_paths: list[Path],
                       labels: list[str], duration_s: float) -> None:
    """Show up to 4 highlight images in a 2×2 grid."""
    n = min(len(image_paths), 4)
    cell_w, cell_h = W // 2, H // 2
    canvas = blank()
    for i, (p, lbl) in enumerate(zip(image_paths[:n], labels[:n])):
        cx = (i % 2) * cell_w
        cy = (i // 2) * cell_h
        cell = load_image_fit(p, cell_w - 4, cell_h - 4)
        canvas[cy + 2:cy + cell_h - 2, cx + 2:cx + cell_w - 2] = cell
        cv2.rectangle(canvas, (cx, cy), (cx + cell_w, cy + cell_h), GREEN_ACCENT, 2)
        put(canvas, lbl, cx + 8, cy + cell_h - 16, scale=0.5, color=GOLD_ACCENT, thickness=1)
    write_static(writer, canvas, duration_s)


def seg_outro(writer: cv2.VideoWriter) -> None:
    """Final summary / outro, 4 seconds."""
    for i in range(int(4 * FPS)):
        canvas = blank()
        cv2.rectangle(canvas, (0, 0), (W, 6), GREEN_ACCENT, -1)
        cv2.rectangle(canvas, (0, H - 6), (W, H), GREEN_ACCENT, -1)

        put_centered(canvas, "Analysis Complete", 220, scale=2.0, color=GREEN_ACCENT, thickness=3)
        hline(canvas, 260, x0=W // 2 - 250, x1=W // 2 + 250, color=GOLD_ACCENT)

        stats = [
            ("Videos analyzed", "2"),
            ("Clips processed", "2  (frames 120–180)"),
            ("Detection model", "SAM3 + OWLv2"),
            ("Tracking", "ByteTrack (lightweight)"),
            ("Events detected", "Level1 + Level2 + Level3"),
            ("Visualizations", "Voronoi · Minimap · Highlights"),
        ]
        y = 310
        for label, val in stats:
            put(canvas, f"{label}:", 240, y, scale=0.65, color=GRAY, thickness=1)
            put(canvas, val, 530, y, scale=0.65, color=WHITE, thickness=1)
            y += 34

        put_centered(canvas, "FutBotMX  —  Copa FutMX 2025", H - 50,
                     scale=0.7, color=GOLD_ACCENT, thickness=1)

        alpha = min(1.0, i / (0.4 * FPS))
        canvas = (canvas * alpha).astype(np.uint8)
        writer.write(canvas)


# ── main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    tmp_path = OUT_DIR / "_demo_raw.mp4"

    print("Loading tracks…")
    tracks_595 = load_tracks(EXP_595 / "tracking/tracks.csv")
    tracks_836 = load_tracks(EXP_836 / "tracking/tracks.csv")

    print("Creating compilation…")
    writer = make_writer(tmp_path)

    # ── 1. Title (3s) ──────────────────────────────────────────────────────────
    print("  [1/9] Title card…")
    seg_title(writer)

    # ── 2. Video 595 section card (2s) ─────────────────────────────────────────
    print("  [2/9] Section card: video 595…")
    seg_section_card(writer,
                     "Clip Analysis — video 595",
                     "SAM3 Detection  +  ByteTrack  +  Level 3 Events",
                     "Frames 120–180  |  ~1 second of real play",
                     duration_s=2.0)

    # ── 3. Video 595 animated overlay (frames at 8fps → ~7.6s) ────────────────
    print("  [3/9] Animated overlay — video 595…")
    seg_video_overlay(writer, VIDEO_595, tracks_595,
                      frame_start=120, frame_end=180,
                      display_fps=8.0,
                      clip_id="video_595",
                      show_raw_first=True)

    # ── 4. Tactical analysis cards for 595 ────────────────────────────────────
    print("  [4/9] Tactical cards — video 595…")
    voronoi_150 = EXP_595 / "level3_visualizations/voronoi_frame_video_595_150.png"
    interaction = EXP_595 / "level3_visualizations/interaction_graph.png"
    minimap = EXP_595 / "level3_spatial/minimap_tracks.png"
    storyboard = EXP_595 / "level3_visualizations/highlight_storyboard.png"

    if minimap.exists():
        seg_static_image(writer, minimap,
                         "Spatial Model — Minimap", "video_595  |  rectified top-down view",
                         duration_s=3.0)
    if voronoi_150.exists():
        seg_static_image(writer, voronoi_150,
                         "Voronoi Control — Frame 150", "video_595  |  spatial dominance per robot",
                         duration_s=3.0)
    if interaction.exists():
        seg_static_image(writer, interaction,
                         "Interaction Graph", "video_595  |  proximity and pressure between robots",
                         duration_s=3.0)

    # ── 5. Event highlight grid for 595 (4 images in 2×2, 5s) ─────────────────
    print("  [5/9] Event highlights — video 595…")
    hl_paths_595 = sorted((EXP_595 / "level3_events").glob("overlay_highlight_*.png"))
    if hl_paths_595:
        seg_highlight_grid(writer,
                           hl_paths_595[:4],
                           [p.stem.replace("overlay_highlight_", "Highlight ") for p in hl_paths_595[:4]],
                           duration_s=5.0)

    # ── 6. Video 836 section card (2s) ─────────────────────────────────────────
    print("  [6/9] Section card: video 836…")
    seg_section_card(writer,
                     "Clip Analysis — video 836",
                     "SAM3 Detection  +  ByteTrack  |  Multi-robot scene",
                     "Frames 120–180  |  ~1 second of real play",
                     duration_s=2.0)

    # ── 7. Video 836 animated overlay ─────────────────────────────────────────
    print("  [7/9] Animated overlay — video 836…")
    seg_video_overlay(writer, VIDEO_836, tracks_836,
                      frame_start=120, frame_end=180,
                      display_fps=8.0,
                      clip_id="video_836",
                      show_raw_first=True)

    # ── 8. Video 836 highlight frames (individual frames shown 2.5s each) ──────
    print("  [8/9] Highlight frames — video 836…")
    highlight_frames_836 = [125, 140, 158, 172]
    for fnum in highlight_frames_836:
        raw = extract_frame(VIDEO_836, fnum)
        if raw is None:
            continue
        ftracks = tracks_836.get(fnum, [])
        annotated = annotate_frame(raw, ftracks)
        canvas = blank()
        vid = fit_video_frame(annotated, W - 40, H - 90)
        canvas[80:80 + vid.shape[0], 20:20 + vid.shape[1]] = vid
        cv2.rectangle(canvas, (0, 0), (W, 72), (10, 18, 10), -1)
        n_robots = sum(1 for r in ftracks if "robot" in r.get("class_name", ""))
        n_balls = sum(1 for r in ftracks if "ball" in r.get("class_name", ""))
        put(canvas, f"Frame {fnum} — video_836", 20, 42,
            scale=0.85, color=GREEN_ACCENT, thickness=2)
        put(canvas, f"robots={n_robots}  balls={n_balls}  t={fnum/59.94:.2f}s",
            W - 480, 42, scale=0.65, color=GRAY, thickness=1)
        hline(canvas, 72, color=GREEN_ACCENT, thickness=2)
        write_static(writer, canvas, 2.5)

    # ── 9. Outro (4s) ──────────────────────────────────────────────────────────
    print("  [9/9] Outro…")
    seg_outro(writer)

    writer.release()
    print(f"Raw video written: {tmp_path}")

    # Re-encode with H.264 for compatibility
    print("Re-encoding to H.264…")
    result = subprocess.run(
        [
            "ffmpeg", "-y",
            "-i", str(tmp_path),
            "-vcodec", "libx264",
            "-crf", "20",
            "-preset", "fast",
            "-pix_fmt", "yuv420p",
            str(OUT_PATH),
        ],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        print("ffmpeg error:", result.stderr[-500:])
        sys.exit(1)
    tmp_path.unlink(missing_ok=True)

    # Print duration
    probe = subprocess.run(
        ["ffprobe", "-v", "quiet", "-show_entries", "format=duration",
         "-of", "csv=p=0", str(OUT_PATH)],
        capture_output=True, text=True,
    )
    duration = float(probe.stdout.strip() or 0)
    print(f"\nDone! Output: {OUT_PATH}")
    print(f"Duration: {duration:.1f}s ({duration/60:.1f} min)")
    print(f"Size: {OUT_PATH.stat().st_size / 1_000_000:.1f} MB")


if __name__ == "__main__":
    main()
