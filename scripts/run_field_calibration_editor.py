from __future__ import annotations

import argparse
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from futbotmx.level3.manual_calibration import (
    DEFAULT_CLIPS,
    DEFAULT_OUTPUT_DIR,
    DEFAULT_SOURCE_DIR,
    build_calibration_editor,
    serve_calibration_editor,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the FutBotMX manual field calibration editor.")
    parser.add_argument("--config", default="configs/default.yaml")
    parser.add_argument("--source-dir", default=str(DEFAULT_SOURCE_DIR))
    parser.add_argument("--experiment", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--clips", nargs="+", default=list(DEFAULT_CLIPS))
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8766)
    parser.add_argument("--build-only", action="store_true", help="Generate editor artifacts and exit.")
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[1]
    output_dir = Path(args.experiment)
    context = build_calibration_editor(
        root / args.config,
        root / args.source_dir,
        root / output_dir,
        tuple(args.clips),
    )
    print(f"Wrote calibration editor to {output_dir} ({len(context.clips)} clips)")
    if args.build_only:
        return 0
    serve_calibration_editor(root, root / output_dir, args.host, args.port)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
