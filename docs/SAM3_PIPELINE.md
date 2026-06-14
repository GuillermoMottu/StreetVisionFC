# SAM3 Pipeline — FutBotMX / StreetVisionFC

Segmentation Anything Model 3 integration details: prompts, masks, outputs, and goalpost fallback.

---

## Model

| Property | Value |
|---|---|
| Checkpoint | `checkpoints/sam3/sam3.pt` |
| Size | ~3.3 GB |
| VRAM after load | 3626 MB |
| VRAM peak (inference) | 3878 MB |
| Load time | 15.6 s (one-time per session) |
| API | `sam3.model.sam3_image_processor.Sam3Processor` |

---

## Two prompt modes

### 1. Text prompt (original pipeline)

```python
state = processor.set_image(image)
output = processor.set_text_prompt(state=state, prompt="small robot")
# output: {"boxes": Tensor, "scores": Tensor, "masks": Tensor (N,1,H,W)}
```

Used for: `small_robot`, `ball`, `green_soccer_field`.
**Limitation**: SAM3 returns 0 detections for all goalpost text prompts tested
(confirmed across 6 frames, 5 prompts: "goal", "soccer goal", "goalpost",
"small soccer goal", "robot soccer goal").

### 2. Geometric (box) prompt — used by Grounded-SAM

```python
state = processor.set_image(image)
output = processor.add_geometric_prompt(
    box=[cx_norm, cy_norm, w_norm, h_norm],  # cxcywh, normalized 0-1
    label=True,
    state=state,
)
# output: {"boxes": Tensor, "scores": Tensor, "masks": Tensor (N,1,H,W)}
```

Used for: goalpost (prompted by OWLv2 bbox or `_CLIP_GOALS`), and in
`GroundedSAMSegmenter` for ALL classes (OWLv2 provides the initial bbox).

---

## Grounded-SAM pipeline (primary)

```
Text prompts
     │
     ▼ OWLv2 (text → bbox, zero-shot)
     │  Model: google/owlv2-base-patch16-ensemble (1.2 GB)
     │  Confidence threshold: 0.1 (default)
     ▼
  OWLv2 bboxes
     │
     ▼ OWLv2 offloaded to CPU (free ~1.5 GB VRAM)
     │
     ▼ SAM3 box-prompt (bbox → pixel mask)
     │  For each detection with bbox_area < 30% of frame:
     │    → add_geometric_prompt(cxcywh_norm, label=True)
     │    → save mask PNG to mask_output_dir
     ▼
  FrameDetections (bbox + confidence + mask_path)
```

### VRAM management

OWLv2 (~1.5 GB) and SAM3 (~3.8 GB) exceed the 6 GB GPU limit when both loaded.
Solution: OWLv2 runs first, is moved to CPU, then SAM3 processes each bbox.
`torch.cuda.empty_cache()` is called between detections to reduce fragmentation.

---

## Goalpost detection

SAM3 text prompts do not detect the goalpost. The solution is two-tiered:

**Tier 1 — OWLv2 text (automatic, camera-angle agnostic):**

| Clip | OWLv2 conf | Mask via SAM3 |
|---|---|---|
| video\_836 | 0.108 | YES |
| video\_667 | 0.077–0.090 | YES (6/7 frames in 120-180) |
| video\_595 | < 0.05 in 120-180 | not detected |

**Tier 2 — `_CLIP_GOALS` fallback (when OWLv2 misses):**

HSV yellow-blob detection produced per-clip pixel coordinates (2026-06-11):

```python
_CLIP_GOALS = {
    "video_836": [(1000.0, 650.0, 1360.0, 800.0)],       # 1 goal visible
    "video_480": [(1000.0, 650.0, 1360.0, 800.0)],
    "video_595": [(525.0, 486.0, 820.0, 540.0),           # 2 goals
                  (525.0, 1745.0, 820.0, 1792.0)],
    "video_667": [(530.0, 686.0, 830.0, 740.0),           # 2 goals
                  (530.0, 1760.0, 830.0, 1807.0)],
}
```

These coordinates are image-space pixel coordinates (perspective view), not
real-world field positions.

**Fallback chain for video_595 goalpost:**
1. OWLv2 → miss (conf < 0.05 in frames 120-180)
2. `_CLIP_GOALS` bbox → SAM3 box-prompt → OOM on 6 GB GPU (bbox needs 1.56 GB)
3. Pure bbox detection (conf=0.0, no mask) ← current result

**Result:** video\_595 goalpost is delivered as plain bbox with conf=0.0.
No mask is available with current VRAM constraints.

---

## Output format

Masks are saved as grayscale PNG (0=background, 255=object):

```
experiments/current_evaluation/masks/
  frame_000143_small_robot_000.png     # robot 0
  frame_000143_small_robot_001.png     # robot 1
  frame_000143_ball_005.png
  frame_000143_green_soccer_field_006.png
  frame_000143_goalpost_007.png        # SAM3 box-prompt from _CLIP_GOALS

experiments/current_evaluation/masks_grounded_sam/
  frame_000143_small_robot_000.png     # OWLv2 + SAM3 box-prompt
  frame_000143_ball_003.png
  frame_000143_yellow_goalpost_004.png # OWLv2 text → SAM3 box-prompt
  ...
```

---

## Limitations

- **Not real-time**: 0.45 FPS single-frame, 0.83 FPS batched ×5. Offline analysis only.
- **Green field**: bbox covers >30% of frame, SAM3 skipped (OOM). Bbox-only.
- **video\_595 goalpost**: thin horizontal bars not recognized by OWLv2 in frames 120-180.
- **Hardware dependency**: SAM3 requires CUDA GPU with ≥4 GB free VRAM.
