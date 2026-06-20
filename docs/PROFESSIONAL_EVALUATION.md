# Professional Evaluation Evidence

This document maps FutBotMX / StreetVisionFC against the official Computer Vision chapter of the Copa FutBotMX call, with emphasis on the professional-category criteria: innovation on SAM 3, technical quality, performance, originality, quantitative metrics, visualization and reproducibility.

## Delivery Status

| Official requirement | Status | Public evidence |
|---|---:|---|
| Functional SAM 3 processing flow | Complete | `src/futbotmx/segmentation/`, `scripts/run_unified_analysis.py`, `docs/SAM3_PIPELINE.md` |
| Segment field, allied/rival robots and ball | Complete | `data/annotations/`, `outputs/videos/futbotmx_demo_h264.mp4`, `docs/RESULTS_SUMMARY.md` |
| Track robot and ball trajectories | Complete | `src/futbotmx/tracking/`, `outputs/tracking/tracks.csv` |
| Detect events such as possession, recoveries, shots or collisions | Complete | `src/futbotmx/events/`, `src/futbotmx/level3/advanced_events.py` |
| Visualization or narrative of the match | Complete | `outputs/visualizations/heatmap.png`, `src/futbotmx/level3/visualizations.py`, `src/futbotmx/level3/dashboard.py` |
| Demo video under 2 minutes | Complete | `outputs/videos/futbotmx_demo_h264.mp4` is 46.6 s |
| Public Instagram Reel link | Complete | https://www.instagram.com/reel/DZynpB2pH_L_Mxq8V9Iq3bN5WHSFDGvsy_17iw0/?igsh=dnZ6MnlyYm13ZWV2 |
| Complete README with install, reproduction, hardware/software, results and credits | Complete | `README.md`, `docs/REPRODUCIBILITY.md`, `THIRD_PARTY_NOTICES.md` |
| Open-source license and third-party attribution | Complete | `LICENSE`, `THIRD_PARTY_NOTICES.md` |

## Innovation On SAM 3

The project extends plain SAM 3 prompting into a Grounded-SAM pipeline tailored to robot soccer videos:

| Innovation line | Implementation | Why it matters |
|---|---|---|
| Advanced prompt/context engineering | OWLv2 receives domain prompts (`small robot`, `ball`, `green soccer field`, `yellow goalpost`) and returns object boxes for SAM 3 geometric prompts | Improves reliability compared with SAM 3 text-only prompting on small objects and thin goalposts |
| Integration with another model | OWLv2 text-to-box detection feeds SAM 3 box-prompt segmentation | Provides open-vocabulary localization plus pixel masks |
| Tracker integration | ByteTrack converts frame detections into stable object trajectories | Enables possession, speed and tactical events over time |
| Post-processing | ROI filtering, class-specific NMS, goalpost fallback, confidence preservation and mask contour extraction | Reduces false positives and makes the output useful for sports analytics |
| Hardware-aware inference | OWLv2 is offloaded before SAM 3 runs to avoid GPU OOM on 6 GB VRAM | Makes the pipeline reproducible on the verified RTX 4050 laptop |
| Tactical analytics | Field rectification, Voronoi approximation, minimap, interaction graph and highlight ranking | Turns segmentation/tracking into match-understanding evidence |

Professional innovation is demonstrated through prompt engineering, model integration, tracker integration, post-processing and quantitative validation.

## Quantitative Results

| Metric | Value |
|---|---:|
| SAM 3 single-frame inference | 2.237 s/frame, 0.447 FPS |
| SAM 3 batched x5 inference | 1.203 s/frame, 0.831 FPS |
| VRAM peak | 3878 MB |
| Supervised micro F1 at IoU 0.5 | 0.857 |
| Supervised precision / recall | 0.75 / 1.00 |
| Human annotations | 49 annotations across 8 frames |
| Dense tracking window | 61 frames |
| Current test suite | 461 tests, 0 failures |
| Level 3 closure gate | 11 pass, 0 fail |

Sources: `docs/RESULTS_SUMMARY.md`, `docs/EVALUATOR_GUIDE.md`, `experiments/test_027_level3_closure/summary.md` when regenerated locally.

## Visualization Evidence

The public repository includes lightweight visual evidence:

- `outputs/videos/futbotmx_demo_h264.mp4`: required demo MP4, 46.6 s.
- `outputs/visualizations/heatmap.png`: activity heatmap.
- `data/annotations/frames/`: representative source frames used for supervised evaluation.

Generated local packages also include dashboard, reel storyboard, Voronoi frames, interaction graph and highlight panels. They can be regenerated with:

```bash
source .venv/bin/activate
python scripts/run_local_app.py
```

## Reproducibility Procedure

```bash
python3.14 -m venv .venv
source .venv/bin/activate
pip install torch==2.12.0 torchvision==0.27.0 \
  --index-url https://download.pytorch.org/whl/cu130
pip install -r requirements-gpu.txt

mkdir -p .deps
git clone https://github.com/facebookresearch/sam3 .deps/sam3
pip install -e .deps/sam3

python -m pip check
python -m unittest discover -s tests -q
python scripts/validate_pipeline.py
python scripts/check_level3_closure.py
```

Expected results on the verified environment:

- `pip check`: no broken requirements.
- `461 tests`, `OK`.
- `validate_pipeline.py`: all checks pass.
- `check_level3_closure.py`: `11 pass`, `0 fail`.

Source match videos come from the Copa FutBotMX materials and model checkpoints are obtained from their official releases. The `.env.example` file documents the required local configuration.

## External Publication

The public Instagram Reel required by the call is published at:

https://www.instagram.com/reel/DZynpB2pH_L_Mxq8V9Iq3bN5WHSFDGvsy_17iw0/?igsh=dnZ6MnlyYm13ZWV2
