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
    ) -> None:
        self.checkpoint_path = checkpoint_path or os.environ.get("SAM3_CHECKPOINT_PATH")
        if self.checkpoint_path is None and Path("checkpoints/sam3/sam3.pt").exists():
            self.checkpoint_path = "checkpoints/sam3/sam3.pt"
        self.confidence_threshold = confidence_threshold
        self.device = device
        self._torch = None
        self._processor = None

    def segment_image(self, image_path: str | Path, prompts: list[str]) -> FrameDetections:
        image = Image.open(image_path).convert("RGB")
        detections = self._segment_pil_image(image, prompts)
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
                detections = self._segment_pil_image(image, prompts)
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

    def _segment_pil_image(self, image: Image.Image, prompts: list[str]) -> list[Detection]:
        processor = self._ensure_processor()
        torch = self._torch
        assert torch is not None

        detections: list[Detection] = []
        context = (
            torch.autocast("cuda", dtype=torch.bfloat16)
            if processor.device == "cuda"
            else _NullContext()
        )
        with context:
            state = processor.set_image(image)
            for prompt in prompts:
                output = processor.set_text_prompt(state=state, prompt=prompt)
                detections.extend(_detections_from_output(prompt, output))
                processor.reset_all_prompts(state)
        return detections


class _NullContext:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback) -> bool:
        return False


def _detections_from_output(class_name: str, output: dict) -> list[Detection]:
    boxes = output.get("boxes")
    scores = output.get("scores")
    if boxes is None or scores is None:
        return []

    boxes_cpu = boxes.detach().float().cpu().tolist()
    scores_cpu = scores.detach().float().cpu().tolist()
    detections: list[Detection] = []
    for bbox, score in zip(boxes_cpu, scores_cpu):
        x0, y0, x1, y1 = (float(value) for value in bbox)
        detections.append(
            Detection(
                class_name=class_name.replace(" ", "_"),
                bbox=(x0, y0, x1, y1),
                centroid=((x0 + x1) / 2, (y0 + y1) / 2),
                confidence=float(score),
            )
        )
    return detections
