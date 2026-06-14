"""
Generate a composite overlay visualization from detection JSON + mask PNGs.

Draws semi-transparent colored overlays for each detection's pixel mask (if present),
plus bounding boxes and class labels.  Used to visually verify Phase 2 results.

Usage:
    python scripts/visualize_detections.py \
        --video /path/to/video.mov \
        --detections experiments/current_evaluation/detections_frame143_with_goalpost_mask.json \
        --frame 143 \
        --out experiments/current_evaluation/masks/visualization_frame143_v2.png
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from futbotmx.io.detections import load_detections

CLASS_COLORS: dict[str, tuple[int, int, int]] = {
    "small_robot":        (0,   200, 50),
    "ball":               (255, 165,  0),
    "green_soccer_field": (50,   50, 200),
    "goalpost":           (255, 255,   0),
}
DEFAULT_COLOR = (180, 180, 180)
MASK_ALPHA = 0.40


def load_frame(video_path: str, frame_index: int) -> np.ndarray:
    cap = cv2.VideoCapture(video_path)
    cap.set(cv2.CAP_PROP_POS_FRAMES, frame_index)
    ok, bgr = cap.read()
    cap.release()
    if not ok:
        raise RuntimeError(f"Could not read frame {frame_index} from {video_path}")
    return cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--video", required=True)
    parser.add_argument("--detections", required=True)
    parser.add_argument("--frame", type=int, default=143)
    parser.add_argument("--out", default="experiments/current_evaluation/masks/visualization_frame143_v2.png")
    args = parser.parse_args()

    print(f"Loading frame {args.frame} from {args.video}")
    frame_rgb = load_frame(args.video, args.frame)
    canvas = frame_rgb.copy().astype(np.float32)
    h, w = canvas.shape[:2]

    frame_detections = load_detections(Path(args.detections))
    target = next((fd for fd in frame_detections if fd.frame == args.frame), None)
    if target is None:
        print(f"No detections for frame {args.frame} in {args.detections}")
        return 1

    print(f"Rendering {len(target.detections)} detections:")
    for det in target.detections:
        color_f = tuple(c / 255.0 for c in CLASS_COLORS.get(det.class_name, DEFAULT_COLOR))
        color_i = CLASS_COLORS.get(det.class_name, DEFAULT_COLOR)

        # --- pixel mask overlay ---
        if det.mask_path and Path(det.mask_path).exists():
            mask_img = np.array(Image.open(det.mask_path).convert("L"))
            if mask_img.shape != (h, w):
                mask_img = cv2.resize(mask_img, (w, h), interpolation=cv2.INTER_NEAREST)
            binary = (mask_img > 127).astype(np.float32)
            for c_idx, c_val in enumerate(color_i):
                canvas[:, :, c_idx] = np.where(
                    binary > 0,
                    canvas[:, :, c_idx] * (1 - MASK_ALPHA) + c_val * MASK_ALPHA,
                    canvas[:, :, c_idx],
                )
            mask_source = "mask"
        else:
            mask_source = "bbox-only"

        # --- bounding box ---
        x0, y0, x1, y1 = (int(v) for v in det.bbox)
        overlay_u8 = np.clip(canvas, 0, 255).astype(np.uint8)
        cv2.rectangle(overlay_u8, (x0, y0), (x1, y1), color_i, 2)

        # --- label ---
        label = f"{det.class_name} {det.confidence:.2f} [{mask_source}]"
        (tw, th), bl = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.45, 1)
        cv2.rectangle(overlay_u8, (x0, y0 - th - bl - 4), (x0 + tw + 4, y0), color_i, -1)
        cv2.putText(overlay_u8, label, (x0 + 2, y0 - bl - 2),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 0), 1, cv2.LINE_AA)
        canvas = overlay_u8.astype(np.float32)

        print(f"  {det.class_name:30s} conf={det.confidence:.2f} [{mask_source}]")

    result = np.clip(canvas, 0, 255).astype(np.uint8)
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(result).save(str(out_path))
    print(f"\nSaved visualization → {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
