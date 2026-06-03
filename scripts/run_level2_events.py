from __future__ import annotations

import argparse
import csv
from collections import Counter
from pathlib import Path
import re
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from futbotmx.config import load_config, write_config_snapshot
from futbotmx.events import detect_level2_events, write_level2_event_metrics, write_level2_events_json
from futbotmx.visualization import write_overlay_frame


OVERLAY_FRAME_RE = re.compile(r"(\d+)")


def event_overlay_frames(events: list[dict[str, object]]) -> list[int]:
    frames: list[int] = []
    for event in events:
        start = int(event["frame_start"])
        end = int(event["frame_end"])
        for frame in (start, (start + end) // 2, end):
            if frame not in frames:
                frames.append(frame)
    return frames


def existing_overlays(overlay_dir: str | None) -> dict[int, Path]:
    if not overlay_dir:
        return {}
    root = Path(overlay_dir)
    if not root.exists():
        return {}
    overlays: dict[int, Path] = {}
    for path in sorted(root.glob("*.png")):
        match = OVERLAY_FRAME_RE.findall(path.stem)
        if not match:
            continue
        overlays[int(match[-1])] = path
    return overlays


def nearest_overlay(frame: int, overlays: dict[int, Path], tolerance: int) -> tuple[str, str]:
    if not overlays:
        return "missing", ""
    nearest_frame = min(overlays, key=lambda item: abs(item - frame))
    if abs(nearest_frame - frame) <= tolerance:
        return "matched", str(overlays[nearest_frame])
    return "missing", ""


def write_overlay_manifest(
    path: Path,
    events: list[dict[str, object]],
    video: str | None,
    tracks: str,
    overlay_dir: str | None,
    tolerance: int,
) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    overlays = existing_overlays(overlay_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    for event in events:
        event_id = str(event["event_id"])
        for frame in event_overlay_frames([event]):
            output_path = path.parent / f"overlay_{event_id}_frame_{frame}.png"
            status = "missing"
            overlay_path = ""
            if video:
                write_overlay_frame(video, tracks, output_path, frame)
                status = "generated"
                overlay_path = str(output_path)
            else:
                status, overlay_path = nearest_overlay(frame, overlays, tolerance)
            rows.append(
                {
                    "event_id": event_id,
                    "event_type": event["event_type"],
                    "reliability": event["reliability"],
                    "frame": frame,
                    "overlay_status": status,
                    "overlay_path": overlay_path,
                }
            )

    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["event_id", "event_type", "reliability", "frame", "overlay_status", "overlay_path"],
            lineterminator="\n",
        )
        writer.writeheader()
        for row in rows:
            writer.writerow(row)
    return rows


def write_summary(
    path: Path,
    tracks: str,
    events: list[dict[str, object]],
    overlay_rows: list[dict[str, object]],
    event_config: dict[str, object],
) -> None:
    counts = Counter((event["event_type"], event["reliability"]) for event in events)
    matched = sum(1 for row in overlay_rows if row["overlay_status"] in ("generated", "matched"))
    missing = sum(1 for row in overlay_rows if row["overlay_status"] == "missing")
    lines = [
        "# test_013_level2_events_video_836",
        "",
        "## Configuracion",
        "",
        f"- Tracks: `{tracks}`.",
        f"- Regla: `{event_config['rule_version']}`.",
        f"- Umbral de posesion: `{event_config['possession_distance_px']}px`.",
        f"- Min frames recuperacion: `{event_config['recovery_min_frames']}`.",
        f"- Gap max intercepcion: `{event_config['interception_max_gap_frames']}` frames.",
        f"- Velocidad min highlight: `{event_config['highlight_min_speed_px_per_sec']}px/s`.",
        "",
        "## Eventos",
        "",
    ]
    for (event_type, reliability), count in sorted(counts.items()):
        lines.append(f"- `{event_type}` / `{reliability}`: `{count}`.")
    lines.extend(["", "## Detalle", ""])
    for event in events:
        signals = event["evidence"]["signals"]  # type: ignore[index]
        lines.append(
            f"- `{event['event_id']}` `{event['event_type']}` `{event['reliability']}`: "
            f"frames `{event['frame_start']}-{event['frame_end']}`, "
            f"confianza `{event['confidence']}`, senales `{signals}`."
        )
    lines.extend(
        [
            "",
            "## Validacion Visual",
            "",
            f"- Overlays representativos encontrados/generados: `{matched}`.",
            f"- Overlays pendientes: `{missing}`.",
            "- Si no se provee `--video`, el script enlaza overlays existentes cercanos por frame.",
            "",
            "## Limitaciones",
            "",
            "- Recuperacion e intercepcion son heuristicas de proximidad, no contacto fisico confirmado.",
            "- En tracks con equipo `neutral`, la intercepcion se conserva como candidato descartado cuando no hay cambio de robot.",
            "- La jugada destacada usa velocidad/zona en pixeles y requiere revision visual final.",
            "",
            "## Artefactos",
            "",
            "- `level2_events.json`",
            "- `level2_event_metrics.csv`",
            "- `overlay_validation.csv`",
            "- `config.yaml`",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Detect Level 2 intermediate events from tracks.csv.")
    parser.add_argument("--config", default="configs/default.yaml")
    parser.add_argument("--tracks", required=True)
    parser.add_argument("--experiment", default="experiments/test_013_level2_events/video_836_real_events_120_180")
    parser.add_argument("--fps", type=float, required=True)
    parser.add_argument("--field-width", type=float, default=1360)
    parser.add_argument("--field-height", type=float, default=1808)
    parser.add_argument("--video", default=None)
    parser.add_argument("--overlay-dir", default=None)
    parser.add_argument("--overlay-tolerance-frames", type=int, default=2)
    args = parser.parse_args()

    config = load_config(args.config)
    event_config = dict(config.get("level2_events", {}))
    event_config.setdefault("rule_version", "level2_events_v0.1")
    event_config.setdefault("possession_distance_px", config.get("events", {}).get("possession_distance_px", 190))
    event_config.setdefault("recovery_min_frames", 5)
    event_config.setdefault("interception_max_gap_frames", 12)
    event_config.setdefault("interception_min_speed_px_per_sec", 120)
    event_config.setdefault("highlight_min_speed_px_per_sec", 250)

    experiment = Path(args.experiment)
    experiment.mkdir(parents=True, exist_ok=True)
    write_config_snapshot(config, experiment / "config.yaml")

    events = detect_level2_events(
        args.tracks,
        fps=args.fps,
        field_width=args.field_width,
        field_height=args.field_height,
        config=event_config,
        source_experiment=str(experiment),
    )
    write_level2_events_json(events, experiment / "level2_events.json")
    write_level2_event_metrics(events, experiment / "level2_event_metrics.csv")
    overlay_rows = write_overlay_manifest(
        experiment / "overlay_validation.csv",
        events,
        video=args.video,
        tracks=args.tracks,
        overlay_dir=args.overlay_dir,
        tolerance=args.overlay_tolerance_frames,
    )
    write_summary(experiment / "summary.md", args.tracks, events, overlay_rows, event_config)
    print(f"Wrote Level 2 events experiment to {experiment}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
