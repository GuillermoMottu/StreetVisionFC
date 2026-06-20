from __future__ import annotations

import csv
import math
import os
import textwrap
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import matplotlib.image as mpimg
import matplotlib.pyplot as plt


RULE_VERSION = "activity19_video_overlay_v0.1"

SEGMENT_FIELDS = [
    "segment_id",
    "rank",
    "clip_id",
    "highlight_id",
    "frame_start",
    "frame_end",
    "time_start_sec",
    "time_end_sec",
    "duration_sec",
    "score",
    "confidence",
    "reliability",
    "zone",
    "event_label",
    "source_overlay_path",
    "reference_frame_path",
    "minimap_path",
    "thumbnail_path",
    "selection_reason",
]

MANIFEST_FIELDS = ["asset_id", "asset_type", "path", "source_artifact", "is_versioned", "role", "notes"]


@dataclass(frozen=True)
class VideoOverlayConfig:
    highlights_csv: str = "experiments/test_034_full_analysis/level3_events/level3_highlights.csv"
    overlay_validation_csv: str = "experiments/test_034_full_analysis/level3_events/overlay_validation.csv"
    advanced_events_dir: str = "experiments/test_034_full_analysis/level3_events"
    storyboard_manifest_csv: str = "experiments/test_034_full_analysis/level3_visualizations/highlight_storyboard_manifest.csv"
    visualizations_dir: str = "experiments/test_034_full_analysis/level3_visualizations"
    output_dir: str = "experiments/test_037_activity19_video_overlay"
    local_mp4_path: str = "local_outputs/activity19/video_595_overlay_clip.mp4"
    segment_count: int = 3
    segment_duration_sec: float = 2.5
    min_confidence: float = 0.8


def build_video_overlay_package(config: VideoOverlayConfig) -> dict[str, Any]:
    output_dir = Path(config.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    context = build_video_overlay_context(config)
    segments = context["segments"]
    for segment in segments:
        draw_overlay_thumbnail(output_dir / segment["thumbnail_path"], segment)
    draw_overlay_contact_sheet(output_dir / "video_overlay_contact_sheet.png", segments)
    write_csv_rows(output_dir / "video_overlay_segments.csv", segments, SEGMENT_FIELDS)
    write_ffmpeg_inputs(output_dir / "video_overlay_ffmpeg_inputs.txt", segments, config)
    render_script = output_dir / "render_overlay_clip.sh"
    write_render_script(render_script, config)
    render_script.chmod(0o755)
    write_render_plan(output_dir / "render_overlay_clip_plan.md", segments, config)
    write_summary(output_dir / "summary.md", context)
    manifest = video_overlay_manifest_rows(config, context)
    write_csv_rows(output_dir / "video_overlay_manifest.csv", manifest, MANIFEST_FIELDS)
    context["manifest"] = manifest
    return context


def build_video_overlay_context(config: VideoOverlayConfig) -> dict[str, Any]:
    highlights = sorted(read_csv_rows(config.highlights_csv), key=lambda row: int(row["rank"]))
    overlays = read_csv_rows(config.overlay_validation_csv)
    storyboard_rows = read_optional_csv_rows(config.storyboard_manifest_csv)
    segments = select_overlay_segments(highlights, overlays, storyboard_rows, config)
    return {
        "config": config,
        "rule_version": RULE_VERSION,
        "segments": segments,
        "summary": {
            "segments": len(segments),
            "clips": sorted({segment["clip_id"] for segment in segments}),
            "duration_sec": round(len(segments) * config.segment_duration_sec, 3),
            "top_score": float(segments[0]["score"]) if segments else 0.0,
            "min_confidence": min((float(segment["confidence"]) for segment in segments), default=0.0),
            "local_mp4_path": config.local_mp4_path,
        },
    }


def select_overlay_segments(
    highlights: list[dict[str, str]],
    overlay_rows: list[dict[str, str]],
    storyboard_rows: list[dict[str, str]],
    config: VideoOverlayConfig,
) -> list[dict[str, Any]]:
    target_count = min(3, max(1, config.segment_count))
    overlay_by_highlight = {
        row["highlight_id"]: row
        for row in overlay_rows
        if row.get("status") == "generated" and row.get("asset_path")
    }
    storyboard_by_highlight = {row["highlight_id"]: row for row in storyboard_rows}
    candidates: list[dict[str, str]] = []
    fallback: list[dict[str, str]] = []
    for highlight in highlights:
        highlight_id = str(highlight["highlight_id"])
        if highlight_id not in overlay_by_highlight:
            continue
        if float(highlight.get("confidence", 0.0)) >= config.min_confidence:
            candidates.append(highlight)
        else:
            fallback.append(highlight)
    selected = (candidates + fallback)[:target_count]
    segments: list[dict[str, Any]] = []
    for index, highlight in enumerate(selected, start=1):
        highlight_id = str(highlight["highlight_id"])
        overlay = overlay_by_highlight[highlight_id]
        storyboard = storyboard_by_highlight.get(highlight_id, {})
        overlay_path = _optional_join(config.advanced_events_dir, overlay.get("asset_path", ""))
        reference_path = str(storyboard.get("reference_frame_path", ""))
        minimap_path = _optional_join(config.visualizations_dir, str(storyboard.get("minimap_path", "")))
        thumbnail_name = f"overlay_thumb_rank_{int(highlight['rank']):02d}_{highlight['clip_id']}_frame_{highlight['frame_start']}.png"
        segments.append(
            {
                "segment_id": f"overlay_segment_{index:02d}",
                "rank": highlight["rank"],
                "clip_id": highlight["clip_id"],
                "highlight_id": highlight_id,
                "frame_start": highlight["frame_start"],
                "frame_end": highlight["frame_end"],
                "time_start_sec": highlight["time_start_sec"],
                "time_end_sec": highlight["time_end_sec"],
                "duration_sec": f"{config.segment_duration_sec:.1f}",
                "score": highlight["score"],
                "confidence": highlight["confidence"],
                "reliability": highlight["reliability"],
                "zone": highlight["zone"],
                "event_label": event_label(highlight),
                "source_overlay_path": overlay_path,
                "reference_frame_path": reference_path,
                "minimap_path": minimap_path,
                "thumbnail_path": thumbnail_name,
                "selection_reason": selection_reason(highlight, overlay_path, reference_path, minimap_path, config),
            }
        )
    return segments


def draw_overlay_thumbnail(output_path: str | Path, segment: dict[str, Any]) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(10.4, 4.1), gridspec_kw={"width_ratios": [1.45, 1.0]})
    _draw_image_or_placeholder(axes[0], segment.get("source_overlay_path"), "Overlay con IDs, trails y evento")
    axes[1].set_axis_off()
    axes[1].set_title("Clip local")
    text = (
        f"{segment['segment_id']}\n"
        f"Rank {segment['rank']} | {segment['clip_id']}\n"
        f"Frames {segment['frame_start']}-{segment['frame_end']}\n"
        f"Tiempo {float(segment['time_start_sec']):.3f}-{float(segment['time_end_sec']):.3f}s\n"
        f"Score {float(segment['score']):.1f} | Conf {float(segment['confidence']):.2f}\n"
        f"Zona {segment['zone']}\n\n"
        f"{textwrap.fill(str(segment['event_label']), width=34)}"
    )
    axes[1].text(0.02, 0.95, text, va="top", fontsize=10, linespacing=1.25)
    fig.tight_layout()
    fig.savefig(output_path, dpi=115)
    plt.close(fig)


def draw_overlay_contact_sheet(output_path: str | Path, segments: list[dict[str, Any]]) -> None:
    if not segments:
        return
    cols = min(3, len(segments))
    rows = math.ceil(len(segments) / cols)
    fig, axes = plt.subplots(rows, cols, figsize=(5.2 * cols, 4.0 * rows), squeeze=False)
    for index, ax in enumerate(axes.flat):
        if index >= len(segments):
            ax.set_axis_off()
            continue
        thumbnail_path = Path(output_path).parent / str(segments[index]["thumbnail_path"])
        _draw_image_or_placeholder(ax, thumbnail_path, f"Segmento {index + 1}")
    fig.tight_layout()
    fig.savefig(output_path, dpi=105)
    plt.close(fig)


def write_ffmpeg_inputs(path: str | Path, segments: list[dict[str, Any]], config: VideoOverlayConfig) -> None:
    lines: list[str] = []
    for segment in segments:
        lines.append(f"file '{segment['thumbnail_path']}'")
        lines.append(f"duration {config.segment_duration_sec:.3f}")
    if segments:
        lines.append(f"file '{segments[-1]['thumbnail_path']}'")
    Path(path).write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_render_script(path: str | Path, config: VideoOverlayConfig) -> None:
    local_output = _rel_path(config.local_mp4_path, config.output_dir)
    local_dir = Path(local_output).parent.as_posix()
    lines = [
        "#!/usr/bin/env bash",
        "set -euo pipefail",
        "",
        "if ! command -v ffmpeg >/dev/null 2>&1; then",
        "  echo \"ffmpeg no esta instalado o no esta en PATH\" >&2",
        "  exit 1",
        "fi",
        "",
        f"mkdir -p {local_dir}",
        "ffmpeg -y -f concat -safe 0 -i video_overlay_ffmpeg_inputs.txt "
        "-vf \"scale=1280:720:force_original_aspect_ratio=decrease,"
        "pad=1280:720:(ow-iw)/2:(oh-ih)/2,fps=30\" "
        f"-c:v libx264 -pix_fmt yuv420p {local_output}",
    ]
    Path(path).write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_render_plan(path: str | Path, segments: list[dict[str, Any]], config: VideoOverlayConfig) -> None:
    lines = [
        "# Plan De Render Local - Overlay Corto",
        "",
        "El MP4 se renderiza localmente y queda fuera de Git. La evidencia versionada son thumbnails, contact sheet, CSV y manifest.",
        "",
        "## Dependencias",
        "",
        "- `ffmpeg` disponible en `PATH`.",
        "- Overlays PNG ya versionados en la etapa de eventos Nivel 3.",
        "",
        "## Comando",
        "",
        "```bash",
        f"cd {config.output_dir}",
        "bash render_overlay_clip.sh",
        "```",
        "",
        f"Salida local esperada: `{config.local_mp4_path}`.",
        "",
        "## Segmentos",
        "",
    ]
    for segment in segments:
        lines.append(
            f"- `{segment['segment_id']}` rank `{segment['rank']}` frames "
            f"`{segment['frame_start']}-{segment['frame_end']}` thumbnail `{segment['thumbnail_path']}`."
        )
    lines.extend(
        [
            "",
            "## Politica",
            "",
            "- `*.mp4` esta ignorado por `.gitignore`.",
            "- No se copian videos fuente ni frames masivos al repositorio.",
            "- El overlay muestra IDs, trazas cortas y etiqueta de evento cuando existen en la evidencia Nivel 3.",
        ]
    )
    Path(path).write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_summary(path: str | Path, context: dict[str, Any]) -> None:
    config: VideoOverlayConfig = context["config"]
    summary = context["summary"]
    lines = [
        "# Actividad 19 - Overlay De Video Corto",
        "",
        "## Resultado",
        "",
        "- Estado: `generado`.",
        f"- Regla: `{RULE_VERSION}`.",
        f"- Segmentos seleccionados: `{summary['segments']}`.",
        f"- Clips incluidos: `{', '.join(summary['clips'])}`.",
        f"- Duracion sugerida: `{summary['duration_sec']}` segundos.",
        f"- MP4 local esperado: `{config.local_mp4_path}`.",
        "- MP4 generado localmente como artefacto de revision.",
        "",
        "## Segmentos",
        "",
    ]
    for segment in context["segments"]:
        lines.append(
            f"- `{segment['segment_id']}` rank `{segment['rank']}` `{segment['clip_id']}` "
            f"frames `{segment['frame_start']}-{segment['frame_end']}` score `{float(segment['score']):.1f}` "
            f"conf `{float(segment['confidence']):.2f}`."
        )
    lines.extend(
        [
            "",
            "## Render Local",
            "",
            "```bash",
            f"cd {config.output_dir}",
            "bash render_overlay_clip.sh",
            "```",
            "",
            "## Artefactos",
            "",
            "- `video_overlay_segments.csv`",
            "- `video_overlay_manifest.csv`",
            "- `video_overlay_contact_sheet.png`",
            "- `overlay_thumb_rank_*.png`",
            "- `video_overlay_ffmpeg_inputs.txt`",
            "- `render_overlay_clip.sh`",
            "- `render_overlay_clip_plan.md`",
            "",
            "## Limitaciones",
            "",
            "- El paquete versiona evidencia visual ligera, no el MP4 final.",
            "- Los eventos siguen siendo highlights candidatos con lenguaje conservador.",
        ]
    )
    Path(path).write_text("\n".join(lines) + "\n", encoding="utf-8")


def video_overlay_manifest_rows(config: VideoOverlayConfig, context: dict[str, Any]) -> list[dict[str, Any]]:
    output_dir = Path(config.output_dir)
    rows = [
        manifest_row("summary", "md", "summary.md", "video_overlay_segments.csv", True, "summary", "Activity 19 package summary."),
        manifest_row("video_overlay_segments", "csv", "video_overlay_segments.csv", config.highlights_csv, True, "timeline", "Selected overlay clip segments."),
        manifest_row("video_overlay_manifest", "csv", "video_overlay_manifest.csv", "video_overlay_segments.csv", True, "manifest", "Overlay clip artifact manifest."),
        manifest_row("video_overlay_contact_sheet", "png", "video_overlay_contact_sheet.png", "video_overlay_segments.csv", True, "contact_sheet", "Lightweight visual evidence for selected segments."),
        manifest_row("video_overlay_ffmpeg_inputs", "txt", "video_overlay_ffmpeg_inputs.txt", "video_overlay_segments.csv", True, "render_input", "Concat input list for local MP4 render."),
        manifest_row("render_overlay_clip", "sh", "render_overlay_clip.sh", "video_overlay_ffmpeg_inputs.txt", True, "render_script", "Local FFmpeg helper; MP4 remains outside Git."),
        manifest_row("render_overlay_clip_plan", "md", "render_overlay_clip_plan.md", "render_overlay_clip.sh", True, "render_plan", "Dependencies and reproduction notes."),
        manifest_row("local_overlay_mp4", "mp4", _rel_path(config.local_mp4_path, output_dir), "render_overlay_clip.sh", False, "local_output", "Not generated or versioned in Git."),
    ]
    for segment in context["segments"]:
        rows.append(
            manifest_row(
                segment["segment_id"],
                "png",
                segment["thumbnail_path"],
                segment["source_overlay_path"],
                True,
                "thumbnail",
                f"Rank {segment['rank']} overlay thumbnail with IDs/trails/event evidence.",
            )
        )
    source_paths = {
        "highlights_csv": config.highlights_csv,
        "overlay_validation_csv": config.overlay_validation_csv,
        "storyboard_manifest_csv": config.storyboard_manifest_csv,
    }
    for asset_id, source in source_paths.items():
        rows.append(
            manifest_row(
                asset_id,
                Path(source).suffix.lstrip(".") or "artifact",
                _rel_path(source, output_dir),
                source,
                True,
                "source",
                "Linked source artifact.",
            )
        )
    return rows


def config_to_dict(config: VideoOverlayConfig) -> dict[str, Any]:
    return asdict(config)


def event_label(highlight: dict[str, str]) -> str:
    reasons = [part.strip() for part in str(highlight["reason"]).split(";") if part.strip()]
    return " | ".join(reasons[:3])


def selection_reason(highlight: dict[str, str], overlay_path: str, reference_path: str, minimap_path: str, config: VideoOverlayConfig) -> str:
    reasons = ["ranking_highlight", "overlay_ids_trails_event"]
    if float(highlight.get("confidence", 0.0)) >= config.min_confidence:
        reasons.append(f"confidence>={config.min_confidence:.2f}")
    if reference_path:
        reasons.append("frame_referencia")
    if minimap_path:
        reasons.append("minimap")
    if overlay_path:
        reasons.append("png_versionado")
    return ";".join(reasons)


def read_csv_rows(path: str | Path) -> list[dict[str, str]]:
    with Path(path).open("r", newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def read_optional_csv_rows(path: str | Path) -> list[dict[str, str]]:
    if not path:
        return []
    candidate = Path(path)
    if not candidate.exists():
        return []
    return read_csv_rows(candidate)


def write_csv_rows(path: str | Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def _draw_image_or_placeholder(ax: Any, image_path: str | Path | None, title: str) -> None:
    ax.set_title(title)
    ax.set_axis_off()
    path = Path(str(image_path)) if image_path else None
    if path and path.exists():
        try:
            ax.imshow(mpimg.imread(path))
            return
        except Exception:
            pass
    ax.text(0.5, 0.5, "sin imagen", ha="center", va="center", fontsize=11)


def _optional_join(root: str | Path, path: str) -> str:
    if not path:
        return ""
    candidate = Path(path)
    return candidate.as_posix() if candidate.parent != Path(".") else (Path(root) / candidate).as_posix()


def _rel_path(path: str | Path, base_dir: str | Path) -> str:
    return Path(os.path.relpath(Path(path), start=Path(base_dir))).as_posix()


def manifest_row(asset_id: str, asset_type: str, path: str, source_artifact: str, is_versioned: bool, role: str, notes: str) -> dict[str, Any]:
    return {
        "asset_id": asset_id,
        "asset_type": asset_type,
        "path": path,
        "source_artifact": source_artifact,
        "is_versioned": str(is_versioned).lower(),
        "role": role,
        "notes": notes,
    }
