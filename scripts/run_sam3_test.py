from __future__ import annotations

import argparse
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from futbotmx.config import load_config, write_config_snapshot
from futbotmx.segmentation import SAM3Segmenter, SAM3UnavailableError


def main() -> int:
    parser = argparse.ArgumentParser(description="Run SAM 3 segmentation test on the GPU laptop.")
    parser.add_argument("--config", default="configs/default.yaml")
    parser.add_argument("--experiment", default="experiments/test_002_sam3_segmentation")
    args = parser.parse_args()

    config = load_config(args.config)
    experiment = Path(args.experiment)
    experiment.mkdir(parents=True, exist_ok=True)
    write_config_snapshot(config, experiment / "config.yaml")

    try:
        segmenter = SAM3Segmenter()
        segmenter.segment_video(config["video"]["input_path"], [0])
    except SAM3UnavailableError as exc:
        (experiment / "errors.md").write_text(
            "# SAM 3 validation pending\n\n"
            f"{exc}\n\n"
            "Run this script on the MSI laptop after installing SAM 3 officially.\n",
            encoding="utf-8",
        )
        print(str(exc))
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
