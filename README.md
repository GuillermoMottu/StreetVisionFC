# FutBotMX / StreetVisionFC

Computer-vision pipeline for robot soccer video analysis.
Detects robots, ball, and goalpost; tracks multi-object motion; assigns teams; generates demo video.

---

## Quick start for evaluators

```
outputs/videos/futbotmx_demo_h264.mp4       ← public demo video (H.264, 46.6 s, 2.3 MB)
docs/PROFESSIONAL_EVALUATION.md             ← rubric mapping for Categoría Profesional
docs/EVALUATOR_GUIDE.md                     ← evidence map and key metrics
docs/RESULTS_SUMMARY.md                     ← benchmark, tracking, segmentation results
```

Instagram Reel: https://www.instagram.com/reel/DZynpB2pH_L_Mxq8V9Iq3bN5WHSFDGvsy_17iw0/?igsh=dnZ6MnlyYm13ZWV2

---

## Architecture

```
Video → OWLv2 (text→bbox) → SAM3 (bbox→mask) → ByteTrack → Level3 Analytics → Demo Video
```

- **OWLv2** (`google/owlv2-base-patch16-ensemble`): zero-shot object detection from text prompts
- **SAM3** (`checkpoints/sam3/sam3.pt`): pixel-level segmentation from geometric box prompts
- **ByteTrack**: multi-object tracking across 61 dense frames
- **Level3 analytics**: team assignment, possession candidates, speed/proximity events, Voronoi control, minimap, interaction graph, dashboard
- **Team assignment**: initial-side heuristic (x-axis), confidence 0.64, human-validated

Full architecture: [docs/TECHNICAL_ARCHITECTURE.md](docs/TECHNICAL_ARCHITECTURE.md)
Segmentation details: [docs/SAM3_PIPELINE.md](docs/SAM3_PIPELINE.md)
Professional evaluation evidence: [docs/PROFESSIONAL_EVALUATION.md](docs/PROFESSIONAL_EVALUATION.md)

---

## Competition compliance

| Requirement from the call | Status | Evidence |
|---|---|---|
| SAM 3-based segmentation of field, robots, ball and goalpost | Complete | `src/futbotmx/segmentation/`, `docs/SAM3_PIPELINE.md` |
| Tracking trajectories through video | Complete | ByteTrack integration in `src/futbotmx/tracking/`, `outputs/tracking/tracks.csv` |
| Key event detection | Complete | `src/futbotmx/events/`, `src/futbotmx/level3/advanced_events.py` |
| Data visualization and match narrative | Complete | heatmap, Voronoi, minimap, dashboard and storyboard in `src/futbotmx/level3/` |
| Demo video under 2 minutes | Complete | `outputs/videos/futbotmx_demo_h264.mp4`, 46.6 s |
| Instagram Reel public link | Complete | https://www.instagram.com/reel/DZynpB2pH_L_Mxq8V9Iq3bN5WHSFDGvsy_17iw0/?igsh=dnZ6MnlyYm13ZWV2 |
| Installation, reproduction, hardware/software requirements | Complete | this README and `docs/REPRODUCIBILITY.md` |
| License and third-party credits | Complete | `LICENSE`, `THIRD_PARTY_NOTICES.md` |

For the professional-category rubric, this solution emphasizes innovation through a Grounded-SAM pipeline: OWLv2 proposes open-vocabulary boxes, SAM 3 converts those boxes into masks, and the pipeline adds VRAM-aware model offloading, goalpost fallback logic, ByteTrack integration, quantitative validation and Level3 tactical analytics.

---

## Environment

| Component | Value |
|---|---|
| GPU | NVIDIA GeForce RTX 4050 Laptop (6141 MB VRAM) |
| CUDA | 13.0 |
| Python | 3.14.4 |
| PyTorch | 2.12.0+cu130 |
| OS | Ubuntu 24.04 |

---

## Installation

```bash
# 1. Create virtual environment
python3.14 -m venv .venv
source .venv/bin/activate

# 2. Install PyTorch (CUDA 13.0)
pip install torch==2.12.0 torchvision==0.27.0 \
  --index-url https://download.pytorch.org/whl/cu130

# 3. Install dependencies
pip install -r requirements-gpu.txt

# 4. Install SAM3 from source
mkdir -p .deps
git clone https://github.com/facebookresearch/sam3 .deps/sam3
pip install -e .deps/sam3

# 5. Install OWLv2
python -c "
from huggingface_hub import snapshot_download
snapshot_download('google/owlv2-base-patch16-ensemble',
                  local_dir='checkpoints/owlv2-base')
"
```

---

## Environment variables

```bash
cp .env.example .env
# Edit .env: set FUTBOTMX_VIDEO_836, FUTBOTMX_VIDEO_595, etc.
# SAM3_CHECKPOINT_PATH=checkpoints/sam3/sam3.pt
# OWLV2_MODEL_PATH=checkpoints/owlv2-base
# PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
```

Source match videos are not included in the repository because they are large binary files. The public demo required by the call is included at `outputs/videos/futbotmx_demo_h264.mp4`. Source video paths are set via `.env`.

---

## Run

```bash
source .venv/bin/activate

# ── Pipeline completo (recomendado para jueces) ──────────────────────────────
# Grounded-SAM → tracking → Level3 analytics → visualización en navegador
PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True \
python scripts/run_unified_analysis.py \
  --video "$FUTBOTMX_VIDEO_836" \
  --clip-id video_836 \
  --start-frame 120 --end-frame 180
# Abre automáticamente http://127.0.0.1:8766

# ── Validación individual ────────────────────────────────────────────────────
# Test suite (sin GPU)
python -m unittest discover -s tests -q

# Segmentación en un solo frame
PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True \
python scripts/run_grounded_sam_test.py \
  --video "$FUTBOTMX_VIDEO_836" --frame 143

# Métricas supervisadas
python scripts/run_phase5_metrics.py
```

Full guide: [docs/EVALUATOR_GUIDE.md](docs/EVALUATOR_GUIDE.md)

---

## Key results

| Metric | Value |
|---|---|
| Inference speed | 0.447 FPS (single), 0.831 FPS (batched ×5) |
| VRAM peak | 3878 MB |
| Robots tracked | 3, frames 120–180 |
| Goalpost detection | OWLv2 text → SAM3 mask (video\_836 conf=0.108) |
| Test suite | 461 tests pass |
| Supervised IoU/F1 | **micro F1=0.857 · P=0.75 · R=1.00** (49 anotaciones Roboflow) |

Full results: [docs/RESULTS_SUMMARY.md](docs/RESULTS_SUMMARY.md)

---

## Repository layout

```
src/futbotmx/          Python package (segmentation, tracking, team assignment, metrics)
scripts/               Runnable scripts (test, demo, benchmark, annotation)
configs/               YAML configuration (default.yaml)
data/annotations/      Ground-truth annotation template + exported frames
checkpoints/           Model weights (not versioned — see ARTIFACTS_INDEX.md)
experiments/           Experiment outputs and evaluation results
outputs/videos/        Versioned public demo video
docs/                  Documentation for evaluation
tests/                 Unit test suite
```

---

## License and notices

See [LICENSE](LICENSE) and [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).

SAM3: Copyright Meta Platforms, Inc. — SAM License. Checkpoint weights are downloaded separately from the official release.
OWLv2: Copyright Google — Apache 2.0.
