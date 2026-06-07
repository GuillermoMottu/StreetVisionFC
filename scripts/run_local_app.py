from __future__ import annotations

import argparse
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from futbotmx.local_app import DEFAULT_EXPERIMENT_DIR, run_smoke_test, serve_local_app


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the FutBotMX local browser app.")
    parser.add_argument("--config", default="configs/default.yaml")
    parser.add_argument("--experiment", default=str(DEFAULT_EXPERIMENT_DIR))
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--smoke-test", action="store_true", help="Write lightweight app evidence and exit.")
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[1]
    config_path = Path(args.config)
    experiment_dir = Path(args.experiment)
    if args.smoke_test:
        result = run_smoke_test(root, config_path, experiment_dir)
        print(f"Wrote local app smoke evidence to {experiment_dir} ({result.status})")
        return 0 if result.status == "pass" else 1
    serve_local_app(root, config_path, experiment_dir, args.host, args.port)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
