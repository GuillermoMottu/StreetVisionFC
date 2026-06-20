"""
Segmentación multi-frame con Grounded-SAM (OWLv2 + SAM3).

Procesa un rango de frames de un video y guarda las detecciones en JSON
compatible con run_full_analysis.py --detections.

El pipeline aplica NMS por clase después de OWLv2 para eliminar detecciones
duplicadas del mismo objeto.  Los parámetros recomendados para partidos con
1-3 robots son:
  --confidence 0.20 --nms-iou 0.30 --max-robots 3 --max-balls 2

Usage:
    PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True \\
    python scripts/run_segment_video.py \\
      --video /ruta/video.mp4 \\
      --clip-id video_692 \\
      --start-frame 400 --end-frame 700 \\
      --confidence 0.20 --nms-iou 0.30 --max-robots 3 --max-balls 2 \\
      --out experiments/seg_video_692/detections.json

    # Con stride (procesa 1 de cada N frames — más rápido):
    python scripts/run_segment_video.py \\
      --video /ruta/video.mp4 --clip-id mi_clip \\
      --start-frame 0 --end-frame 300 --stride 5 \\
      --confidence 0.20 --nms-iou 0.30 --max-robots 3 --max-balls 2 \\
      --out experiments/mi_analisis/detections.json
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path
from typing import Any

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
    p.add_argument("--confidence", type=float, default=0.20,
                   help="Umbral de confianza OWLv2 (default: 0.20 — sube si hay demasiados falsos positivos)")
    p.add_argument("--nms-iou", type=float, default=0.30,
                   help="Umbral IoU para NMS por clase (default: 0.30 — baja para eliminar más duplicados)")
    p.add_argument("--max-robots", type=int, default=3,
                   help="Máximo de robots a conservar por frame tras NMS (default: 3)")
    p.add_argument("--max-balls", type=int, default=2,
                   help="Máximo de balones a conservar por frame tras NMS (default: 2)")
    p.add_argument("--max-goalposts", type=int, default=2,
                   help="Máximo de porterías a conservar por frame tras NMS (default: 2)")
    p.add_argument("--min-mask-ratio", type=float, default=0.5,
                   help="Fraccion minima de detecciones de objetos que deben tener mascara PNG")
    p.add_argument("--allow-bbox-only", action="store_true",
                   help="Permite terminar con exito aunque SAM3 no haya generado suficientes mascaras")
    p.add_argument("--prompts", nargs="+",
                   default=["small robot", "ball", "green soccer field", "yellow goalpost"],
                   help="Prompts de texto para OWLv2")
    return p.parse_args()


def mask_quality_summary(frames: list[Any]) -> dict[str, float | int]:
    total = 0
    required = 0
    with_masks = 0
    for frame in frames:
        for det in frame.detections:
            total += 1
            class_name = str(det.class_name)
            if "field" in class_name:
                continue
            required += 1
            if det.mask_path:
                with_masks += 1
    ratio = with_masks / required if required else 1.0
    return {"total": total, "required": required, "with_masks": with_masks, "ratio": ratio}


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
    from futbotmx.io.detections import save_detections, deduplicate_detections

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
    print(f"NMS IoU    : {args.nms_iou}  |  max robots={args.max_robots}  balls={args.max_balls}  goals={args.max_goalposts}\n")

    t_start = time.monotonic()
    all_frames = seg.segment_video(
        video_path=args.video,
        frame_indices=frame_indices,
        prompts=args.prompts,
        clip_id=args.clip_id,
    )
    elapsed = time.monotonic() - t_start

    raw_dets = sum(len(fd.detections) for fd in all_frames)

    # Apply per-class NMS and top-k cap to remove duplicate detections of the same object.
    top_k: dict[str, int] = {}
    for prompt in args.prompts:
        cls = prompt.replace(" ", "_")
        if "robot" in cls:
            top_k[cls] = args.max_robots
        elif "ball" in cls:
            top_k[cls] = args.max_balls
        elif "goalpost" in cls:
            top_k[cls] = args.max_goalposts
    all_frames = deduplicate_detections(all_frames, iou_threshold=args.nms_iou, top_k_by_class=top_k)

    total_dets = sum(len(fd.detections) for fd in all_frames)
    total_masks = sum(1 for fd in all_frames for d in fd.detections if d.mask_path)
    print(f"  Detecciones antes NMS : {raw_dets}")
    print(f"  Detecciones tras NMS  : {total_dets}  (eliminadas: {raw_dets - total_dets})")
    quality = mask_quality_summary(all_frames)
    print(f"\nSegmentación completa:")
    print(f"  Frames procesados : {len(all_frames)}")
    print(f"  Detecciones total : {total_dets}  (antes NMS: {raw_dets})")
    print(f"  Con máscara PNG   : {total_masks}")
    print(
        "  Objetos con máscara: "
        f"{quality['with_masks']}/{quality['required']} ({float(quality['ratio']):.1%})"
    )
    print(f"  Tiempo total      : {elapsed:.1f}s  ({elapsed/max(1,len(all_frames)):.2f}s/frame)")

    save_detections(all_frames, out_path)
    print(f"\nDetecciones guardadas → {out_path}")
    if total_dets == 0:
        print("ERROR: segmentación sin detecciones.", file=sys.stderr)
        return 1
    if not args.allow_bbox_only and float(quality["ratio"]) < args.min_mask_ratio:
        print(
            "ERROR: demasiadas detecciones quedaron sin máscara "
            f"({float(quality['ratio']):.1%} < {args.min_mask_ratio:.1%}). "
            "Usa --allow-bbox-only solo para diagnóstico.",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
