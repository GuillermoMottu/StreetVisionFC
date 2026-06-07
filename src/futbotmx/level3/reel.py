from __future__ import annotations

import csv
import html
import json
import math
import os
import textwrap
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import matplotlib.image as mpimg
import matplotlib.pyplot as plt


RULE_VERSION = "level3_reel_v0.1"

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
    "review_status",
    "reviewer",
    "zone",
    "event_label",
    "narration",
    "source_overlay_path",
    "minimap_path",
    "reference_frame_path",
    "thumbnail_path",
    "selection_reason",
    "review_notes",
]

MANIFEST_FIELDS = ["asset_id", "asset_type", "path", "source_artifact", "is_versioned", "role", "notes"]


@dataclass(frozen=True)
class Level3ReelConfig:
    highlights_csv: str = "experiments/test_022_level3_advanced_events/level3_highlights.csv"
    events_json: str = "experiments/test_022_level3_advanced_events/level3_events.json"
    overlay_validation_csv: str = "experiments/test_022_level3_advanced_events/overlay_validation.csv"
    advanced_events_dir: str = "experiments/test_022_level3_advanced_events"
    visualization_manifest_csv: str = "experiments/test_023_level3_visualizations/visualization_manifest.csv"
    storyboard_manifest_csv: str = "experiments/test_023_level3_visualizations/highlight_storyboard_manifest.csv"
    visualizations_dir: str = "experiments/test_023_level3_visualizations"
    dashboard_html: str = "experiments/test_024_level3_dashboard/dashboard.html"
    human_review_csv: str = ""
    output_dir: str = "experiments/test_025_level3_reel"
    local_reel_path: str = "local_outputs/level3_reel/futbotmx_level3_reel.mp4"
    segment_count: int = 4
    segment_duration_sec: float = 3.0
    min_confidence: float = 0.8


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


def read_json(path: str | Path) -> Any:
    with Path(path).open("r", encoding="utf-8") as handle:
        return json.load(handle)


def write_csv_rows(path: str | Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def build_reel_package(config: Level3ReelConfig) -> dict[str, Any]:
    output_dir = Path(config.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    context = build_reel_context(config)
    segments = context["segments"]
    for segment in segments:
        draw_reel_thumbnail(output_dir / segment["thumbnail_path"], segment)
    draw_contact_sheet(output_dir / "reel_contact_sheet.png", segments)
    write_csv_rows(output_dir / "reel_segments.csv", segments, SEGMENT_FIELDS)
    write_reel_narrative(output_dir / "reel_narrative.md", segments, config)
    write_ffmpeg_inputs(output_dir / "reel_ffmpeg_inputs.txt", segments, config)
    write_render_script(output_dir / "render_reel_local.sh", config)
    write_render_plan(output_dir / "reel_render_plan.md", segments, config)
    (output_dir / "reel_demo.html").write_text(render_reel_demo_html(context), encoding="utf-8")
    manifest = reel_manifest_rows(config, context)
    write_csv_rows(output_dir / "reel_manifest.csv", manifest, MANIFEST_FIELDS)
    context["manifest"] = manifest
    return context


def build_reel_context(config: Level3ReelConfig) -> dict[str, Any]:
    highlights = sorted(read_csv_rows(config.highlights_csv), key=lambda row: int(row["rank"]))
    events = read_json(config.events_json)
    overlays = read_csv_rows(config.overlay_validation_csv)
    visualizations = read_csv_rows(config.visualization_manifest_csv)
    storyboard_rows = read_csv_rows(config.storyboard_manifest_csv)
    review_rows = read_optional_csv_rows(config.human_review_csv)
    events_by_id = {str(event["event_id"]): event for event in events if "event_id" in event}
    segments = select_reel_segments(highlights, events_by_id, overlays, visualizations, storyboard_rows, config, review_rows)
    return {
        "config": config,
        "rule_version": RULE_VERSION,
        "segments": segments,
        "highlights": highlights,
        "events": events,
        "overlays": overlays,
        "visualizations": visualizations,
        "storyboard_rows": storyboard_rows,
        "review_rows": review_rows,
        "summary": {
            "segments": len(segments),
            "clips": sorted({segment["clip_id"] for segment in segments}),
            "duration_sec": round(len(segments) * config.segment_duration_sec, 3),
            "top_score": float(segments[0]["score"]) if segments else 0.0,
            "min_confidence": min((float(segment["confidence"]) for segment in segments), default=0.0),
            "reviewed_highlights": len(review_rows),
            "discarded_highlights": sum(1 for row in review_rows if row.get("review_status") == "descartado"),
        },
    }


def select_reel_segments(
    highlights: list[dict[str, str]],
    events_by_id: dict[str, dict[str, Any]],
    overlay_rows: list[dict[str, str]],
    visualization_rows: list[dict[str, str]],
    storyboard_rows: list[dict[str, str]],
    config: Level3ReelConfig,
    review_rows: list[dict[str, str]] | None = None,
) -> list[dict[str, Any]]:
    target_count = min(5, max(3, config.segment_count))
    overlay_by_highlight = {row["highlight_id"]: row for row in overlay_rows}
    minimap_by_highlight = {row["event_id"]: row for row in visualization_rows if row.get("asset_id", "").startswith("minimap_highlight")}
    storyboard_by_highlight = {row["highlight_id"]: row for row in storyboard_rows}
    review_by_highlight = {row["highlight_id"]: row for row in (review_rows or [])}
    candidates: list[dict[str, str]] = []
    fallback: list[dict[str, str]] = []
    for row in highlights:
        highlight_id = str(row["highlight_id"])
        review = review_by_highlight.get(highlight_id, {})
        if review.get("review_status") == "descartado":
            continue
        has_overlay = highlight_id in overlay_by_highlight
        has_minimap = highlight_id in minimap_by_highlight or storyboard_by_highlight.get(highlight_id, {}).get("minimap_path")
        confidence = float(row["confidence"])
        if confidence >= config.min_confidence and (has_overlay or has_minimap):
            candidates.append(row)
        elif has_overlay or has_minimap:
            fallback.append(row)
    selected: list[dict[str, str]] = []
    seen_ids: set[str] = set()
    selectable = [row for row in highlights if review_by_highlight.get(str(row["highlight_id"]), {}).get("review_status") != "descartado"]
    for row in candidates + fallback + selectable:
        highlight_id = str(row["highlight_id"])
        if highlight_id in seen_ids:
            continue
        selected.append(row)
        seen_ids.add(highlight_id)
        if len(selected) == target_count:
            break
    segments: list[dict[str, Any]] = []
    for index, highlight in enumerate(selected, start=1):
        highlight_id = str(highlight["highlight_id"])
        overlay = overlay_by_highlight.get(highlight_id, {})
        minimap = minimap_by_highlight.get(highlight_id, {})
        storyboard = storyboard_by_highlight.get(highlight_id, {})
        event = events_by_id.get(highlight_id, {})
        review = review_by_highlight.get(highlight_id, {})
        review_status = str(review.get("review_status", "sin_revision") or "sin_revision")
        overlay_path = _optional_join(config.advanced_events_dir, overlay.get("asset_path", ""))
        minimap_path = _optional_join(config.visualizations_dir, minimap.get("path") or storyboard.get("minimap_path", ""))
        reference_path = storyboard.get("reference_frame_path", "")
        thumbnail_name = f"reel_thumb_rank_{int(highlight['rank']):02d}_{highlight['clip_id']}_frame_{highlight['frame_start']}.png"
        segments.append(
            {
                "segment_id": f"reel_segment_{index:02d}",
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
                "review_status": review_status,
                "reviewer": review.get("reviewer", ""),
                "zone": highlight["zone"],
                "event_label": _event_label(highlight),
                "narration": _narration_for(highlight, event),
                "source_overlay_path": overlay_path,
                "minimap_path": minimap_path,
                "reference_frame_path": reference_path,
                "thumbnail_path": thumbnail_name,
                "selection_reason": _selection_reason(highlight, overlay_path, minimap_path, reference_path, config, review_status),
                "review_notes": review.get("notes", ""),
            }
        )
    return segments


def draw_reel_thumbnail(output_path: str | Path, segment: dict[str, Any]) -> None:
    fig, axes = plt.subplots(1, 3, figsize=(11.5, 4.2), gridspec_kw={"width_ratios": [1.25, 1.0, 1.05]})
    _draw_image_or_placeholder(axes[0], segment.get("source_overlay_path"), "Overlay evento")
    _draw_image_or_placeholder(axes[1], segment.get("minimap_path"), "Mini-mapa")
    axes[2].set_axis_off()
    axes[2].set_title("Narrativa")
    text = (
        f"Rank {segment['rank']} | {segment['clip_id']}\n"
        f"Frames {segment['frame_start']}-{segment['frame_end']}\n"
        f"Score {float(segment['score']):.1f} | Conf {float(segment['confidence']):.2f}\n"
        f"Revision {segment.get('review_status', 'sin_revision')}\n"
        f"{segment['event_label']}\n\n"
        f"{textwrap.fill(str(segment['narration']), width=34)}"
    )
    axes[2].text(0.02, 0.95, text, va="top", fontsize=10, linespacing=1.25)
    fig.tight_layout()
    fig.savefig(output_path, dpi=115)
    plt.close(fig)


def draw_contact_sheet(output_path: str | Path, segments: list[dict[str, Any]]) -> None:
    if not segments:
        return
    cols = 2
    rows = math.ceil(len(segments) / cols)
    fig, axes = plt.subplots(rows, cols, figsize=(11, 4.2 * rows), squeeze=False)
    for index, ax in enumerate(axes.flat):
        if index >= len(segments):
            ax.set_axis_off()
            continue
        segment = segments[index]
        thumbnail_path = Path(output_path).parent / str(segment["thumbnail_path"])
        _draw_image_or_placeholder(ax, thumbnail_path, f"Segmento {index + 1}")
    fig.tight_layout()
    fig.savefig(output_path, dpi=105)
    plt.close(fig)


def write_reel_narrative(path: str | Path, segments: list[dict[str, Any]], config: Level3ReelConfig) -> None:
    lines = [
        "# Narrativa Reel Nivel 3",
        "",
        "## Enfoque",
        "",
        "- Reel de demo con highlights candidatos y lenguaje conservador.",
        "- No afirma goles, faltas, tiros oficiales ni pases confirmados sin evidencia suficiente.",
        f"- Duracion sugerida por segmento: `{config.segment_duration_sec:.1f}` segundos.",
        "",
        "## Guion",
        "",
    ]
    for segment in segments:
        lines.append(
            f"- Segmento `{segment['segment_id']}` rank `{segment['rank']}` `{segment['clip_id']}` "
            f"frames `{segment['frame_start']}-{segment['frame_end']}` "
            f"revision `{segment.get('review_status', 'sin_revision')}`: {segment['narration']}"
        )
    lines.extend(
        [
            "",
            "## Cierre",
            "",
            "- Mostrar dashboard Nivel 3 y manifests como evidencia reproducible.",
            "- Mantener el MP4 final como salida local no versionada.",
        ]
    )
    Path(path).write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_ffmpeg_inputs(path: str | Path, segments: list[dict[str, Any]], config: Level3ReelConfig) -> None:
    lines: list[str] = []
    for segment in segments:
        lines.append(f"file '{segment['thumbnail_path']}'")
        lines.append(f"duration {config.segment_duration_sec:.3f}")
    if segments:
        lines.append(f"file '{segments[-1]['thumbnail_path']}'")
    Path(path).write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_render_script(path: str | Path, config: Level3ReelConfig) -> None:
    local_output = _rel_path(config.local_reel_path, config.output_dir)
    local_dir = Path(local_output).parent.as_posix()
    lines = [
        "#!/usr/bin/env bash",
        "set -euo pipefail",
        f"mkdir -p {local_dir}",
        "ffmpeg -y -f concat -safe 0 -i reel_ffmpeg_inputs.txt "
        "-vf \"scale=1280:720:force_original_aspect_ratio=decrease,"
        "pad=1280:720:(ow-iw)/2:(oh-ih)/2,fps=30\" "
        f"-c:v libx264 -pix_fmt yuv420p {local_output}",
    ]
    Path(path).write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_render_plan(path: str | Path, segments: list[dict[str, Any]], config: Level3ReelConfig) -> None:
    lines = [
        "# Plan De Render Local Reel Nivel 3",
        "",
        "El MP4 no se versiona. Para renderizarlo localmente desde las capturas ligeras:",
        "",
        "```bash",
        f"cd {config.output_dir}",
        "bash render_reel_local.sh",
        "```",
        "",
        f"Salida local esperada: `{config.local_reel_path}`.",
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
            "## Notas",
            "",
            "- El render usa thumbnails estaticos para evitar versionar video pesado.",
            "- Si se desea un reel con video real, usar los frames/timestamps de `reel_segments.csv` sobre los videos locales fuera de Git.",
        ]
    )
    Path(path).write_text("\n".join(lines) + "\n", encoding="utf-8")


def render_reel_demo_html(context: dict[str, Any]) -> str:
    config: Level3ReelConfig = context["config"]
    output_dir = Path(config.output_dir)
    cards = []
    for segment in context["segments"]:
        thumb = _rel_path(Path(config.output_dir) / segment["thumbnail_path"], output_dir)
        cards.append(
            "<article>"
            f'<a href="{_esc(thumb)}"><img src="{_esc(thumb)}" alt="Segmento {int(segment["rank"])}"></a>'
            f"<h2>Rank {_esc(segment['rank'])} | {_esc(segment['clip_id'])}</h2>"
            f"<p>Frames {_esc(segment['frame_start'])}-{_esc(segment['frame_end'])} | "
            f"score {float(segment['score']):.1f} | conf {float(segment['confidence']):.2f} | "
            f"revision {_esc(segment.get('review_status', 'sin_revision'))}</p>"
            f"<p>{_esc(segment['event_label'])}</p>"
            "</article>"
        )
    return "\n".join(
        [
            "<!doctype html>",
            '<html lang="es">',
            "<head>",
            '<meta charset="utf-8">',
            '<meta name="viewport" content="width=device-width, initial-scale=1">',
            "<title>FutBotMX Nivel 3 Reel</title>",
            f"<style>{_demo_css()}</style>",
            "</head>",
            "<body>",
            "<main>",
            "<header>",
            "<p>FutBotMX Nivel 3</p>",
            "<h1>Reel final y demo de presentacion</h1>",
            f"<span>{len(context['segments'])} segmentos | {context['summary']['duration_sec']:.1f}s sugeridos | MP4 local no versionado</span>",
            "</header>",
            '<section class="grid">',
            "".join(cards),
            "</section>",
            '<section class="render">',
            "<h2>Render local</h2>",
            '<p><a href="reel_render_plan.md">reel_render_plan.md</a> | <a href="reel_segments.csv">reel_segments.csv</a> | <a href="reel_manifest.csv">reel_manifest.csv</a></p>',
            f'<p><a href="{_esc(_rel_path(config.dashboard_html, output_dir))}">Dashboard Nivel 3</a></p>',
            "</section>",
            "</main>",
            "</body>",
            "</html>",
        ]
    ) + "\n"


def reel_manifest_rows(config: Level3ReelConfig, context: dict[str, Any]) -> list[dict[str, Any]]:
    output_dir = Path(config.output_dir)
    rows = [
        _manifest_row("config", "yaml", "config.yaml", "configs/default.yaml", True, "package", "Configuration snapshot."),
        _manifest_row("summary", "md", "summary.md", "reel_segments.csv", True, "package", "Reel package summary."),
        _manifest_row("reel_segments", "csv", "reel_segments.csv", config.highlights_csv, True, "timeline", "Selected frames and timestamps."),
        _manifest_row("reel_manifest", "csv", "reel_manifest.csv", "reel_segments.csv", True, "manifest", "Reel artifact manifest."),
        _manifest_row("reel_narrative", "md", "reel_narrative.md", config.events_json, True, "narrative", "Conservative narration script."),
        _manifest_row("reel_render_plan", "md", "reel_render_plan.md", "reel_ffmpeg_inputs.txt", True, "render_plan", "Local MP4 command documentation."),
        _manifest_row("render_reel_local", "sh", "render_reel_local.sh", "reel_ffmpeg_inputs.txt", True, "render_plan", "Local FFmpeg helper script."),
        _manifest_row("reel_ffmpeg_inputs", "txt", "reel_ffmpeg_inputs.txt", "reel_segments.csv", True, "render_plan", "Concat input list for local render."),
        _manifest_row("reel_demo", "html", "reel_demo.html", "reel_segments.csv", True, "demo", "Static reel demo page."),
        _manifest_row("reel_contact_sheet", "png", "reel_contact_sheet.png", "reel_segments.csv", True, "thumbnail", "Contact sheet of selected segments."),
        _manifest_row("local_reel_mp4", "mp4", _rel_path(config.local_reel_path, output_dir), "render_reel_local.sh", False, "local_output", "Not generated or versioned in Git."),
        _manifest_row("dashboard_html", "html", _rel_path(config.dashboard_html, output_dir), config.dashboard_html, True, "evidence", "Dashboard evidence link."),
    ]
    for segment in context["segments"]:
        rows.append(
            _manifest_row(
                segment["segment_id"],
                "png",
                segment["thumbnail_path"],
                "|".join(filter(None, [segment["source_overlay_path"], segment["minimap_path"], segment["reference_frame_path"]])),
                True,
                "thumbnail",
                f"Rank {segment['rank']} reel thumbnail.",
            )
        )
    source_paths = {
        "highlights_csv": config.highlights_csv,
        "events_json": config.events_json,
        "overlay_validation_csv": config.overlay_validation_csv,
        "visualization_manifest_csv": config.visualization_manifest_csv,
        "storyboard_manifest_csv": config.storyboard_manifest_csv,
    }
    if config.human_review_csv:
        source_paths["human_review_csv"] = config.human_review_csv
    for asset_id, path in source_paths.items():
        rows.append(_manifest_row(asset_id, Path(path).suffix.lstrip(".") or "artifact", _rel_path(path, output_dir), path, True, "evidence", "Linked source artifact."))
    return rows


def config_to_dict(config: Level3ReelConfig) -> dict[str, Any]:
    return asdict(config)


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


def _event_label(highlight: dict[str, str]) -> str:
    reasons = [part.strip() for part in str(highlight["reason"]).split(";") if part.strip()]
    return " | ".join(reasons[:3])


def _narration_for(highlight: dict[str, str], event: dict[str, Any]) -> str:
    narrative = str(event.get("narrative", "")).strip()
    if narrative:
        return narrative
    return (
        f"Highlight provisional en frames {highlight['frame_start']}-{highlight['frame_end']} "
        f"con score {float(highlight['score']):.1f}; motivos: {highlight['reason']}."
    )


def _selection_reason(
    highlight: dict[str, str],
    overlay_path: str,
    minimap_path: str,
    reference_path: str,
    config: Level3ReelConfig,
    review_status: str,
) -> str:
    reasons = ["ranking_highlight"]
    if float(highlight["confidence"]) >= config.min_confidence:
        reasons.append(f"confidence>={config.min_confidence:.2f}")
    if review_status != "sin_revision":
        reasons.append(f"review={review_status}")
    if overlay_path:
        reasons.append("overlay_evento")
    if minimap_path:
        reasons.append("minimap")
    if reference_path:
        reasons.append("frame_referencia")
    return ";".join(reasons)


def _optional_join(root: str | Path, path: str) -> str:
    if not path:
        return ""
    candidate = Path(path)
    return candidate.as_posix() if candidate.parent != Path(".") else (Path(root) / candidate).as_posix()


def _rel_path(path: str | Path, base_dir: str | Path) -> str:
    return Path(os.path.relpath(Path(path), start=Path(base_dir))).as_posix()


def _manifest_row(asset_id: str, asset_type: str, path: str, source_artifact: str, is_versioned: bool, role: str, notes: str) -> dict[str, Any]:
    return {
        "asset_id": asset_id,
        "asset_type": asset_type,
        "path": path,
        "source_artifact": source_artifact,
        "is_versioned": str(is_versioned).lower(),
        "role": role,
        "notes": notes,
    }


def _demo_css() -> str:
    return """
:root {
  --ink: #17201b;
  --muted: #5b675f;
  --line: #c9d6ce;
  --field: #e9f4ea;
  --paper: #fbfcfa;
  --panel: #ffffff;
  --blue: #315f9b;
  --green: #2f6f4f;
  --amber: #a36d1f;
}
* { box-sizing: border-box; }
body {
  margin: 0;
  background: var(--paper);
  color: var(--ink);
  font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
}
main {
  width: min(1120px, calc(100vw - 32px));
  margin: 0 auto;
  padding: 22px 0 36px;
}
header {
  border-bottom: 2px solid var(--line);
  padding-bottom: 16px;
}
header p {
  margin: 0 0 5px;
  color: var(--green);
  font-size: 13px;
  font-weight: 700;
  text-transform: uppercase;
}
h1 {
  margin: 0 0 8px;
  font-size: 38px;
  line-height: 1.05;
  letter-spacing: 0;
}
h2 {
  margin: 0;
  font-size: 17px;
  letter-spacing: 0;
}
header span,
article p,
.render p {
  color: var(--muted);
  font-size: 13px;
}
.grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 14px;
  padding: 18px 0;
}
article {
  background: var(--panel);
  border: 1px solid var(--line);
}
article img {
  width: 100%;
  aspect-ratio: 16 / 9;
  object-fit: contain;
  display: block;
  background: var(--field);
}
article h2,
article p {
  padding: 0 10px;
}
article h2 {
  padding-top: 10px;
}
.render {
  border-top: 1px solid var(--line);
  padding-top: 16px;
}
a {
  color: var(--blue);
  text-underline-offset: 2px;
}
@media (max-width: 760px) {
  main {
    width: min(100vw - 20px, 1120px);
  }
  .grid {
    grid-template-columns: 1fr;
  }
  h1 {
    font-size: 30px;
  }
}
"""


def _esc(value: Any) -> str:
    return html.escape(str(value), quote=True)
