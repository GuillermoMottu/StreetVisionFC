# Results Summary — FutBotMX / StreetVisionFC

Final pipeline results as of 2026-06-14. Supervised metrics computed against
real human annotations (Roboflow, 49 annotations across 8 frames).

---

## R1. Benchmark (SAM3, RTX 4050 Laptop, CUDA 13.0)

| Metric | Value |
|---|---|
| GPU | NVIDIA GeForce RTX 4050 Laptop GPU |
| VRAM total | 6141 MB |
| VRAM after model load | 3626 MB |
| Model load time | 15.57 s (one-time) |
| **Inference — single frame** | **2.237 s/frame — 0.447 FPS** |
| **Inference — batched ×5** | **1.203 s/frame — 0.831 FPS** |
| VRAM peak (inference) | 3878 MB |

Source: `experiments/test_007_msi_benchmarks/video_836_sam3/benchmark.json`

---

## R2. Tracking results (video\_836, frames 120–180)

| Metric | Value |
|---|---|
| Frames analyzed | 61 (frames 120 to 180) |
| Tracker | ByteTrack |
| Tracks detected | 3 robots (`robot_bt_01`, `robot_bt_02`, `robot_bt_03`) |
| Track rows | 205 |
| Team assignment method | `initial_side_fallback` (x\_norm at first observation) |
| Team assignment confidence | 0.64 |
| Human validation | Confirmed 2026-06-13 ("Es correcta la asignación de equipos") |

Team assignments:

| Track ID | Team |
|---|---|
| robot\_bt\_01 | team\_right |
| robot\_bt\_02 | team\_left |
| robot\_bt\_03 | team\_left |

Source: `experiments/current_evaluation/phase4_team_assignment/tracks_bytetrack_with_teams.csv`

---

## R3. Segmentation coverage (frame 143, video\_836, Grounded-SAM)

| Class | Detected | Has pixel mask |
|---|---|---|
| small\_robot | 7 detections | 7/7 (OWLv2 + SAM3 box-prompt) |
| ball | 1 detection | 1/1 |
| yellow\_goalpost | 1 detection, conf=0.108 | 1/1 |
| green\_soccer\_field | 2 detections | 0/2 (bbox area >30%, SAM3 skipped) |

Source: `experiments/current_evaluation/masks_grounded_sam/`

---

## R4. Goalpost detection — multi-clip

| Clip | OWLv2 detected | Pixel mask |
|---|---|---|
| video\_836 | YES, conf=0.108 | YES (SAM3 box-prompt) |
| video\_667 | YES, conf=0.089, 6/7 frames | YES (SAM3 box-prompt) |
| video\_595 | NO in frames 120-180 | NO — falls back to `_CLIP_GOALS` bbox |

---

## R5. Supervised metrics (IoU@0.5, frame 143)

Ground truth: **49 human annotations** (Roboflow) across 8 frames (120–180).
Evaluation frame: **143** (only frame with pipeline predictions).
Source: `data/annotations/train_COCO/_annotations.coco.json` → `data/annotations/annotation_template.json`

| Class | GT boxes | Pred boxes | TP | FP | FN | Precision | Recall | F1 |
|---|---|---|---|---|---|---|---|---|
| small\_robot | 3 | 5 | 3 | 2 | 0 | 0.60 | 1.00 | **0.75** |
| ball | 1 | 1 | 1 | 0 | 0 | 1.00 | 1.00 | **1.00** |
| green\_soccer\_field | 1 | 1 | 1 | 0 | 0 | 1.00 | 1.00 | **1.00** |
| goalpost | 1 | 1 | 1 | 0 | 0 | 1.00 | 1.00 | **1.00** |
| **Micro avg** | **6** | **8** | **6** | **2** | **0** | **0.75** | **1.00** | **0.857** |

**Recall = 1.00** — every human-labeled object in frame 143 was detected.  
**2 FP on small\_robot**: overlapping box on center-right robot cluster + 1 detection above the playing field.

Source: `experiments/current_evaluation/phase5_metrics/supervised_metrics.json`

---

## R6. Test suite

```
python -m unittest discover -s tests -q
425 tests: PASS  0 FAIL
```

---

## R7. Dependencies

18 pinned packages. See `requirements-gpu.txt`.
Key additions in this phase: `transformers==5.12.0` (OWLv2 support).

---

## Known limitations

| Limitation | Impact |
|---|---|
| Not real-time (0.45 FPS) | Offline analysis only; not suitable for live refereeing |
| Metrics on 1/8 frames only | Recall/F1 reflect frame 143; full 8-frame evaluation requires multi-frame inference |
| video\_595 goalpost no mask | Plain bbox fallback; confidence=0.0 |
| Team assignment heuristic | Confidence=0.64; not applicable if robots swap sides |
| Green field no pixel mask | OWLv2 bbox used; enough for ROI, not for area measurement |
