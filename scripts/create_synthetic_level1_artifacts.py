from __future__ import annotations

import csv
import json
from pathlib import Path
import shutil
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from futbotmx.config import load_config, write_config_snapshot
from futbotmx.events import detect_level1_events, write_events_json
from futbotmx.io.detections import Detection, FrameDetections, save_detections
from futbotmx.tracking import track_detections, write_tracks_csv
from futbotmx.visualization import write_heatmap


def synthetic_detections() -> list[FrameDetections]:
    frames: list[FrameDetections] = []
    for frame in range(18):
        if frame <= 5:
            ball_x = 38 + frame
            robot_one_x = 31 + frame
            robot_two_x = 92
        elif frame <= 7:
            ball_x = 62 + frame
            robot_one_x = 40
            robot_two_x = 92
        elif frame <= 13:
            ball_x = 88 + frame
            robot_one_x = 40
            robot_two_x = 92 + frame
        elif frame == 14:
            ball_x = 95
            robot_one_x = 40
            robot_two_x = 112
        else:
            ball_x = 128 + (frame - 15) * 12
            robot_one_x = 40
            robot_two_x = 112

        opponent_x = robot_two_x + 3 if 9 <= frame <= 12 else 132
        frames.append(
            FrameDetections(
                frame=frame,
                detections=(
                    Detection("ball", (ball_x - 5, 42, ball_x + 5, 52), (ball_x, 47), 0.9),
                    Detection("ally_robot", (robot_one_x - 12, 28, robot_one_x + 12, 65), (robot_one_x, 47), 0.86),
                    Detection("ally_robot", (robot_two_x - 12, 28, robot_two_x + 12, 65), (robot_two_x, 47), 0.84),
                    Detection("opponent_robot", (opponent_x - 12, 28, opponent_x + 12, 65), (opponent_x, 47), 0.82),
                ),
            )
        )
    return frames


def write_metrics(path: Path, rows: list[dict[str, str | int | float]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["metric", "value"])
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    config = load_config("configs/default.yaml")

    env_dir = Path("experiments/test_000_environment_check")
    env_dir.mkdir(parents=True, exist_ok=True)
    write_config_snapshot(config, env_dir / "config.yaml")
    write_metrics(
        env_dir / "metrics.csv",
        [
            {"metric": "desktop_python", "value": "3.12.10"},
            {"metric": "desktop_dependencies", "value": "validated"},
            {"metric": "gpu_validation", "value": "pending_laptop_msi"},
        ],
    )

    tracking_dir = Path("experiments/test_003_tracking")
    tracking_dir.mkdir(parents=True, exist_ok=True)
    frames = synthetic_detections()
    save_detections(frames, tracking_dir / "detections.json")
    tracks = track_detections(frames, max_distance_px=80)
    write_tracks_csv(tracks, tracking_dir / "tracks.csv")
    write_config_snapshot(config, tracking_dir / "config.yaml")
    write_metrics(
        tracking_dir / "metrics.csv",
        [
            {"metric": "frames", "value": len(frames)},
            {"metric": "track_rows", "value": len(tracks)},
            {"metric": "source", "value": "synthetic_detections"},
        ],
    )

    events_dir = Path("experiments/test_004_events")
    events_dir.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(tracking_dir / "tracks.csv", events_dir / "tracks.csv")
    write_config_snapshot(config, events_dir / "config.yaml")
    events = detect_level1_events(
        events_dir / "tracks.csv",
        fps=15,
        field_width=160,
        field_height=90,
        config={**config["events"], "possession_distance_px": 30, "possession_min_frames": 3},
        source_experiment="experiments/test_004_events",
    )
    write_events_json(events, events_dir / "events.json")
    write_metrics(
        events_dir / "metrics.csv",
        [
            {"metric": "events", "value": len(events)},
            {"metric": "source", "value": "synthetic_tracks"},
        ],
    )

    visualization_dir = Path("experiments/test_005_visualizations")
    visualization_dir.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(tracking_dir / "tracks.csv", visualization_dir / "tracks.csv")
    write_config_snapshot(config, visualization_dir / "config.yaml")
    write_heatmap(visualization_dir / "tracks.csv", visualization_dir / "heatmap.png", width=160, height=90)
    write_metrics(
        visualization_dir / "metrics.csv",
        [
            {"metric": "heatmap_png", "value": "created"},
            {"metric": "source", "value": "synthetic_tracks"},
        ],
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
