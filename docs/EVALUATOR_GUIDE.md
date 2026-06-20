# Evaluator Guide — FutBotMX / StreetVisionFC

Quick access to demo, metrics, and evidence in under 5 minutes.

---

## 1. Demo video (start here)

```
outputs/videos/futbotmx_demo_h264.mp4
```

H.264, 46.6 s, 2.3 MB. This MP4 is versioned in the public repository. Five sections: raw video, segmentation overlays, tracking paths, team assignment, and benchmark summary. Play with any video player.

Instagram Reel: https://www.instagram.com/reel/DZynpB2pH_L_Mxq8V9Iq3bN5WHSFDGvsy_17iw0/?igsh=dnZ6MnlyYm13ZWV2

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
| Test suite | **461 tests pass** | `python -m unittest discover -s tests` |

Professional-category rubric map: `docs/PROFESSIONAL_EVALUATION.md`.

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
| Public demo video | `outputs/videos/futbotmx_demo_h264.mp4` |
| Instagram Reel | `https://www.instagram.com/reel/DZynpB2pH_L_Mxq8V9Iq3bN5WHSFDGvsy_17iw0/?igsh=dnZ6MnlyYm13ZWV2` |
| Heatmap screenshot | `outputs/visualizations/heatmap.png` |
| All artefacts index | `ARTIFACTS_INDEX.md` |

---

## 4. Full pipeline — analyze any video (recommended entry point)

```bash
source .venv/bin/activate

# Single command: Grounded-SAM segmentation → tracking → Level3 analytics → browser UI
PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True \
python scripts/run_unified_analysis.py \
  --video /path/to/your_video.mp4 \
  --clip-id my_clip \
  --start-frame 0 --end-frame 300

# The unified local frontend serves the playback at http://127.0.0.1:8765/playback/ with:
#   - Synchronized video + bounding-box overlay
#   - Voronoi minimap (field zones, team control)
#   - Interaction graph (robot-robot / robot-ball events)
#   - Level3 events timeline (possession, proximity, shots)
#   - Dashboard and storyboard
```

Flags:
- `--stride N` — process 1 every N frames (faster, e.g. `--stride 5`)
- `--detections path/detections.json` — reuse existing detections, skip Grounded-SAM
- `--skip-analysis` — relaunch the browser app without re-running the pipeline
- `--allow-gpu` — enable GPU-gated live inference modes in the playback app

---

## 5. Run the validation scripts

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

## 6. Architecture in one paragraph

Video frames are decoded with OpenCV. A **Grounded-SAM** pipeline (OWLv2 zero-shot text→bbox + SAM3 bbox→pixel mask) detects four classes: `small_robot`, `ball`, `green_soccer_field`, `yellow_goalpost`. Detections are fed to **ByteTrack** for multi-object tracking across 61 dense frames. Tracks are labelled by team using an **initial-side heuristic** (x-axis at first observation). The goalpost uses OWLv2 text detection for video\_836/667; clips where OWLv2 fails (video\_595) fall back to HSV-confirmed bounding boxes. Full architecture: `docs/TECHNICAL_ARCHITECTURE.md`. Segmentation details: `docs/SAM3_PIPELINE.md`.

---

## 7. Ground-truth annotation source

49 human annotations (Roboflow, 2026-06-14) across 8 frames of video_836.
Source: `data/annotations/train_COCO/_annotations.coco.json`
Converted template: `data/annotations/annotation_template.json`

To re-run metrics from scratch:
```bash
python scripts/run_phase5_metrics.py
```
