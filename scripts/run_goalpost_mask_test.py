"""
Test: goalpost pixel mask via box-prompt → SAM3 geometric prompt.

Run on video_836 frame 143 to validate that detect_goalposts_with_mask produces
a real pixel-level mask (mask_path populated) instead of a plain rectangle fallback.

Usage:
    python scripts/run_goalpost_mask_test.py [--video PATH] [--frame N]
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import cv2
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from futbotmx.io.detections import FrameDetections, save_detections
from futbotmx.segmentation import SAM3Segmenter, SAM3UnavailableError, detect_goalposts_with_mask

EXPERIMENT = Path("experiments/current_evaluation")
MASKS_DIR = EXPERIMENT / "masks"
CLIP_ID = "video_836"
FRAME_INDEX = 143
TEXT_PROMPTS = ["small robot", "ball", "green soccer field"]
SAM3_CHECKPOINT = "checkpoints/sam3/sam3.pt"


def load_frame(video_path: str, frame_index: int) -> Image.Image:
    cap = cv2.VideoCapture(video_path)
    cap.set(cv2.CAP_PROP_POS_FRAMES, frame_index)
    ok, bgr = cap.read()
    cap.release()
    if not ok:
        raise RuntimeError(f"Could not read frame {frame_index} from {video_path}")
    return Image.fromarray(cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB))


def main() -> int:
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--video", required=True, help="Path to video_836")
    parser.add_argument("--frame", type=int, default=FRAME_INDEX)
    args = parser.parse_args()

    MASKS_DIR.mkdir(parents=True, exist_ok=True)
    frame_index = args.frame

    print(f"[1/4] Loading frame {frame_index} from {args.video}")
    image = load_frame(args.video, frame_index)
    print(f"      Image size: {image.size}")

    print(f"[2/4] Initializing SAM3 segmenter")
    try:
        segmenter = SAM3Segmenter(
            checkpoint_path=SAM3_CHECKPOINT,
            confidence_threshold=0.5,
            mask_output_dir=MASKS_DIR,
        )
    except SAM3UnavailableError as exc:
        print(f"ERROR: SAM3 unavailable — {exc}")
        return 2

    print(f"[3/4] Running text-prompt segmentation: {TEXT_PROMPTS}")
    text_result = segmenter.segment_video(args.video, [frame_index], TEXT_PROMPTS)
    text_detections = list(text_result[0].detections) if text_result else []
    print(f"      Text detections: {len(text_detections)}")
    for d in text_detections:
        print(f"        {d.class_name:30s} conf={d.confidence:.2f}  mask={'YES' if d.mask_path else 'NO'}")

    print(f"[4/4] Running goalpost box-prompt segmentation (clip_id={CLIP_ID})")
    goalpost_result = detect_goalposts_with_mask(
        image=image,
        frame_index=frame_index,
        clip_id=CLIP_ID,
        segmenter=segmenter,
        det_idx_start=len(text_detections),
    )
    print(f"      Goalpost detections: {len(goalpost_result.detections)}")
    for d in goalpost_result.detections:
        print(f"        {d.class_name:30s} conf={d.confidence:.2f}  mask={'YES' if d.mask_path else 'NO'}")
        if d.mask_path:
            mp = Path(d.mask_path)
            if mp.exists():
                print(f"          mask file: {mp.name} ({mp.stat().st_size} bytes)")

    all_detections = text_detections + list(goalpost_result.detections)
    combined = FrameDetections(frame=frame_index, detections=tuple(all_detections))

    out_json = EXPERIMENT / f"detections_frame{frame_index}_with_goalpost_mask.json"
    save_detections([combined], out_json)
    print(f"\nSaved {len(all_detections)} detections → {out_json}")

    mask_count = sum(1 for d in all_detections if d.mask_path)
    print(f"Masks populated: {mask_count}/{len(all_detections)}")

    if mask_count == len(all_detections):
        print("\n[PASS] All detections have pixel-level masks including goalpost.")
        return 0
    else:
        no_mask = [d.class_name for d in all_detections if not d.mask_path]
        print(f"\n[PARTIAL] Classes without mask: {no_mask}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
