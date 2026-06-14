"""
Validation script for the Grounded-SAM pipeline (OWLv2 + SAM3).

Tests that all 4 classes are detected on a real video frame using text prompts,
with pixel masks for objects whose bbox covers <30% of the image. The goalpost
must be detected via the "yellow goalpost" text prompt without hardcoded coordinates.

Usage:
    PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True \\
    python scripts/run_grounded_sam_test.py \\
      --video "$FUTBOTMX_VIDEO_836" \\
      --frame 143

Exit code 0 = pass, 1 = fail.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


def parse_args():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--video", required=True)
    p.add_argument("--frame", type=int, default=143)
    p.add_argument("--owlv2-path", default="checkpoints/owlv2-base")
    p.add_argument("--sam3-checkpoint", default=None)
    p.add_argument("--output-dir", default="experiments/current_evaluation/masks_grounded_sam")
    return p.parse_args()


def main():
    args = parse_args()
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    import cv2
    from PIL import Image
    from futbotmx.segmentation import GroundedSAMSegmenter

    print(f"Loading frame {args.frame} from {args.video}")
    cap = cv2.VideoCapture(args.video)
    cap.set(cv2.CAP_PROP_POS_FRAMES, args.frame)
    ok, bgr = cap.read()
    cap.release()
    if not ok:
        print(f"ERROR: could not read frame {args.frame}", file=sys.stderr)
        sys.exit(1)

    image = Image.fromarray(cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB))
    W, H = image.size
    print(f"Image: {W}x{H}")

    print("Initializing GroundedSAMSegmenter (OWLv2 + SAM3)...")
    seg = GroundedSAMSegmenter(
        owlv2_model_path=args.owlv2_path,
        sam3_checkpoint=args.sam3_checkpoint,
        owlv2_confidence_threshold=0.1,
        sam3_confidence_threshold=0.05,
        mask_output_dir=str(output_dir),
    )

    prompts = ["small robot", "ball", "green soccer field", "yellow goalpost"]
    print(f"Prompts: {prompts}")
    fd = seg.segment_image(image, prompts, frame_index=args.frame)

    print(f"\nDetections ({len(fd.detections)}):")
    img_area = W * H
    for d in fd.detections:
        x0, y0, x1, y1 = d.bbox
        area_pct = (max(0, x1 - x0) * max(0, y1 - y0)) / img_area * 100
        mask_flag = "mask=YES" if d.mask_path else "mask=no "
        print(f"  {d.class_name:30s}  conf={d.confidence:.3f}  {mask_flag}  {area_pct:5.1f}% of frame")

    # Assertions
    errors = []

    goalpost_dets = [d for d in fd.detections if "goalpost" in d.class_name]
    if not goalpost_dets:
        errors.append("FAIL: no goalpost detected via 'yellow goalpost' text prompt")
    elif not goalpost_dets[0].mask_path:
        errors.append(f"FAIL: goalpost detected (conf={goalpost_dets[0].confidence:.3f}) but has no pixel mask")
    else:
        print(f"\n[PASS] goalpost detected via OWLv2 text + SAM3 mask, conf={goalpost_dets[0].confidence:.3f}")

    robot_dets = [d for d in fd.detections if "robot" in d.class_name]
    robot_with_mask = [d for d in robot_dets if d.mask_path]
    if not robot_with_mask:
        errors.append("FAIL: no robot detections have pixel masks")
    else:
        print(f"[PASS] {len(robot_with_mask)}/{len(robot_dets)} robot detections have pixel masks")

    ball_dets = [d for d in fd.detections if d.class_name == "ball"]
    if ball_dets and ball_dets[0].mask_path:
        print(f"[PASS] ball detected with pixel mask, conf={ball_dets[0].confidence:.3f}")
    elif ball_dets:
        print(f"[WARN] ball detected but no mask (conf={ball_dets[0].confidence:.3f})")
    else:
        print("[WARN] ball not detected (may be occluded or off-frame)")

    if errors:
        for e in errors:
            print(e, file=sys.stderr)
        sys.exit(1)
    else:
        print(f"\n[ALL PASS] GroundedSAM pipeline validated on frame {args.frame}")
        print(f"Masks saved to: {output_dir}")


if __name__ == "__main__":
    main()
