# Technical Architecture — FutBotMX / StreetVisionFC

Computer-vision pipeline for robot soccer video analysis.

---

## Pipeline overview

```
Video (MOV/MP4)
      │
      ▼
┌─────────────────────────────────────────────────────┐
│  Frame decoder (OpenCV)                              │
│  Input:  video path + frame indices                  │
│  Output: PIL Image (RGB)                             │
└─────────────────────┬───────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────┐
│  Grounded-SAM Segmenter                             │
│                                                     │
│  Stage 1 — OWLv2 (text → bbox)                     │
│    Model:  google/owlv2-base-patch16-ensemble       │
│    Input:  PIL Image + text prompts                  │
│    Output: bounding boxes + confidence scores        │
│                                                     │
│  Stage 2 — SAM3 (bbox → pixel mask)                │
│    Model:  checkpoints/sam3/sam3.pt (3.3 GB)        │
│    Input:  PIL Image + bbox (normalized cxcywh)      │
│    Output: binary mask (H × W), saved as PNG        │
│                                                     │
│  Memory management: OWLv2 offloaded to CPU before   │
│  SAM3 runs (prevents OOM on 6 GB VRAM).             │
│  Bboxes > 30% of frame skip SAM3 (field class).    │
│                                                     │
│  Goalpost fallback: if OWLv2 misses goalpost and   │
│  clip_id is provided, uses HSV-confirmed coords     │
│  (_CLIP_GOALS) + SAM3 box-prompt.                  │
└─────────────────────┬───────────────────────────────┘
                      │ FrameDetections (detections + mask paths)
                      ▼
┌─────────────────────────────────────────────────────┐
│  ByteTrack (multi-object tracker)                   │
│  Input:  FrameDetections per frame                  │
│  Output: tracks_bytetrack.csv                       │
│          columns: frame, track_id, x, y, w, h,     │
│                   x_norm, y_norm, class, conf       │
└─────────────────────┬───────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────┐
│  Team Assignment                                    │
│  Strategy: initial_side_fallback                    │
│  Input:  tracks CSV (x_norm at first observation)  │
│  Output: tracks_bytetrack_with_teams.csv            │
│          new column: team (team_left / team_right)  │
│  Confidence: 0.64 (validated by human, 2026-06-13) │
└─────────────────────┬───────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────┐
│  Visualization (create_phase3_demo.py)              │
│  Input:  tracks + masks + team assignments          │
│  Output: outputs/videos/futbotmx_demo_h264.mp4     │
│          (H.264, 46.6 s, 2.3 MB)                   │
└─────────────────────────────────────────────────────┘
```

---

## Detected classes

| Class | Detection method | Mask |
|---|---|---|
| `small_robot` | OWLv2 text `"small robot"` + SAM3 box-prompt | pixel PNG |
| `ball` | OWLv2 text `"ball"` + SAM3 box-prompt | pixel PNG |
| `green_soccer_field` | OWLv2 text `"green soccer field"` (bbox only, >30% frame) | bbox only |
| `yellow_goalpost` | OWLv2 text `"yellow goalpost"` + SAM3; fallback to `_CLIP_GOALS` | pixel PNG (when available) |

---

## Module map

```
src/futbotmx/
├── segmentation/
│   ├── grounded_sam_segmenter.py   # OWLv2 + SAM3 pipeline (primary)
│   ├── owlv2_detector.py           # OWLv2 text → bbox wrapper
│   ├── sam3_segmenter.py           # SAM3 text + box-prompt wrapper
│   └── goalpost_fallback.py        # _CLIP_GOALS fallback + detect_goalposts_with_mask()
├── tracking/                       # ByteTrack integration
├── team_assignment/                # initial_side_fallback + manual override
├── io/
│   └── detections.py               # Detection, FrameDetections dataclasses
└── metrics/                        # benchmark + supervised metrics infrastructure
```

---

## Data formats

**Detection output** (`FrameDetections`):
```python
@dataclass
class Detection:
    class_name: str          # e.g. "small_robot"
    bbox: tuple[float,float,float,float]  # (x0, y0, x1, y1) pixels
    centroid: tuple[float, float]
    confidence: float
    mask_path: str | None    # abs path to PNG mask, or None
```

**Tracks CSV** (ByteTrack output):
```
frame, track_id, x, y, w, h, x_norm, y_norm, class_name, confidence
```

**Tracks with teams CSV**:
```
frame, track_id, x, y, w, h, x_norm, y_norm, class_name, confidence, team
```

---

## Hardware target

- GPU: NVIDIA GeForce RTX 4050 Laptop (6141 MB VRAM)
- CUDA: 13.0
- Python: 3.14.4
- PyTorch: 2.12.0+cu130
- OS: Ubuntu 24.04 (kernel 7.0.0-22-generic)
