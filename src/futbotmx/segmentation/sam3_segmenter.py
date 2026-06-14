from __future__ import annotations

import os
from pathlib import Path

import cv2
from PIL import Image

from futbotmx.io.detections import Detection, FrameDetections


class SAM3UnavailableError(RuntimeError):
    """Raised when SAM 3 has not been installed on the GPU machine."""


class SAM3Segmenter:
    def __init__(
        self,
        checkpoint_path: str | None = None,
        confidence_threshold: float = 0.5,
        device: str | None = None,
        mask_output_dir: str | Path | None = None,
    ) -> None:
        self.checkpoint_path = checkpoint_path or os.environ.get("SAM3_CHECKPOINT_PATH")
        if self.checkpoint_path is None and Path("checkpoints/sam3/sam3.pt").exists():
            self.checkpoint_path = "checkpoints/sam3/sam3.pt"
        self.confidence_threshold = confidence_threshold
        self.device = device
        self._mask_output_dir = Path(mask_output_dir) if mask_output_dir is not None else None
        self._torch = None
        self._processor = None

    def segment_image(self, image_path: str | Path, prompts: list[str]) -> FrameDetections:
        image = Image.open(image_path).convert("RGB")
        detections = self._segment_pil_image(image, prompts, frame_index=0)
        return FrameDetections(frame=0, detections=tuple(detections))

    def segment_video(
        self,
        video_path: str | Path,
        frame_indices: list[int],
        prompts: list[str] | None = None,
    ) -> list[FrameDetections]:
        prompts = prompts or ["ball", "ally robot", "opponent robot", "field"]
        capture = cv2.VideoCapture(str(video_path))
        if not capture.isOpened():
            raise FileNotFoundError(f"Could not open video: {video_path}")

        frames: list[FrameDetections] = []
        try:
            for frame_index in frame_indices:
                capture.set(cv2.CAP_PROP_POS_FRAMES, frame_index)
                ok, frame_bgr = capture.read()
                if not ok:
                    continue
                frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
                image = Image.fromarray(frame_rgb)
                detections = self._segment_pil_image(image, prompts, frame_index=frame_index)
                frames.append(FrameDetections(frame=frame_index, detections=tuple(detections)))
        finally:
            capture.release()
        return frames

    def _ensure_processor(self):
        if self._processor is not None:
            return self._processor

        try:
            import torch
            from sam3.model_builder import build_sam3_image_model
            from sam3.model.sam3_image_processor import Sam3Processor
        except ImportError as exc:
            raise SAM3UnavailableError(
                "SAM 3 is not importable. Install facebookresearch/sam3 in the GPU environment."
            ) from exc

        device = self.device or ("cuda" if torch.cuda.is_available() else "cpu")
        checkpoint_path = self.checkpoint_path
        load_from_hf = checkpoint_path is None
        try:
            model = build_sam3_image_model(
                checkpoint_path=checkpoint_path,
                load_from_HF=load_from_hf,
                compile=False,
                device=device,
            )
            self._processor = Sam3Processor(
                model,
                device=device,
                confidence_threshold=self.confidence_threshold,
            )
        except Exception as exc:
            raise SAM3UnavailableError(f"SAM 3 could not be initialized: {exc}") from exc

        self._torch = torch
        return self._processor

    def segment_with_box_prompt(
        self,
        image: Image.Image,
        class_name: str,
        bbox_pixel: tuple[float, float, float, float],
        frame_index: int = 0,
        det_idx: int = 0,
        box_prompt_threshold: float = 0.1,
    ) -> Detection:
        """
        Prompt SAM3 with a known bounding box to produce a pixel-level mask.

        bbox_pixel: (x0, y0, x1, y1) in image pixel coordinates.
        box_prompt_threshold: lower than text-prompt threshold since location is known.
        Returns a Detection; mask_path is populated if mask_output_dir was provided.
        """
        processor = self._ensure_processor()
        torch = self._torch
        assert torch is not None

        img_w, img_h = image.size
        x0, y0, x1, y1 = bbox_pixel
        cx_norm = (x0 + x1) / (2 * img_w)
        cy_norm = (y0 + y1) / (2 * img_h)
        w_norm = (x1 - x0) / img_w
        h_norm = (y1 - y0) / img_h

        if self._mask_output_dir is not None:
            self._mask_output_dir.mkdir(parents=True, exist_ok=True)

        context = (
            torch.autocast("cuda", dtype=torch.bfloat16)
            if processor.device == "cuda"
            else _NullContext()
        )

        prev_threshold = processor.confidence_threshold
        processor.confidence_threshold = box_prompt_threshold
        try:
            with context:
                state = processor.set_image(image)
                output = processor.add_geometric_prompt(
                    box=[cx_norm, cy_norm, w_norm, h_norm],
                    label=True,
                    state=state,
                )
        finally:
            processor.confidence_threshold = prev_threshold

        masks = output.get("masks")
        boxes_out = output.get("boxes")
        scores = output.get("scores")

        if masks is not None and masks.shape[0] > 0:
            best_idx = int(scores.argmax()) if (scores is not None and scores.shape[0] > 0) else 0

            mask_path: str | None = None
            if self._mask_output_dir is not None:
                mask_path = _save_mask(masks[best_idx], class_name, frame_index, det_idx, self._mask_output_dir)

            if boxes_out is not None and boxes_out.shape[0] > best_idx:
                b = boxes_out[best_idx].cpu().tolist()
                refined_bbox: tuple[float, float, float, float] = (float(b[0]), float(b[1]), float(b[2]), float(b[3]))
            else:
                refined_bbox = bbox_pixel

            confidence = float(scores[best_idx]) if (scores is not None and scores.shape[0] > 0) else 0.5
        else:
            refined_bbox = bbox_pixel
            confidence = 0.0
            mask_path = None

        safe_class = class_name.replace(" ", "_")
        cx = (refined_bbox[0] + refined_bbox[2]) / 2
        cy = (refined_bbox[1] + refined_bbox[3]) / 2
        return Detection(
            class_name=safe_class,
            bbox=refined_bbox,
            centroid=(cx, cy),
            confidence=confidence,
            mask_path=mask_path,
        )

    def _segment_pil_image(
        self, image: Image.Image, prompts: list[str], frame_index: int = 0
    ) -> list[Detection]:
        processor = self._ensure_processor()
        torch = self._torch
        assert torch is not None

        if self._mask_output_dir is not None:
            self._mask_output_dir.mkdir(parents=True, exist_ok=True)

        detections: list[Detection] = []
        context = (
            torch.autocast("cuda", dtype=torch.bfloat16)
            if processor.device == "cuda"
            else _NullContext()
        )
        with context:
            state = processor.set_image(image)
            det_start = 0
            for prompt in prompts:
                output = processor.set_text_prompt(state=state, prompt=prompt)
                new_dets = _detections_from_output(
                    prompt, output, frame_index, det_start, self._mask_output_dir
                )
                detections.extend(new_dets)
                det_start += len(new_dets)
                processor.reset_all_prompts(state)
        return detections


class _NullContext:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback) -> bool:
        return False


def _save_mask(
    mask_tensor,
    class_name: str,
    frame_index: int,
    det_idx: int,
    mask_output_dir: Path,
) -> str:
    """Save a (1, H, W) bool mask tensor as PNG. Returns the file path string."""
    import numpy as np

    mask_np = mask_tensor.squeeze(0).cpu().numpy().astype("uint8") * 255
    safe_class = class_name.replace(" ", "_").replace("/", "_")
    filename = f"frame_{frame_index:06d}_{safe_class}_{det_idx:03d}.png"
    output_path = mask_output_dir / filename
    Image.fromarray(mask_np, mode="L").save(str(output_path))
    return str(output_path)


def _detections_from_output(
    class_name: str,
    output: dict,
    frame_index: int = 0,
    det_start_idx: int = 0,
    mask_output_dir: Path | None = None,
) -> list[Detection]:
    boxes = output.get("boxes")
    scores = output.get("scores")
    masks = output.get("masks")  # (N, 1, H, W) bool tensor, or None / empty

    if boxes is None or scores is None:
        return []

    boxes_cpu = boxes.detach().float().cpu().tolist()
    scores_cpu = scores.detach().float().cpu().tolist()

    detections: list[Detection] = []
    for idx, (bbox, score) in enumerate(zip(boxes_cpu, scores_cpu)):
        x0, y0, x1, y1 = (float(value) for value in bbox)

        mask_path: str | None = None
        if (
            mask_output_dir is not None
            and masks is not None
            and masks.shape[0] > idx
        ):
            mask_path = _save_mask(
                masks[idx], class_name, frame_index, det_start_idx + idx, mask_output_dir
            )

        detections.append(
            Detection(
                class_name=class_name.replace(" ", "_"),
                bbox=(x0, y0, x1, y1),
                centroid=((x0 + x1) / 2, (y0 + y1) / 2),
                confidence=float(score),
                mask_path=mask_path,
            )
        )
    return detections
