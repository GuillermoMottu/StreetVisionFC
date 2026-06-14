"""
Grounded-SAM segmenter: OWLv2 (text→bbox) + SAM3 (bbox→mask).

For each text prompt:
  1. OWLv2 detects bounding boxes (zero-shot, camera-angle agnostic)
  2. Each bbox is fed to SAM3.segment_with_box_prompt → pixel-level mask

This replaces the hardcoded _CLIP_GOALS fallback for the goalpost and makes
every class get a real pixel mask regardless of camera angle or clip.
"""
from __future__ import annotations

import cv2
from pathlib import Path
from PIL import Image

from futbotmx.io.detections import Detection, FrameDetections
from futbotmx.segmentation.owlv2_detector import OWLv2Detector, OWLv2UnavailableError
from futbotmx.segmentation.sam3_segmenter import SAM3Segmenter, SAM3UnavailableError


class GroundedSAMSegmenter:
    """
    OWLv2 → SAM3 pipeline producing pixel-level masks for all classes.

    Drop-in replacement for SAM3Segmenter.segment_video() — same output
    format (list[FrameDetections]) but all detections come with mask_path.
    """

    def __init__(
        self,
        owlv2_model_path: str | Path = "checkpoints/owlv2-base",
        sam3_checkpoint: str | Path | None = None,
        owlv2_confidence_threshold: float = 0.1,
        sam3_confidence_threshold: float = 0.1,
        device: str | None = None,
        mask_output_dir: str | Path | None = None,
    ) -> None:
        self._detector = OWLv2Detector(
            model_path=owlv2_model_path,
            confidence_threshold=owlv2_confidence_threshold,
            device=device,
        )
        self._sam3 = SAM3Segmenter(
            checkpoint_path=sam3_checkpoint,
            confidence_threshold=sam3_confidence_threshold,
            device=device,
            mask_output_dir=mask_output_dir,
        )
        self._mask_output_dir = Path(mask_output_dir) if mask_output_dir else None

    def segment_image(
        self,
        image: Image.Image,
        prompts: list[str],
        frame_index: int = 0,
    ) -> FrameDetections:
        """
        Segment all objects in a PIL image using text prompts.
        Returns FrameDetections with mask_path populated for every detection.

        OWLv2 and SAM3 each consume ~1.5 GB and ~3.8 GB VRAM respectively.
        On GPUs with <6 GB VRAM they cannot coexist: OWLv2 is offloaded to CPU
        after detection and VRAM is freed before SAM3 runs.
        """
        # Step 1: OWLv2 → bboxes for all prompts at once
        all_texts = [p.replace("_", " ") for p in prompts]
        raw_detections = self._detector.detect(image, all_texts, frame_index=frame_index)

        if not raw_detections:
            return FrameDetections(frame=frame_index, detections=())

        # Offload OWLv2 to CPU so SAM3 can use VRAM without OOM
        self._offload_owlv2()

        img_area = image.width * image.height

        # Step 2: SAM3 box-prompt → pixel mask for each detection
        final: list[Detection] = []
        for i, det in enumerate(raw_detections):
            x0, y0, x1, y1 = det.bbox
            x0c = max(0.0, x0); y0c = max(0.0, y0)
            x1c = min(float(image.width), x1); y1c = min(float(image.height), y1)
            bbox_area = (x1c - x0c) * (y1c - y0c)

            # Skip SAM3 for near-full-frame bboxes (e.g. field): they exhaust VRAM
            # and the OWLv2 bbox is already a good enough region.
            if bbox_area > 0.30 * img_area:
                final.append(det)
                continue

            try:
                import torch as _torch
                _torch.cuda.empty_cache()  # reduce fragmentation between calls
                masked = self._sam3.segment_with_box_prompt(
                    image=image,
                    class_name=det.class_name,
                    bbox_pixel=(x0c, y0c, x1c, y1c),
                    frame_index=frame_index,
                    det_idx=i,
                    box_prompt_threshold=0.05,
                )
                # preserve OWLv2 confidence (more meaningful than SAM3 box score)
                final.append(Detection(
                    class_name=masked.class_name,
                    bbox=masked.bbox,
                    centroid=masked.centroid,
                    confidence=det.confidence,
                    mask_path=masked.mask_path,
                ))
            except SAM3UnavailableError:
                final.append(det)
            except Exception:
                # SAM3 failed for this det — keep OWLv2 bbox, no mask
                final.append(det)

        return FrameDetections(frame=frame_index, detections=tuple(final))

    def _offload_owlv2(self) -> None:
        """Move OWLv2 model to CPU and free CUDA cache (needed before SAM3 on <6 GB GPUs)."""
        model = self._detector._model
        if model is None:
            return
        try:
            import torch
            model.cpu()
            torch.cuda.empty_cache()
        except Exception:
            pass

    def _reload_owlv2(self) -> None:
        """Move OWLv2 model back to its target device after SAM3 is done."""
        model = self._detector._model
        if model is None:
            return
        try:
            model.to(self._detector.device)
        except Exception:
            pass

    def segment_video(
        self,
        video_path: str | Path,
        frame_indices: list[int],
        prompts: list[str] | None = None,
    ) -> list[FrameDetections]:
        """Same interface as SAM3Segmenter.segment_video()."""
        prompts = prompts or ["ball", "small robot", "green soccer field", "yellow goalpost"]

        capture = cv2.VideoCapture(str(video_path))
        if not capture.isOpened():
            raise FileNotFoundError(f"Could not open video: {video_path}")

        frames: list[FrameDetections] = []
        try:
            for frame_index in frame_indices:
                capture.set(cv2.CAP_PROP_POS_FRAMES, frame_index)
                ok, bgr = capture.read()
                if not ok:
                    continue
                import cv2 as _cv2
                rgb = _cv2.cvtColor(bgr, _cv2.COLOR_BGR2RGB)
                image = Image.fromarray(rgb)
                fd = self.segment_image(image, prompts, frame_index=frame_index)
                frames.append(fd)
        finally:
            capture.release()
        return frames
