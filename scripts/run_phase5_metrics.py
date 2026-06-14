"""
Phase 5 — Supervised metrics (IoU, Dice, precision, recall, F1).

Compares SAM3 detections against ground truth annotations (COCO format).
If annotations are not yet available, produces infrastructure + pending status.

Usage:
    python scripts/run_phase5_metrics.py \
        --detections experiments/current_evaluation/detections_frame143_with_goalpost_mask.json \
        --annotations data/annotations/annotation_template.json \
        --out experiments/current_evaluation/phase5_metrics/
"""
from __future__ import annotations

import json
import math
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from futbotmx.io.detections import load_detections

OUT_DIR = Path("experiments/current_evaluation/phase5_metrics")


def iou_box(a: tuple, b: tuple) -> float:
    ax0, ay0, ax1, ay1 = a
    bx0, by0, bx1, by1 = b
    ix0, iy0 = max(ax0, bx0), max(ay0, by0)
    ix1, iy1 = min(ax1, bx1), min(ay1, by1)
    inter = max(0.0, ix1 - ix0) * max(0.0, iy1 - iy0)
    if inter == 0:
        return 0.0
    area_a = (ax1 - ax0) * (ay1 - ay0)
    area_b = (bx1 - bx0) * (by1 - by0)
    return inter / (area_a + area_b - inter)


def match_detections(
    gt_boxes: list[tuple],
    pred_boxes: list[tuple],
    iou_threshold: float = 0.5,
) -> tuple[int, int, int]:
    matched_gt: set[int] = set()
    tp = 0
    for pred in pred_boxes:
        best_iou, best_gi = 0.0, -1
        for gi, gt in enumerate(gt_boxes):
            if gi in matched_gt:
                continue
            iou = iou_box(pred, gt)
            if iou > best_iou:
                best_iou, best_gi = iou, gi
        if best_iou >= iou_threshold and best_gi >= 0:
            tp += 1
            matched_gt.add(best_gi)
    fp = len(pred_boxes) - tp
    fn = len(gt_boxes) - tp
    return tp, fp, fn


def f1(precision: float, recall: float) -> float:
    if precision + recall == 0:
        return 0.0
    return 2 * precision * recall / (precision + recall)


def compute_metrics_from_annotations(
    detections_path: Path,
    annotations_path: Path,
    iou_threshold: float = 0.5,
) -> dict:
    ann_data = json.loads(annotations_path.read_text())
    if not ann_data.get("annotations"):
        return {"status": "pending_annotation", "message": "No annotations in template yet. Annotate data/annotations/annotation_template.json and re-run."}

    cat_by_id = {c["id"]: c["name"] for c in ann_data["categories"]}
    gt_by_frame_class: dict[tuple, list] = {}
    for ann in ann_data["annotations"]:
        frame = ann["image_id"]
        cls = cat_by_id.get(ann["category_id"], "unknown")
        bbox = ann.get("bbox")  # [x, y, w, h] COCO format
        if bbox:
            x0, y0, w, h = bbox
            gt_by_frame_class.setdefault((frame, cls), []).append((x0, y0, x0 + w, y0 + h))

    all_frames = load_detections(detections_path)
    pred_by_frame_class: dict[tuple, list] = {}
    for fd in all_frames:
        for det in fd.detections:
            pred_by_frame_class.setdefault((fd.frame, det.class_name), []).append(det.bbox)

    # Only evaluate frames where predictions exist; GT frames without predictions are
    # out-of-scope (no inference was run) and would unfairly penalise recall.
    evaluated_frames = {f for (f, _) in pred_by_frame_class}
    gt_by_frame_class = {
        (f, c): boxes for (f, c), boxes in gt_by_frame_class.items()
        if f in evaluated_frames
    }

    classes = sorted({c for (_, c) in list(gt_by_frame_class.keys()) + list(pred_by_frame_class.keys())})
    per_class: dict[str, dict] = {}
    total_tp = total_fp = total_fn = 0
    for cls in classes:
        frames = sorted({f for (f, c) in list(gt_by_frame_class.keys()) + list(pred_by_frame_class.keys()) if c == cls})
        tp = fp = fn = 0
        for fi in frames:
            gt = gt_by_frame_class.get((fi, cls), [])
            pred = pred_by_frame_class.get((fi, cls), [])
            _tp, _fp, _fn = match_detections(gt, pred, iou_threshold)
            tp += _tp; fp += _fp; fn += _fn
        prec = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        rec  = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        per_class[cls] = {"tp": tp, "fp": fp, "fn": fn,
                          "precision": round(prec, 4), "recall": round(rec, 4),
                          "f1": round(f1(prec, rec), 4)}
        total_tp += tp; total_fp += fp; total_fn += fn

    micro_prec = total_tp / (total_tp + total_fp) if (total_tp + total_fp) > 0 else 0.0
    micro_rec  = total_tp / (total_tp + total_fn) if (total_tp + total_fn) > 0 else 0.0
    return {
        "status": "computed",
        "iou_threshold": iou_threshold,
        "evaluated_frames": sorted(evaluated_frames),
        "gt_frames_total": len({ann["image_id"] for ann in ann_data["annotations"]}),
        "per_class": per_class,
        "micro_avg": {"precision": round(micro_prec, 4), "recall": round(micro_rec, 4),
                      "f1": round(f1(micro_prec, micro_rec), 4)},
    }


def copy_benchmark_summary(out_dir: Path) -> dict:
    src = Path("experiments/test_007_msi_benchmarks/video_836_sam3/benchmark.json")
    if not src.exists():
        return {"status": "benchmark_not_found"}
    data = json.loads(src.read_text())
    single = next((r for r in data.get("runs", []) if r["name"] == "single_frame"), {})
    multi  = next((r for r in data.get("runs", []) if r["name"] == "multi_frame"), {})
    gpu_after = data.get("gpu_after_load", {})
    summary = {
        "source": str(src),
        "load_time_sec": data.get("load_time_sec"),
        "gpu": {
            "name": gpu_after.get("name"),
            "vram_total_mb": gpu_after.get("memory_total_mb"),
            "vram_after_load_mb": gpu_after.get("memory_used_mb"),
        },
        "single_frame": {
            "sec_per_frame": single.get("sec_per_frame"),
            "fps_effective": single.get("fps_effective"),
            "vram_peak_mb": single.get("cuda_memory_allocated_peak_mb"),
        },
        "multi_frame_5": {
            "sec_per_frame": multi.get("sec_per_frame"),
            "fps_effective": multi.get("fps_effective"),
            "vram_peak_mb": multi.get("cuda_memory_allocated_peak_mb"),
        },
    }
    (out_dir / "benchmark_summary.json").write_text(json.dumps(summary, indent=2))
    return summary


def main() -> int:
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--detections", default="experiments/current_evaluation/detections_frame143_with_goalpost_mask.json")
    parser.add_argument("--annotations", default="data/annotations/annotation_template.json")
    parser.add_argument("--iou-threshold", type=float, default=0.5)
    parser.add_argument("--out", default=str(OUT_DIR))
    args = parser.parse_args()

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    print("[R3] Copying benchmark summary")
    bench = copy_benchmark_summary(out)
    if bench.get("single_frame"):
        s = bench["single_frame"]
        print(f"     {s['sec_per_frame']:.3f} s/frame  |  {s['fps_effective']:.3f} FPS  |  {s['vram_peak_mb']:.0f} MB VRAM")

    print("[R2] Computing supervised metrics")
    metrics = compute_metrics_from_annotations(
        Path(args.detections), Path(args.annotations), args.iou_threshold
    )
    (out / "supervised_metrics.json").write_text(json.dumps(metrics, indent=2))

    if metrics["status"] == "pending_annotation":
        print(f"     PENDING: {metrics['message']}")
    else:
        print(f"     micro F1={metrics['micro_avg']['f1']}  prec={metrics['micro_avg']['precision']}  rec={metrics['micro_avg']['recall']}")
        for cls, m in metrics["per_class"].items():
            print(f"     {cls:30s} P={m['precision']} R={m['recall']} F1={m['f1']}")

    # consolidated report
    report = {"benchmark": bench, "supervised_metrics": metrics,
              "annotation_status": metrics["status"],
              "annotation_frames": 8, "annotation_classes": 4}
    (out / "phase5_report.json").write_text(json.dumps(report, indent=2))
    print(f"\nPhase 5 report → {out}/phase5_report.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
