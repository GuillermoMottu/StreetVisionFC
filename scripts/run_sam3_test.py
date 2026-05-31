from __future__ import annotations

import argparse
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from futbotmx.config import load_config, write_config_snapshot
from futbotmx.io.detections import save_detections
from futbotmx.segmentation import SAM3Segmenter, SAM3UnavailableError


def main() -> int:
    parser = argparse.ArgumentParser(description="Run SAM 3 segmentation test on the GPU laptop.")
    parser.add_argument("--config", default="configs/default.yaml")
    parser.add_argument("--experiment", default="experiments/test_002_sam3_segmentation")
    parser.add_argument("--video", default=None)
    parser.add_argument("--checkpoint", default=None)
    parser.add_argument("--frame", type=int, action="append", dest="frames")
    parser.add_argument("--prompt", action="append", dest="prompts")
    args = parser.parse_args()

    config = load_config(args.config)
    experiment = Path(args.experiment)
    experiment.mkdir(parents=True, exist_ok=True)
    write_config_snapshot(config, experiment / "config.yaml")

    prompt_values = args.prompts or config["segmentation"]["classes"]
    prompts = [item.replace("_", " ") for item in prompt_values]
    threshold = float(config["segmentation"].get("confidence_threshold", 0.5))

    try:
        segmenter = SAM3Segmenter(
            checkpoint_path=args.checkpoint,
            confidence_threshold=threshold,
        )
        video_path = args.video or config["video"]["input_path"]
        frame_indices = args.frames or [0]
        frames = segmenter.segment_video(video_path, frame_indices, prompts)
    except SAM3UnavailableError as exc:
        (experiment / "errors.md").write_text(
            "# SAM 3 validation pending\n\n"
            f"{exc}\n\n"
            "Run this script on the MSI laptop after installing SAM 3 officially.\n",
            encoding="utf-8",
        )
        print(str(exc))
        return 2
    except FileNotFoundError as exc:
        (experiment / "errors.md").write_text(
            "# SAM 3 input missing\n\n"
            f"{exc}\n\n"
            "Place a local clip at the configured video path or pass a config with an existing video.\n",
            encoding="utf-8",
        )
        print(str(exc))
        return 3

    save_detections(frames, experiment / "detections.json")
    detection_count = sum(len(frame.detections) for frame in frames)
    (experiment / "summary.md").write_text(
        "# test_002_sam3_segmentation\n\n"
        "## Estado\n\n"
        "SAM 3 ejecutado en laptop MSI.\n\n"
        "## Configuracion\n\n"
        f"- Video: `{video_path}`\n"
        f"- Frames: `{', '.join(str(frame) for frame in frame_indices)}`\n"
        f"- Prompts: `{', '.join(prompts)}`\n"
        f"- Detecciones: `{detection_count}`\n\n"
        "## Artefactos\n\n"
        "- `config.yaml`\n"
        "- `detections.json`\n",
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
