# Reproducibility Guide — FutBotMX / StreetVisionFC

Installation and execution on the verified hardware configuration.

---

## Hardware and software environment

| Component | Value |
|---|---|
| Machine | MSI Laptop |
| GPU | NVIDIA GeForce RTX 4050 Laptop GPU (6141 MB VRAM) |
| CUDA | 13.0 |
| OS | Ubuntu 24.04 (kernel 7.0.0-22-generic) |
| Python | 3.14.4 |
| PyTorch | 2.12.0+cu130 |

---

## 1. Clone and set up environment

```bash
git clone <repo-url> StreetVisionFC
cd StreetVisionFC
git checkout fix/master-audit-corrections   # active branch

python3.14 -m venv .venv
source .venv/bin/activate

# Install PyTorch first (CUDA 13.0)
pip install torch==2.12.0 torchvision==0.27.0 --index-url https://download.pytorch.org/whl/cu130

# Install remaining dependencies
pip install -r requirements-gpu.txt
```

---

## 2. Install SAM3

SAM3 is installed from source into `.deps/sam3/`:

```bash
mkdir -p .deps
git clone https://github.com/facebookresearch/sam3 .deps/sam3
pip install -e .deps/sam3
```

SAM3 checkpoint (3.3 GB) must be downloaded separately:

```bash
mkdir -p checkpoints/sam3
# Download sam3.pt from the official SAM3 release and place it at:
#   checkpoints/sam3/sam3.pt
```

---

## 3. Install OWLv2

```bash
pip install transformers==5.12.0

python -c "
from huggingface_hub import snapshot_download
snapshot_download(
    repo_id='google/owlv2-base-patch16-ensemble',
    local_dir='checkpoints/owlv2-base',
)
"
# Downloads ~1.2 GB to checkpoints/owlv2-base/
```

---

## 4. Configure environment variables

Copy `.env.example` to `.env` and set video paths:

```bash
cp .env.example .env
```

Edit `.env`:
```
FUTBOTMX_VIDEO_836=/path/to/video-836_singular_display.mov
FUTBOTMX_VIDEO_595=/path/to/video-595_singular_display.mov
FUTBOTMX_VIDEO_667=/path/to/video-667_singular_display.mov
FUTBOTMX_VIDEO_480=/path/to/video-480_singular_display.mov
SAM3_CHECKPOINT_PATH=checkpoints/sam3/sam3.pt
OWLV2_MODEL_PATH=checkpoints/owlv2-base
PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
```

Videos are not versioned in Git. They must be placed on the local machine.

---

## 5. Verify installation

```bash
# Test suite (no GPU required)
python -m unittest discover -s tests -q
# Expected: 425 tests pass, 0 fail

# Verify SAM3 + OWLv2 on a real frame
source .env
PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True \
python scripts/run_grounded_sam_test.py \
  --video "$FUTBOTMX_VIDEO_836" \
  --frame 143
# Expected: [ALL PASS] GroundedSAM pipeline validated
```

---

## 6. Run the full pipeline

```bash
source .env

# Segmentation: all classes, frame 143 of video_836
PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True \
python scripts/run_grounded_sam_test.py \
  --video "$FUTBOTMX_VIDEO_836" \
  --output-dir experiments/current_evaluation/masks_grounded_sam

# Goalpost mask with SAM3 box-prompt (original pipeline)
python scripts/run_goalpost_mask_test.py \
  --video "$FUTBOTMX_VIDEO_836"

# Team assignment
python scripts/run_phase4_team_assignment.py

# Benchmark and metrics report
python scripts/run_phase5_metrics.py

# Regenerate demo video (requires full video access)
python scripts/create_phase3_demo.py \
  --video "$FUTBOTMX_VIDEO_836" \
  --tracks experiments/current_evaluation/phase4_team_assignment/tracks_bytetrack_with_teams.csv
```

---

## 7. Known constraints

| Constraint | Detail |
|---|---|
| VRAM limit | OWLv2 + SAM3 cannot coexist on 6 GB GPU. Pipeline offloads OWLv2 to CPU between stages. |
| video_595 goalpost | OWLv2 misses thin horizontal bars in frames 120-180; falls back to `_CLIP_GOALS` bbox (no mask). |
| Green field mask | SAM3 skipped when bbox > 30% of frame (OOM). OWLv2 bbox is used instead. |
| Supervised metrics | Require human annotation of `data/annotations/annotation_template.json`. |
| Videos not in Git | All `.mov`/`.mp4` source files must be placed locally; paths set in `.env`. |

---

## 8. Pinned dependencies

See `requirements-gpu.txt` for the full list (17 packages, exact versions).
Key packages: `torch==2.12.0`, `torchvision==0.27.0`, `transformers==5.12.0`,
`supervision==0.28.0`, `timm==1.0.27`, `huggingface-hub==1.17.0`.
