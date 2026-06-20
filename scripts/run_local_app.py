from __future__ import annotations

import argparse
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from futbotmx.local_app import DEFAULT_EXPERIMENT_DIR, serve_local_app


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the FutBotMX product frontend.")
    parser.add_argument("--config", default="configs/default.yaml")
    parser.add_argument("--experiment", default=str(DEFAULT_EXPERIMENT_DIR))
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[1]
    serve_local_app(root, Path(args.config), Path(args.experiment), args.host, args.port)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
