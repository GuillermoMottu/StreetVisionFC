"""
Segmentación multi-frame con Grounded-SAM (OWLv2 + SAM3).

Procesa un rango de frames de un video y guarda las detecciones en JSON
compatible con run_full_analysis.py --detections.

Usage:
    PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True \\
    python scripts/run_segment_video.py \\
      --video /ruta/video.mp4 \\
      --clip-id video_836 \\
      --start-frame 120 --end-frame 180 \\
      --out experiments/mi_analisis/detections.json

    # Con stride (procesa 1 de cada N frames — más rápido):
    python scripts/run_segment_video.py \\
      --video /ruta/video.mp4 --clip-id mi_clip \\
      --start-frame 0 --end-frame 300 --stride 5 \\
      --out experiments/mi_analisis/detections.json
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--video", required=True, help="Ruta al video a analizar")
    p.add_argument("--clip-id", default="clip", help="Identificador del clip (ej: video_836)")
    p.add_argument("--start-frame", type=int, default=0)
    p.add_argument("--end-frame", type=int, required=True)
    p.add_argument("--stride", type=int, default=1,
                   help="Procesar 1 de cada N frames (default: 1 = todos los frames)")
    p.add_argument("--out", required=True, help="Ruta de salida para detections.json")
    p.add_argument("--mask-dir", default=None,
                   help="Carpeta donde guardar las máscaras PNG (default: junto al JSON)")
    p.add_argument("--owlv2-path", default="checkpoints/owlv2-base")
    p.add_argument("--sam3-checkpoint", default=None)
    p.add_argument("--confidence", type=float, default=0.1)
    p.add_argument("--prompts", nargs="+",
                   default=["small robot", "ball", "green soccer field", "yellow goalpost"],
                   help="Prompts de texto para OWLv2")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    mask_dir = Path(args.mask_dir) if args.mask_dir else out_path.parent / "masks"

    frame_indices = list(range(args.start_frame, args.end_frame + 1, args.stride))
    total = len(frame_indices)
    print(f"Video      : {args.video}")
    print(f"Clip       : {args.clip_id}")
    print(f"Frames     : {args.start_frame}–{args.end_frame}  stride={args.stride}  total={total}")
    print(f"Prompts    : {args.prompts}")
    print(f"Output     : {out_path}")
    print(f"Máscaras   : {mask_dir}")
    print()

    from futbotmx.segmentation import GroundedSAMSegmenter
    from futbotmx.io.detections import save_detections

    print("Cargando modelos (OWLv2 + SAM3)…")
    t_load = time.monotonic()
    seg = GroundedSAMSegmenter(
        owlv2_model_path=args.owlv2_path,
        sam3_checkpoint=args.sam3_checkpoint,
        owlv2_confidence_threshold=args.confidence,
        sam3_confidence_threshold=0.05,
        mask_output_dir=str(mask_dir),
    )
    print(f"Modelos listos en {time.monotonic() - t_load:.1f}s\n")

    t_start = time.monotonic()
    all_frames = seg.segment_video(
        video_path=args.video,
        frame_indices=frame_indices,
        prompts=args.prompts,
        clip_id=args.clip_id,
    )
    elapsed = time.monotonic() - t_start

    total_dets = sum(len(fd.detections) for fd in all_frames)
    total_masks = sum(1 for fd in all_frames for d in fd.detections if d.mask_path)
    print(f"\nSegmentación completa:")
    print(f"  Frames procesados : {len(all_frames)}")
    print(f"  Detecciones total : {total_dets}")
    print(f"  Con máscara PNG   : {total_masks}")
    print(f"  Tiempo total      : {elapsed:.1f}s  ({elapsed/max(1,len(all_frames)):.2f}s/frame)")

    save_detections(all_frames, out_path)
    print(f"\nDetecciones guardadas → {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
