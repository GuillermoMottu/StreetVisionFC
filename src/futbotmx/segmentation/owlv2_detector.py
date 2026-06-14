"""
OWLv2 zero-shot text→bbox detector.

Wraps google/owlv2-base-patch16-ensemble via HuggingFace transformers.
Returns Detection objects with bbox and confidence; mask_path is always
None (masks are produced downstream by SAM3 via segment_with_box_prompt).
"""
from __future__ import annotations

import os
from pathlib import Path

from PIL import Image

from futbotmx.io.detections import Detection, FrameDetections


class OWLv2UnavailableError(RuntimeError):
    """Raised when transformers or the OWLv2 checkpoint is not available."""


class OWLv2Detector:
    """Text → bounding box zero-shot detector using OWLv2."""

    def __init__(
        self,
        model_path: str | Path | None = None,
        confidence_threshold: float = 0.1,
        device: str | None = None,
    ) -> None:
        self.model_path = str(
            model_path
            or os.environ.get("OWLV2_MODEL_PATH", "checkpoints/owlv2-base")
        )
        self.confidence_threshold = confidence_threshold
        self.device = device
        self._model = None
        self._processor = None
        self._torch = None

    def _ensure_model(self):
        if self._model is not None:
            return

        try:
            import torch
            from transformers import AutoProcessor, AutoModelForZeroShotObjectDetection
        except ImportError as exc:
            raise OWLv2UnavailableError(
                "transformers is not installed. Run: pip install transformers"
            ) from exc

        if not Path(self.model_path).exists():
            raise OWLv2UnavailableError(
                f"OWLv2 checkpoint not found at {self.model_path}. "
                "Download with: huggingface_hub.snapshot_download('google/owlv2-base-patch16-ensemble')"
            )

        device = self.device or ("cuda" if torch.cuda.is_available() else "cpu")
        self._processor = AutoProcessor.from_pretrained(self.model_path)
        self._model = AutoModelForZeroShotObjectDetection.from_pretrained(
            self.model_path
        ).to(device)
        self._model.eval()
        self._torch = torch
        self.device = device

    def detect(
        self,
        image: Image.Image,
        texts: list[str],
        frame_index: int = 0,
    ) -> list[Detection]:
        """
        Detect objects matching each text prompt.

        Returns one Detection per detected object; mask_path is None
        (masks must be produced by SAM3 downstream).
        """
        self._ensure_model()
        torch = self._torch

        inputs = self._processor(
            text=[texts], images=image, return_tensors="pt"
        ).to(self.device)

        with torch.inference_mode():
            outputs = self._model(**inputs)

        target_sizes = torch.tensor(
            [image.size[::-1]], device=self.device
        )
        results = self._processor.post_process_grounded_object_detection(
            outputs,
            threshold=self.confidence_threshold,
            target_sizes=target_sizes,
        )[0]

        boxes = results["boxes"].cpu().tolist()
        scores = results["scores"].cpu().tolist()
        labels = results["labels"].cpu().tolist()

        detections: list[Detection] = []
        for box, score, label_idx in zip(boxes, scores, labels):
            x0, y0, x1, y1 = (float(v) for v in box)
            class_name = texts[label_idx].replace(" ", "_")
            detections.append(
                Detection(
                    class_name=class_name,
                    bbox=(x0, y0, x1, y1),
                    centroid=((x0 + x1) / 2, (y0 + y1) / 2),
                    confidence=float(score),
                    mask_path=None,
                )
            )
        return detections

    def detect_frame(
        self,
        image: Image.Image,
        texts: list[str],
        frame_index: int = 0,
    ) -> FrameDetections:
        detections = self.detect(image, texts, frame_index=frame_index)
        return FrameDetections(frame=frame_index, detections=tuple(detections))
