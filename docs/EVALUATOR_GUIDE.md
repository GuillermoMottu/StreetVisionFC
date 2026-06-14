# Evaluator Guide — FutBotMX / StreetVisionFC

Quick access to demo, metrics, and evidence in under 5 minutes.

---

## 1. Demo video (start here)

```
outputs/videos/futbotmx_demo_h264.mp4
```

H.264, 46.6 s, 2.3 MB. Five sections: raw video, segmentation overlays, tracking paths, team assignment, and benchmark summary. Play with any video player.

---

## 2. Key results at a glance

| Metric | Value | Source |
|---|---|---|
| Inference (single frame) | **2.237 s/frame — 0.447 FPS** | `phase5_metrics/benchmark_summary.json` |
| Inference (batched ×5) | **1.203 s/frame — 0.831 FPS** | same |
| VRAM peak | **3878 MB** | same |
| Model load time | 15.6 s (one-time) | same |
| Tracking frames validated | 61 frames (120–180) | `tracks_bytetrack_with_teams.csv` |
| Robots tracked | 3 (robot\_bt\_01, 02, 03) | ByteTrack, video\_836 |
| Team assignment confidence | 0.64 (initial-side method) | `team_assignment_summary.json` |
| Supervised IoU/F1 | **micro F1=0.857 · P=0.75 · R=1.00** | `supervised_metrics.json` |
| Test suite | **425 tests pass** | `python -m unittest discover -s tests` |

---

## 3. Evidence files

| Artefact | Path |
|---|---|
| Pixel masks (SAM3) | `experiments/current_evaluation/masks/` |
| Grounded-SAM masks (OWLv2+SAM3) | `experiments/current_evaluation/masks_grounded_sam/` |
| ByteTrack CSV with teams | `experiments/current_evaluation/phase4_team_assignment/tracks_bytetrack_with_teams.csv` |
| Robot contactsheet | `experiments/current_evaluation/phase4_team_assignment/robot_contactsheet.png` |
| Benchmark JSON | `experiments/current_evaluation/phase5_metrics/benchmark_summary.json` |
| Annotation frames (8 PNGs) | `data/annotations/frames/` |
| COCO template | `data/annotations/annotation_template.json` |
| All artefacts index | `ARTIFACTS_INDEX.md` |

---

## 4. Run the validation scripts

```bash
# Activate environment
source .venv/bin/activate

# Run test suite
python -m unittest discover -s tests -q

# Re-run segmentation + masks on a single frame
PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True \
python scripts/run_grounded_sam_test.py \
  --video "$FUTBOTMX_VIDEO_836" --frame 143

# Re-run goalpost mask test (SAM3 box-prompt)
python scripts/run_goalpost_mask_test.py \
  --video "$FUTBOTMX_VIDEO_836"

# Regenerate benchmark
python scripts/run_phase5_metrics.py

# Regenerate demo video
python scripts/create_phase3_demo.py \
  --video "$FUTBOTMX_VIDEO_836"
```

---

## 5. Architecture in one paragraph

Video frames are decoded with OpenCV. A **Grounded-SAM** pipeline (OWLv2 zero-shot text→bbox + SAM3 bbox→pixel mask) detects four classes: `small_robot`, `ball`, `green_soccer_field`, `yellow_goalpost`. Detections are fed to **ByteTrack** for multi-object tracking across 61 dense frames. Tracks are labelled by team using an **initial-side heuristic** (x-axis at first observation). The goalpost uses OWLv2 text detection for video\_836/667; clips where OWLv2 fails (video\_595) fall back to HSV-confirmed bounding boxes. Full architecture: `docs/TECHNICAL_ARCHITECTURE.md`. Segmentation details: `docs/SAM3_PIPELINE.md`.

---

## 6. Ground-truth annotation source

49 human annotations (Roboflow, 2026-06-14) across 8 frames of video_836.
Source: `data/annotations/train_COCO/_annotations.coco.json`
Converted template: `data/annotations/annotation_template.json`

To re-run metrics from scratch:
```bash
python scripts/run_phase5_metrics.py
```
