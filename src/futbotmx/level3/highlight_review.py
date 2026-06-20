from __future__ import annotations

import csv
import html
import json
import os
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from futbotmx.ui import shared_css, ui_body_attrs


RULE_VERSION = "highlight_human_review_v0.1"
VALID_REVIEW_STATUSES = ("confiable", "provisional", "descartado")
REVIEW_FIELDS = [
    "clip_id",
    "highlight_id",
    "rank",
    "frame_start",
    "frame_end",
    "event_type",
    "score",
    "confidence",
    "reliability",
    "review_status",
    "reviewer",
    "reviewed_at",
    "notes",
    "overlay_path",
    "minimap_path",
    "event_summary",
    "source_highlights_csv",
    "source_overlay_validation_csv",
    "source_visualization_manifest_csv",
]
VALIDATION_FIELDS = ["highlight_id", "status", "issue", "notes"]
MANIFEST_FIELDS = ["asset_id", "asset_type", "path", "source_artifact", "is_versioned", "role", "notes"]


@dataclass(frozen=True)
class HighlightReviewConfig:
    highlights_csv: str = "experiments/test_022_level3_advanced_events/level3_highlights.csv"
    events_json: str = "experiments/test_022_level3_advanced_events/level3_events.json"
    overlay_validation_csv: str = "experiments/test_022_level3_advanced_events/overlay_validation.csv"
    advanced_events_dir: str = "experiments/test_022_level3_advanced_events"
    visualization_manifest_csv: str = "experiments/test_023_level3_visualizations/visualization_manifest.csv"
    storyboard_manifest_csv: str = "experiments/test_023_level3_visualizations/highlight_storyboard_manifest.csv"
    visualizations_dir: str = "experiments/test_023_level3_visualizations"
    output_dir: str = "experiments/test_035_human_review"
    reviewer: str = "human_reviewer"
    reviewed_at: str = ""
    top_highlights: int = 6


def build_highlight_review_package(config: HighlightReviewConfig) -> dict[str, Any]:
    output_dir = Path(config.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    context = build_highlight_review_context(config)
    rows = context["review_rows"]
    write_csv_rows(output_dir / "human_review.csv", rows, REVIEW_FIELDS)
    write_csv_rows(output_dir / "human_review_validation.csv", context["validation_rows"], VALIDATION_FIELDS)
    (output_dir / "human_review_panel.html").write_text(render_review_panel_html(context), encoding="utf-8")
    write_summary(output_dir / "summary.md", context)
    manifest = review_manifest_rows(config, context)
    write_csv_rows(output_dir / "human_review_manifest.csv", manifest, MANIFEST_FIELDS)
    context["manifest"] = manifest
    return context


def build_highlight_review_context(config: HighlightReviewConfig) -> dict[str, Any]:
    highlights = sorted(read_csv_rows(config.highlights_csv), key=lambda row: int(row["rank"]))
    events = read_json(config.events_json)
    overlays = read_csv_rows(config.overlay_validation_csv)
    visualizations = read_csv_rows(config.visualization_manifest_csv)
    storyboard_rows = read_csv_rows(config.storyboard_manifest_csv)
    events_by_id = {str(event.get("event_id", "")): event for event in events if isinstance(event, dict)}
    rows = build_review_rows(highlights, events_by_id, overlays, visualizations, storyboard_rows, config)
    validation_rows = validate_review_rows(rows)
    counts = Counter(str(row["review_status"]) for row in rows)
    return {
        "config": config,
        "rule_version": RULE_VERSION,
        "highlights": highlights,
        "events": events,
        "overlays": overlays,
        "visualizations": visualizations,
        "storyboard_rows": storyboard_rows,
        "review_rows": rows,
        "validation_rows": validation_rows,
        "status_counts": dict(sorted(counts.items())),
        "output_dir": Path(config.output_dir),
    }


def build_review_rows(
    highlights: list[dict[str, str]],
    events_by_id: dict[str, dict[str, Any]],
    overlay_rows: list[dict[str, str]],
    visualization_rows: list[dict[str, str]],
    storyboard_rows: list[dict[str, str]],
    config: HighlightReviewConfig,
) -> list[dict[str, Any]]:
    overlay_by_highlight = {str(row.get("highlight_id", "")): row for row in overlay_rows}
    minimap_by_highlight = {
        str(row.get("event_id", "")): row
        for row in visualization_rows
        if str(row.get("asset_id", "")).startswith("minimap_highlight")
    }
    storyboard_by_highlight = {str(row.get("highlight_id", "")): row for row in storyboard_rows}
    selected = highlights[: max(1, config.top_highlights)]
    rows: list[dict[str, Any]] = []
    for highlight in selected:
        highlight_id = str(highlight["highlight_id"])
        overlay = overlay_by_highlight.get(highlight_id, {})
        minimap = minimap_by_highlight.get(highlight_id, {})
        storyboard = storyboard_by_highlight.get(highlight_id, {})
        overlay_path = _join_optional(config.advanced_events_dir, overlay.get("asset_path", ""))
        minimap_path = _join_optional(config.visualizations_dir, minimap.get("path") or storyboard.get("minimap_path", ""))
        event = events_by_id.get(highlight_id, {})
        status = default_review_status(highlight, overlay_path, minimap_path)
        rows.append(
            {
                "clip_id": highlight.get("clip_id", ""),
                "highlight_id": highlight_id,
                "rank": highlight.get("rank", ""),
                "frame_start": highlight.get("frame_start", ""),
                "frame_end": highlight.get("frame_end", ""),
                "event_type": highlight.get("event_type", ""),
                "score": highlight.get("score", ""),
                "confidence": highlight.get("confidence", ""),
                "reliability": highlight.get("reliability", ""),
                "review_status": status,
                "reviewer": config.reviewer,
                "reviewed_at": config.reviewed_at,
                "notes": default_review_notes(status, highlight, overlay_path, minimap_path),
                "overlay_path": overlay_path,
                "minimap_path": minimap_path,
                "event_summary": event_summary(highlight, event),
                "source_highlights_csv": config.highlights_csv,
                "source_overlay_validation_csv": config.overlay_validation_csv,
                "source_visualization_manifest_csv": config.visualization_manifest_csv,
            }
        )
    return rows


def default_review_status(highlight: dict[str, str], overlay_path: str, minimap_path: str) -> str:
    confidence = _float(highlight.get("confidence"))
    reason = str(highlight.get("reason", ""))
    has_visual = bool(overlay_path or minimap_path)
    if not has_visual or confidence < 0.45:
        return "descartado"
    if confidence >= 0.86 and "respaldo_level2" in reason:
        return "confiable"
    return "provisional"


def default_review_notes(status: str, highlight: dict[str, str], overlay_path: str, minimap_path: str) -> str:
    if status == "descartado":
        return "Evidencia visual insuficiente o confianza baja; conservar el highlight original como evidencia no seleccionada."
    if status == "confiable":
        return "Overlay/minimapa disponible, confianza alta y respaldo Nivel 2; mantener lenguaje de analisis aproximado."
    assets = []
    if overlay_path:
        assets.append("overlay")
    if minimap_path:
        assets.append("minimapa")
    return f"Revision requiere confirmacion humana fina; assets disponibles: {', '.join(assets) or 'ninguno'}."


def event_summary(highlight: dict[str, str], event: dict[str, Any]) -> str:
    narrative = str(event.get("narrative", "")).strip()
    if narrative:
        return narrative
    return (
        f"Rank {highlight.get('rank', '')} frames {highlight.get('frame_start', '')}-{highlight.get('frame_end', '')}; "
        f"score {highlight.get('score', '')}; motivo {highlight.get('reason', '')}."
    )


def validate_review_rows(rows: list[dict[str, Any]]) -> list[dict[str, str]]:
    validation: list[dict[str, str]] = []
    seen_ids: set[str] = set()
    for row in rows:
        highlight_id = str(row.get("highlight_id", ""))
        status = str(row.get("review_status", ""))
        issues: list[str] = []
        if not highlight_id:
            issues.append("missing_highlight_id")
        if highlight_id in seen_ids:
            issues.append("duplicate_highlight_id")
        seen_ids.add(highlight_id)
        if status not in VALID_REVIEW_STATUSES:
            issues.append("invalid_review_status")
        if not row.get("reviewer"):
            issues.append("missing_reviewer")
        if not (row.get("overlay_path") or row.get("minimap_path")) and status != "descartado":
            issues.append("visual_asset_missing_for_kept_highlight")
        validation.append(
            {
                "highlight_id": highlight_id,
                "status": "fail" if issues else "pass",
                "issue": "|".join(issues) if issues else "none",
                "notes": "Editable human_review.csv validation row.",
            }
        )
    if not rows:
        validation.append({"highlight_id": "", "status": "fail", "issue": "no_review_rows", "notes": "No highlights available for review."})
    return validation


def render_review_panel_html(context: dict[str, Any]) -> str:
    config: HighlightReviewConfig = context["config"]
    output_dir = Path(config.output_dir)
    rows = context["review_rows"]
    data_json = json.dumps(rows, ensure_ascii=True)
    cards = "\n".join(_review_card(row, output_dir) for row in rows)
    return "\n".join(
        [
            "<!doctype html>",
            '<html lang="es">',
            "<head>",
            '<meta charset="utf-8">',
            '<meta name="viewport" content="width=device-width, initial-scale=1">',
            "<title>FutBotMX Revision de Highlights</title>",
            f"<style>{_panel_css()}</style>",
            "</head>",
            f'<body {ui_body_attrs("review", "highlight-review-page")}>',
            '<main class="fb-shell">',
            '<header class="fb-topbar">',
            "<div>",
            '<p class="fb-eyebrow">FutBotMX Nivel 3</p>',
            "<h1>Revision humana de highlights</h1>",
            "</div>",
            f'<button type="button" id="exportCsv" class="btn-primary">Exportar CSV</button>',
            "</header>",
            '<section class="summary" aria-label="Resumen">',
            _summary_badges(context["status_counts"]),
            "</section>",
            '<section class="review-grid" aria-label="Highlights">',
            cards,
            "</section>",
            "</main>",
            f"<script>window.REVIEW_ROWS = {data_json};{_panel_js()}</script>",
            "</body>",
            "</html>",
        ]
    ) + "\n"


def write_summary(path: Path, context: dict[str, Any]) -> None:
    config: HighlightReviewConfig = context["config"]
    validation_fails = sum(1 for row in context["validation_rows"] if row["status"] != "pass")
    lines = [
        "# Revision Humana De Highlights",
        "",
        "## Resultado",
        "",
        "- Estado: `generado`.",
        f"- Regla: `{RULE_VERSION}`.",
        f"- Reviewer inicial: `{config.reviewer}`.",
        f"- Fecha revision inicial: `{config.reviewed_at or 'no_especificada'}`.",
        f"- Highlights revisados: `{len(context['review_rows'])}`.",
        f"- Estados: `{context['status_counts']}`.",
        f"- Validaciones fallidas: `{validation_fails}`.",
        "",
        "## Operacion",
        "",
        "- `human_review_panel.html` muestra overlay, mini-mapa y datos de cada highlight top.",
        "- El panel permite cambiar `confiable`, `provisional` o `descartado`, editar notas y exportar un CSV.",
        "- `human_review.csv` es editable manualmente y se valida con `human_review_validation.csv`.",
        "- Dashboard y reel pueden consumir este CSV con `--human-review` sin borrar `level3_highlights.csv` original.",
        "",
        "## Artefactos",
        "",
        "- `config.yaml`",
        "- `human_review_panel.html`",
        "- `human_review.csv`",
        "- `human_review_validation.csv`",
        "- `human_review_manifest.csv`",
        "- `summary.md`",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def review_manifest_rows(config: HighlightReviewConfig, context: dict[str, Any]) -> list[dict[str, Any]]:
    rows = [
        _manifest_row("config", "yaml", "config.yaml", "configs/default.yaml", True, "configuration", "Configuration snapshot."),
        _manifest_row("summary", "md", "summary.md", "human_review.csv", True, "summary", "Human review package summary."),
        _manifest_row("human_review_panel", "html", "human_review_panel.html", config.highlights_csv, True, "review_panel", "Local editable panel."),
        _manifest_row("human_review", "csv", "human_review.csv", config.highlights_csv, True, "human_review", "Editable review status by highlight."),
        _manifest_row("human_review_validation", "csv", "human_review_validation.csv", "human_review.csv", True, "validation", "Validation rows for editable review CSV."),
        _manifest_row("human_review_manifest", "csv", "human_review_manifest.csv", "human_review_panel.html", True, "manifest", "Review package manifest."),
        _manifest_row("highlights_csv", "csv", _rel_path(config.highlights_csv, config.output_dir), config.highlights_csv, True, "source", "Original highlights are preserved."),
        _manifest_row("overlay_validation_csv", "csv", _rel_path(config.overlay_validation_csv, config.output_dir), config.overlay_validation_csv, True, "source", "Overlay validation source."),
        _manifest_row("visualization_manifest_csv", "csv", _rel_path(config.visualization_manifest_csv, config.output_dir), config.visualization_manifest_csv, True, "source", "Minimap source manifest."),
    ]
    return rows


def write_csv_rows(path: str | Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows([{field: row.get(field, "") for field in fieldnames} for row in rows])


def read_csv_rows(path: str | Path) -> list[dict[str, str]]:
    with Path(path).open("r", newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def read_json(path: str | Path) -> Any:
    with Path(path).open("r", encoding="utf-8") as handle:
        return json.load(handle)


def config_to_dict(config: HighlightReviewConfig) -> dict[str, Any]:
    return asdict(config)


def _review_card(row: dict[str, Any], output_dir: Path) -> str:
    overlay = _img_html(row.get("overlay_path", ""), output_dir, "Overlay highlight")
    minimap = _img_html(row.get("minimap_path", ""), output_dir, "Mini-mapa")
    options = "".join(
        f'<option value="{status}"{" selected" if row.get("review_status") == status else ""}>{status}</option>'
        for status in VALID_REVIEW_STATUSES
    )
    return f"""
<article class="review-card" data-highlight-id="{_esc(row['highlight_id'])}">
  <div class="media">{overlay}{minimap}</div>
  <div class="review-body">
    <div class="title-row">
      <h2>Rank {_esc(row['rank'])} | {_esc(row['highlight_id'])}</h2>
      <select name="review_status">{options}</select>
    </div>
    <dl>
      <dt>Clip</dt><dd>{_esc(row['clip_id'])}</dd>
      <dt>Frames</dt><dd>{_esc(row['frame_start'])}-{_esc(row['frame_end'])}</dd>
      <dt>Score</dt><dd>{_esc(row['score'])}</dd>
      <dt>Confianza</dt><dd>{_esc(row['confidence'])}</dd>
      <dt>Reliability</dt><dd>{_esc(row['reliability'])}</dd>
    </dl>
    <p>{_esc(row['event_summary'])}</p>
    <label>Notas<textarea name="notes">{_esc(row['notes'])}</textarea></label>
  </div>
</article>"""


def _img_html(path: Any, output_dir: Path, title: str) -> str:
    if not path:
        return f'<figure><div class="missing">sin imagen</div><figcaption>{_esc(title)}</figcaption></figure>'
    rel = _rel_path(str(path), output_dir)
    return f'<figure><a href="{_esc(rel)}"><img src="{_esc(rel)}" alt="{_esc(title)}"></a><figcaption>{_esc(title)}</figcaption></figure>'


def _summary_badges(counts: dict[str, int]) -> str:
    return "".join(f"<span>{_esc(status)}: <strong>{count}</strong></span>" for status, count in counts.items())


def _panel_js() -> str:
    return r"""
function csvEscape(value) {
  const text = String(value ?? "");
  return /[",\n]/.test(text) ? '"' + text.replaceAll('"', '""') + '"' : text;
}
function collectRows() {
  const byId = new Map(window.REVIEW_ROWS.map(row => [row.highlight_id, {...row}]));
  document.querySelectorAll(".review-card").forEach(card => {
    const row = byId.get(card.dataset.highlightId);
    row.review_status = card.querySelector('[name="review_status"]').value;
    row.notes = card.querySelector('[name="notes"]').value;
  });
  return Array.from(byId.values());
}
document.getElementById("exportCsv").addEventListener("click", () => {
  const fields = Object.keys(window.REVIEW_ROWS[0] || {});
  const lines = [fields.join(",")].concat(collectRows().map(row => fields.map(field => csvEscape(row[field])).join(",")));
  const blob = new Blob([lines.join("\n") + "\n"], {type: "text/csv;charset=utf-8"});
  const link = document.createElement("a");
  link.href = URL.createObjectURL(blob);
  link.download = "human_review.csv";
  link.click();
  URL.revokeObjectURL(link.href);
});
"""


def _panel_css() -> str:
    return shared_css() + """
:root {
  --ink: #05261d;
  --muted: #52665d;
  --line: #c7e2d1;
  --paper: #f5f9ef;
  --panel: #ffffff;
  --field: #e9ffd8;
  --blue: #00c853;
  --green: #00d25b;
}
* { box-sizing: border-box; }
body {
  margin: 0;
  background:
    linear-gradient(90deg, rgba(0,200,83,.08) 1px, transparent 1px),
    linear-gradient(180deg, rgba(0,75,58,.07) 1px, transparent 1px),
    linear-gradient(90deg, rgba(183,243,0,.18) 0 24%, transparent 24%),
    radial-gradient(circle at 84% 0%, rgba(0,75,58,.14), transparent 30%),
    var(--paper);
  background-size: 52px 52px, 52px 52px, auto, auto, auto;
  color: var(--ink);
  font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
}
main {
  width: min(1180px, calc(100vw - 32px));
  margin: 0 auto;
  padding: 20px 0 36px;
}
header {
  display: flex;
  justify-content: space-between;
  align-items: end;
  gap: 20px;
  border: 1px solid var(--line);
  border-bottom: 4px solid #b7f300;
  border-radius: 8px;
  padding: 16px;
  background: linear-gradient(135deg, #004b3a, #00c853);
  color: #ffffff;
}
header p {
  margin: 0 0 5px;
  color: #eaffd6;
  font-size: 13px;
  font-weight: 700;
  text-transform: uppercase;
}
h1 {
  margin: 0;
  font-size: 38px;
  line-height: 1.05;
  letter-spacing: 0;
  color: inherit;
}
button,
select {
  border: 1px solid var(--line);
  background: var(--panel);
  color: var(--ink);
  padding: 8px 10px;
  font: inherit;
}
button {
  background: var(--green);
  color: white;
  border-color: var(--green);
}
.summary {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  padding: 16px 0;
}
.summary span {
  background: var(--panel);
  border: 1px solid var(--line);
  padding: 7px 10px;
  color: var(--muted);
}
.review-grid {
  display: grid;
  gap: 14px;
}
.review-card {
  display: grid;
  grid-template-columns: minmax(0, 1.15fr) minmax(320px, 0.85fr);
  gap: 14px;
  border-top: 1px solid var(--line);
  padding-top: 14px;
}
.media {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
}
figure {
  margin: 0;
  border: 1px solid var(--line);
  background: var(--panel);
  display: grid;
  grid-template-rows: minmax(220px, 320px) auto;
}
img {
  width: 100%;
  height: 100%;
  object-fit: contain;
  display: block;
  background: var(--field);
}
figcaption {
  border-top: 1px solid var(--line);
  padding: 8px;
  color: var(--muted);
  font-size: 13px;
}
.missing {
  display: grid;
  place-items: center;
  min-height: 220px;
  color: var(--muted);
  background: var(--field);
}
.review-body {
  background: var(--panel);
  border: 1px solid var(--line);
  padding: 12px;
}
.title-row {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  align-items: center;
}
h2 {
  margin: 0;
  font-size: 18px;
  letter-spacing: 0;
}
dl {
  display: grid;
  grid-template-columns: 92px 1fr;
  gap: 4px 8px;
  font-size: 13px;
}
dt {
  color: var(--muted);
}
dd {
  margin: 0;
}
p,
label {
  color: var(--muted);
  font-size: 13px;
}
textarea {
  display: block;
  width: 100%;
  min-height: 78px;
  resize: vertical;
  border: 1px solid var(--line);
  margin-top: 5px;
  padding: 8px;
  font: inherit;
}
a { color: var(--blue); }
@media (max-width: 920px) {
  header,
  .review-card,
  .media {
    display: block;
  }
  figure {
    margin-bottom: 10px;
  }
}
"""


def _manifest_row(asset_id: str, asset_type: str, path: str, source: str, versioned: bool, role: str, notes: str) -> dict[str, Any]:
    return {
        "asset_id": asset_id,
        "asset_type": asset_type,
        "path": path,
        "source_artifact": source,
        "is_versioned": str(versioned).lower(),
        "role": role,
        "notes": notes,
    }


def _join_optional(root: str | Path, path: str) -> str:
    if not path:
        return ""
    candidate = Path(path)
    return candidate.as_posix() if candidate.is_absolute() or candidate.parent != Path(".") else (Path(root) / candidate).as_posix()


def _rel_path(path: str | Path, base_dir: str | Path) -> str:
    return Path(os.path.relpath(Path(path), start=Path(base_dir))).as_posix()


def _float(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _esc(value: Any) -> str:
    return html.escape(str(value), quote=True)
