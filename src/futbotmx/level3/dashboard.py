from __future__ import annotations

import csv
import html
import json
import os
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from futbotmx.ui import shared_css, ui_body_attrs


RULE_VERSION = "level3_dashboard_v0.1"


@dataclass(frozen=True)
class Level3DashboardConfig:
    metrics_csv: str = "experiments/test_021_level3_tactical_metrics/level3_metrics.csv"
    metrics_json: str = "experiments/test_021_level3_tactical_metrics/level3_metrics.json"
    interaction_edges_csv: str = "experiments/test_021_level3_tactical_metrics/interaction_edges.csv"
    highlights_csv: str = "experiments/test_022_level3_advanced_events/level3_highlights.csv"
    events_json: str = "experiments/test_022_level3_advanced_events/level3_events.json"
    narrative_md: str = "experiments/test_022_level3_advanced_events/level3_narrative.md"
    visualizations_dir: str = "experiments/test_023_level3_visualizations"
    visualization_manifest_csv: str = "experiments/test_023_level3_visualizations/visualization_manifest.csv"
    human_review_csv: str = ""
    output_dir: str = "experiments/test_024_level3_dashboard"
    top_highlights: int = 6
    top_edges: int = 5


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


def build_dashboard(config: Level3DashboardConfig) -> dict[str, Any]:
    output_dir = Path(config.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    context = build_dashboard_context(config)
    html_path = output_dir / "dashboard.html"
    html_path.write_text(render_dashboard_html(context), encoding="utf-8")
    manifest = dashboard_manifest_rows(config, context)
    write_dashboard_manifest(output_dir / "dashboard_manifest.csv", manifest)
    context["manifest"] = manifest
    context["dashboard_html"] = html_path
    return context


def build_dashboard_context(config: Level3DashboardConfig) -> dict[str, Any]:
    output_dir = Path(config.output_dir)
    metrics_rows = read_csv_rows(config.metrics_csv)
    metrics_json = read_json(config.metrics_json)
    edge_rows = read_csv_rows(config.interaction_edges_csv)
    highlight_rows = sorted(read_csv_rows(config.highlights_csv), key=lambda row: int(row["rank"]))
    review_rows = read_optional_csv_rows(config.human_review_csv)
    reviewed_highlights = apply_human_review(highlight_rows, review_rows)
    events = read_json(config.events_json)
    visualization_rows = read_csv_rows(config.visualization_manifest_csv)
    clip_metrics = _clip_metrics(metrics_rows)
    track_control = _track_control_rows(metrics_rows)
    event_counts = Counter(str(event.get("event_type", "unknown")) for event in events)
    reliability_counts = Counter(str(event.get("reliability", "unknown")) for event in events)
    pass_chains = [event for event in events if str(event.get("event_type")) == "pass_chain"]
    top_highlights = selectable_highlights(reviewed_highlights)[: config.top_highlights]
    top_edges = sorted(edge_rows, key=lambda row: float(row.get("weight") or 0), reverse=True)[: config.top_edges]
    primary_clip = top_highlights[0]["clip_id"] if top_highlights else ""
    clips = sorted(clip_metrics)
    visual_assets = _select_visual_assets(visualization_rows, primary_clip)
    source_paths = {
        "metrics_csv": config.metrics_csv,
        "metrics_json": config.metrics_json,
        "interaction_edges_csv": config.interaction_edges_csv,
        "highlights_csv": config.highlights_csv,
        "events_json": config.events_json,
        "narrative_md": config.narrative_md,
        "visualization_manifest_csv": config.visualization_manifest_csv,
    }
    if config.human_review_csv:
        source_paths["human_review_csv"] = config.human_review_csv
    return {
        "config": config,
        "rule_version": RULE_VERSION,
        "clips": clips,
        "primary_clip": primary_clip,
        "metrics_rows": metrics_rows,
        "metrics_json": metrics_json,
        "edge_rows": edge_rows,
        "highlight_rows": highlight_rows,
        "review_rows": review_rows,
        "reviewed_highlights": reviewed_highlights,
        "events": events,
        "visualization_rows": visualization_rows,
        "clip_metrics": clip_metrics,
        "track_control": track_control,
        "event_counts": event_counts,
        "reliability_counts": reliability_counts,
        "pass_chains": pass_chains,
        "top_highlights": top_highlights,
        "top_edges": top_edges,
        "visual_assets": visual_assets,
        "source_paths": source_paths,
        "summary": _dashboard_summary(metrics_json, metrics_rows, reviewed_highlights, events, edge_rows, pass_chains, review_rows),
        "output_dir": output_dir,
    }


def render_dashboard_html(context: dict[str, Any]) -> str:
    config: Level3DashboardConfig = context["config"]
    output_dir = Path(config.output_dir)
    summary = context["summary"]
    visual_assets = context["visual_assets"]
    return "\n".join(
        [
            "<!doctype html>",
            '<html lang="es">',
            "<head>",
            '<meta charset="utf-8">',
            '<meta name="viewport" content="width=device-width, initial-scale=1">',
            "<title>FutBotMX Nivel 3 Dashboard</title>",
            f"<style>{_dashboard_css()}</style>",
            "</head>",
            f'<body {ui_body_attrs("report", "dashboard-page")}>',
            '<main class="dashboard-shell fb-shell">',
            _header_html(context),
            _summary_html(summary),
            _clip_metrics_html(context),
            _visual_gallery_html(visual_assets, output_dir, config),
            _highlights_html(context),
            _evidence_html(context, output_dir),
            "</main>",
            "</body>",
            "</html>",
        ]
    ) + "\n"


def dashboard_manifest_rows(config: Level3DashboardConfig, context: dict[str, Any]) -> list[dict[str, Any]]:
    output_dir = Path(config.output_dir)
    rows = [
        _manifest_row("dashboard_html", "html", "dashboard.html", "|".join(context["source_paths"].values()), True, "Static local dashboard."),
        _manifest_row("summary", "md", "summary.md", "dashboard.html", True, "Dashboard generation summary."),
        _manifest_row("config", "yaml", "config.yaml", "configs/default.yaml", True, "Configuration snapshot."),
        _manifest_row("dashboard_manifest", "csv", "dashboard_manifest.csv", "dashboard.html", True, "Dashboard asset manifest."),
    ]
    for source_id, path in context["source_paths"].items():
        rows.append(_manifest_row(source_id, _suffix_type(path), _rel_path(path, output_dir), path, True, "Linked evidence artifact."))
    visualizations_dir = Path(config.visualizations_dir)
    for asset in context["visual_assets"].values():
        if not asset:
            continue
        rows.append(
            _manifest_row(
                str(asset["asset_id"]),
                str(asset["asset_type"]),
                _rel_path(visualizations_dir / str(asset["path"]), output_dir),
                str(asset["source_artifact"]),
                str(asset["is_versioned"]) == "true",
                str(asset["notes"]),
            )
        )
    return rows


def write_dashboard_manifest(path: str | Path, rows: list[dict[str, Any]]) -> None:
    fieldnames = ["asset_id", "asset_type", "path", "source_artifact", "is_versioned", "notes"]
    write_csv_rows(path, rows, fieldnames)


def config_to_dict(config: Level3DashboardConfig) -> dict[str, Any]:
    return asdict(config)


def _dashboard_summary(
    metrics_json: dict[str, Any],
    metrics_rows: list[dict[str, str]],
    highlights: list[dict[str, str]],
    events: list[dict[str, Any]],
    edge_rows: list[dict[str, str]],
    pass_chains: list[dict[str, Any]],
    review_rows: list[dict[str, str]],
) -> dict[str, Any]:
    json_summary = metrics_json.get("summary", {}) if isinstance(metrics_json, dict) else {}
    top_selectable = selectable_highlights(highlights)
    top_score = float(top_selectable[0]["score"]) if top_selectable else 0.0
    clip_ids = sorted({str(row["clip_id"]) for row in metrics_rows if row.get("clip_id")})
    interaction_samples = int(float(json_summary.get("interaction_samples", 0)))
    if not interaction_samples:
        interaction_samples = sum(int(float(row.get("value") or 0)) for row in metrics_rows if row.get("metric_name") == "interaction_samples")
    review_counts = Counter(str(row.get("review_status", "sin_revision") or "sin_revision") for row in highlights)
    if not review_rows:
        review_counts = Counter({"sin_revision": len(highlights)})
    return {
        "clips": len(clip_ids),
        "clip_ids": clip_ids,
        "top_highlight_score": top_score,
        "highlights": len(highlights),
        "metrics": len(metrics_rows),
        "events": len(events),
        "interaction_samples": interaction_samples,
        "graph_edges": len(edge_rows),
        "pass_chains": len(pass_chains),
        "frames_analyzed": int(float(json_summary.get("frames_analyzed", 0))),
        "reviewed_highlights": len(review_rows),
        "kept_highlights": sum(1 for row in highlights if row.get("review_status") != "descartado"),
        "discarded_highlights": sum(1 for row in highlights if row.get("review_status") == "descartado"),
        "review_counts": dict(sorted(review_counts.items())),
    }


def apply_human_review(highlights: list[dict[str, str]], review_rows: list[dict[str, str]]) -> list[dict[str, str]]:
    by_id = {str(row.get("highlight_id", "")): row for row in review_rows}
    enriched: list[dict[str, str]] = []
    for row in highlights:
        review = by_id.get(str(row.get("highlight_id", "")), {})
        item = dict(row)
        item["review_status"] = str(review.get("review_status", "sin_revision") or "sin_revision")
        item["reviewer"] = str(review.get("reviewer", ""))
        item["reviewed_at"] = str(review.get("reviewed_at", ""))
        item["review_notes"] = str(review.get("notes", ""))
        enriched.append(item)
    return enriched


def selectable_highlights(highlights: list[dict[str, str]]) -> list[dict[str, str]]:
    kept = [row for row in highlights if row.get("review_status") != "descartado"]
    return kept if kept else highlights


def _clip_metrics(metrics_rows: list[dict[str, str]]) -> dict[str, dict[str, dict[str, str]]]:
    grouped: dict[str, dict[str, dict[str, str]]] = defaultdict(dict)
    for row in metrics_rows:
        if row.get("entity_type") != "clip":
            continue
        grouped[str(row["clip_id"])][str(row["metric_name"])] = row
    return dict(grouped)


def _track_control_rows(metrics_rows: list[dict[str, str]]) -> list[dict[str, str]]:
    rows = [row for row in metrics_rows if row.get("metric_name") == "mean_control_percent"]
    return sorted(rows, key=lambda row: (str(row["clip_id"]), -float(row["value"])))


def _select_visual_assets(visualization_rows: list[dict[str, str]], primary_clip: str) -> dict[str, dict[str, str] | None]:
    by_asset = {row["asset_id"]: row for row in visualization_rows}
    primary_voronoi = _first_asset(visualization_rows, "voronoi_", primary_clip)
    primary_original = _first_asset(visualization_rows, "voronoi_original_", primary_clip)
    return {
        "storyboard": by_asset.get("highlight_storyboard"),
        "interaction_graph": by_asset.get("interaction_graph"),
        "primary_voronoi": primary_voronoi,
        "primary_voronoi_original": primary_original,
    }


def _first_asset(rows: list[dict[str, str]], prefix: str, clip_id: str) -> dict[str, str] | None:
    filtered = [row for row in rows if str(row.get("asset_id", "")).startswith(prefix)]
    if clip_id:
        filtered = [row for row in filtered if row.get("clip_id") == clip_id] or filtered
    return filtered[0] if filtered else None


def _header_html(context: dict[str, Any]) -> str:
    clips = ", ".join(context["summary"]["clip_ids"])
    return f"""
<header class="dashboard-header fb-topbar">
  <div>
    <p class="eyebrow fb-eyebrow">FutBotMX Nivel 3</p>
    <h1>Dashboard tactico avanzado</h1>
  </div>
  <div class="status-strip fb-status-strip">
    <span>Estado: generado</span>
    <span>Regla: {_esc(context["rule_version"])}</span>
    <span>Clips: {_esc(clips)}</span>
  </div>
</header>"""


def _summary_html(summary: dict[str, Any]) -> str:
    cards = [
        ("Score top", f"{summary['top_highlight_score']:.1f}", "highlight provisional rank 1"),
        ("Highlights", str(summary["highlights"]), "ranking completo"),
        ("Revision", str(summary["kept_highlights"]), f"descartados {summary['discarded_highlights']}"),
        ("Metricas", str(summary["metrics"]), "CSV Nivel 3"),
        ("Interacciones", str(summary["interaction_samples"]), "muestras tacticas"),
        ("Aristas", str(summary["graph_edges"]), "grafo agregado"),
        ("Cadenas", str(summary["pass_chains"]), "pases conservadores"),
    ]
    items = "\n".join(f'<li><span>{_esc(label)}</span><strong>{_esc(value)}</strong><em>{_esc(note)}</em></li>' for label, value, note in cards)
    return f"""
<ul class="summary-grid" aria-label="Resumen">
  {items}
</ul>"""


def _clip_metrics_html(context: dict[str, Any]) -> str:
    rows = []
    for clip_id in context["clips"]:
        metrics = context["clip_metrics"].get(clip_id, {})
        rows.append(
            "<tr>"
            f"<th>{_esc(clip_id)}</th>"
            f"<td>{_metric_value(metrics, 'frames_analyzed', 0)}</td>"
            f"<td>{_metric_value(metrics, 'mean_control_entropy', 3)}</td>"
            f"<td>{_metric_value(metrics, 'interaction_samples', 0)}</td>"
            f"<td>{_metric_value(metrics, 'graph_edges', 0)}</td>"
            f"<td>{_metric_confidence(metrics)}</td>"
            "</tr>"
        )
    control_rows = "\n".join(
        "<tr>"
        f"<td>{_esc(row['clip_id'])}</td>"
        f"<td>{_esc(row['entity_id'])}</td>"
        f"<td>{float(row['value']):.1f}%</td>"
        f"<td>{_esc(_note_value(row.get('notes', ''), 'dominant_zone'))}</td>"
        f"<td>{float(row['confidence']):.2f}</td>"
        "</tr>"
        for row in context["track_control"]
    )
    return f"""
<section class="metric-band" aria-label="Metricas por clip">
  <div class="section-heading">
    <h2>Metricas por clip</h2>
    <p>Comparacion normalizada sobre tracks rectificados y grilla de control espacial.</p>
  </div>
  <table>
    <thead><tr><th>Clip</th><th>Frames</th><th>Entropia control</th><th>Interacciones</th><th>Aristas</th><th>Confianza</th></tr></thead>
    <tbody>{"".join(rows)}</tbody>
  </table>
  <div class="section-heading secondary-heading">
    <h2>Control por robot</h2>
    <p>Fallback por robot individual cuando no hay equipo confiable.</p>
  </div>
  <table>
    <thead><tr><th>Clip</th><th>Robot</th><th>Control medio</th><th>Zona dominante</th><th>Confianza</th></tr></thead>
    <tbody>{control_rows}</tbody>
  </table>
</section>"""


def _visual_gallery_html(assets: dict[str, dict[str, str] | None], output_dir: Path, config: Level3DashboardConfig) -> str:
    visualizations_dir = Path(config.visualizations_dir)
    panels = [
        ("Storyboard", assets.get("storyboard"), "Highlights principales con referencia, mini-mapa y texto conservador."),
        ("Grafo", assets.get("interaction_graph"), "Nodos y aristas ponderadas por duracion/frecuencia."),
        ("Voronoi mini-mapa", assets.get("primary_voronoi"), "Control espacial aproximado sobre cancha normalizada."),
        ("Voronoi proyectado", assets.get("primary_voronoi_original"), "Proyeccion sobre overlay Nivel 2 cuando existe homografia."),
    ]
    html_panels = []
    for title, asset, caption in panels:
        if not asset:
            html_panels.append(f'<figure><div class="missing">sin asset</div><figcaption><strong>{_esc(title)}</strong><span>{_esc(caption)}</span></figcaption></figure>')
            continue
        image = _rel_path(visualizations_dir / asset["path"], output_dir)
        html_panels.append(
            "<figure>"
            f'<a href="{_esc(image)}"><img src="{_esc(image)}" alt="{_esc(title)}"></a>'
            f"<figcaption><strong>{_esc(title)}</strong><span>{_esc(caption)}</span></figcaption>"
            "</figure>"
        )
    return f"""
<section class="visual-band" aria-label="Visualizaciones">
  <div class="section-heading">
    <h2>Visualizaciones</h2>
    <p>Assets ligeros versionados desde la Actividad 5.</p>
  </div>
  <div class="visual-grid">
    {"".join(html_panels)}
  </div>
</section>"""


def _highlights_html(context: dict[str, Any]) -> str:
    highlight_rows = "\n".join(
        "<tr>"
        f"<td>{_esc(row['rank'])}</td>"
        f"<td>{_esc(row['clip_id'])}</td>"
        f"<td>{_esc(row['frame_start'])}-{_esc(row['frame_end'])}</td>"
        f"<td>{float(row['score']):.1f}</td>"
        f"<td>{float(row['confidence']):.2f}</td>"
        f"<td>{_esc(row.get('review_status', 'sin_revision'))}</td>"
        f"<td>{_esc(row['reason'])}</td>"
        "</tr>"
        for row in context["top_highlights"]
    )
    edge_rows = "\n".join(
        "<tr>"
        f"<td>{_esc(row['clip_id'])}</td>"
        f"<td>{_esc(row['source'])} -> {_esc(row['target'])}</td>"
        f"<td>{_esc(row['edge_type'])}</td>"
        f"<td>{_esc(row['frames'])}</td>"
        f"<td>{float(row['mean_distance_norm']):.3f}</td>"
        f"<td>{float(row['weight']):.1f}</td>"
        f"<td>{float(row['confidence']):.2f}</td>"
        "</tr>"
        for row in context["top_edges"]
    )
    event_counts = ", ".join(f"{key}: {value}" for key, value in sorted(context["event_counts"].items()))
    reliability_counts = ", ".join(f"{key}: {value}" for key, value in sorted(context["reliability_counts"].items()))
    review_counts = ", ".join(f"{key}: {value}" for key, value in sorted(context["summary"]["review_counts"].items()))
    return f"""
<section class="timeline-band" aria-label="Highlights y grafo">
  <div class="section-heading">
    <h2>Highlights</h2>
    <p>{_esc(event_counts)} | {_esc(reliability_counts)} | revision {_esc(review_counts)}</p>
  </div>
  <table>
    <thead><tr><th>Rank</th><th>Clip</th><th>Frames</th><th>Score</th><th>Conf.</th><th>Revision</th><th>Motivo</th></tr></thead>
    <tbody>{highlight_rows}</tbody>
  </table>
  <div class="section-heading secondary-heading">
    <h2>Aristas principales</h2>
    <p>Interacciones agregadas con ponderacion por duracion, distancia y confianza.</p>
  </div>
  <table>
    <thead><tr><th>Clip</th><th>Conexion</th><th>Tipo</th><th>Frames</th><th>Dist.</th><th>Peso</th><th>Conf.</th></tr></thead>
    <tbody>{edge_rows}</tbody>
  </table>
</section>"""


def _evidence_html(context: dict[str, Any], output_dir: Path) -> str:
    links = "\n".join(
        "<tr>"
        f"<td>{_esc(source_id)}</td>"
        f'<td><a href="{_esc(_rel_path(path, output_dir))}">{_esc(_rel_path(path, output_dir))}</a></td>'
        "<td>versionado</td>"
        "</tr>"
        for source_id, path in context["source_paths"].items()
    )
    return f"""
<section class="evidence-band" aria-label="Evidencia">
  <div class="section-heading">
    <h2>Evidencia</h2>
    <p>Links relativos a CSV, JSON, Markdown y manifests usados para construir esta vista.</p>
  </div>
  <table>
    <thead><tr><th>Fuente</th><th>Ruta</th><th>Estado</th></tr></thead>
    <tbody>{links}</tbody>
  </table>
</section>"""


def _dashboard_css() -> str:
    return shared_css() + """
:root {
  color-scheme: light;
  --ink: #05261d;
  --muted: #52665d;
  --line: #c7e2d1;
  --field: #e9ffd8;
  --paper: #f5f9ef;
  --panel: #ffffff;
  --blue: #00c853;
  --green: #00d25b;
  --red: #b7f300;
  --amber: #d6ad38;
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
.dashboard-shell {
  width: min(1180px, calc(100vw - 32px));
  margin: 0 auto;
  padding: 20px 0 36px;
}
.dashboard-header {
  display: flex;
  justify-content: space-between;
  gap: 24px;
  align-items: end;
  padding: 16px;
  border: 1px solid var(--line);
  border-bottom: 4px solid var(--red);
  border-radius: 8px;
  background: linear-gradient(135deg, #004b3a, #00c853);
  color: #ffffff;
}
.eyebrow {
  margin: 0 0 4px;
  color: #eaffd6;
  font-size: 13px;
  font-weight: 700;
  text-transform: uppercase;
}
h1 {
  margin: 0;
  font-size: 40px;
  line-height: 1.02;
  letter-spacing: 0;
  color: inherit;
}
h2 {
  margin: 0;
  font-size: 19px;
  letter-spacing: 0;
}
.status-strip {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  justify-content: flex-end;
  color: var(--muted);
  font-size: 13px;
}
.status-strip span {
  border: 1px solid var(--line);
  padding: 6px 9px;
  background: var(--panel);
}
.summary-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(135px, 1fr));
  gap: 10px;
  list-style: none;
  padding: 18px 0;
  margin: 0;
}
.summary-grid li {
  min-height: 94px;
  border-left: 4px solid var(--green);
  background: var(--panel);
  padding: 12px;
  display: grid;
  align-content: space-between;
  box-shadow: 0 1px 0 rgba(23, 32, 27, 0.08);
}
.summary-grid li:nth-child(2n) { border-left-color: var(--blue); }
.summary-grid li:nth-child(3n) { border-left-color: var(--amber); }
.summary-grid li:nth-child(5n) { border-left-color: var(--red); }
.summary-grid span,
figcaption span,
.section-heading p,
.summary-grid em {
  color: var(--muted);
}
.summary-grid span {
  font-size: 12px;
  text-transform: uppercase;
  font-weight: 700;
}
.summary-grid strong {
  font-size: 28px;
  line-height: 1;
}
.summary-grid em {
  font-size: 12px;
  font-style: normal;
}
section {
  padding: 18px 0 24px;
  border-top: 1px solid var(--line);
}
.section-heading {
  display: flex;
  justify-content: space-between;
  gap: 20px;
  align-items: baseline;
  margin-bottom: 10px;
}
.section-heading p {
  margin: 0;
  font-size: 13px;
  text-align: right;
}
.secondary-heading {
  margin-top: 18px;
}
table {
  width: 100%;
  border-collapse: collapse;
  background: var(--panel);
  font-size: 13px;
}
th, td {
  border-bottom: 1px solid var(--line);
  padding: 8px 9px;
  text-align: left;
  vertical-align: top;
}
thead th {
  color: var(--green);
  font-size: 12px;
  text-transform: uppercase;
  letter-spacing: 0;
  background: var(--field);
}
.visual-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 14px;
}
figure {
  margin: 0;
  background: var(--panel);
  border: 1px solid var(--line);
  display: grid;
  grid-template-rows: minmax(230px, 360px) auto;
}
figure img {
  width: 100%;
  height: 100%;
  object-fit: contain;
  background: #f4f7f4;
  display: block;
}
figcaption {
  border-top: 1px solid var(--line);
  padding: 9px 10px;
  display: grid;
  gap: 3px;
  font-size: 13px;
}
.missing {
  min-height: 230px;
  display: grid;
  place-items: center;
  color: var(--muted);
  background: var(--field);
}
a {
  color: var(--blue);
  text-decoration-thickness: 1px;
  text-underline-offset: 2px;
}
@media (max-width: 920px) {
  .dashboard-header,
  .section-heading {
    display: block;
  }
  .section-heading p {
    text-align: left;
    margin-top: 4px;
  }
  .summary-grid {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }
  .visual-grid {
    grid-template-columns: 1fr;
  }
}
@media (max-width: 640px) {
  .dashboard-shell {
    width: min(100vw - 20px, 1180px);
  }
  .summary-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
  table {
    display: block;
    overflow-x: auto;
    white-space: nowrap;
  }
  .status-strip {
    justify-content: flex-start;
    margin-top: 10px;
  }
  h1 {
    font-size: 30px;
  }
}
"""


def _metric_value(metrics: dict[str, dict[str, str]], name: str, decimals: int) -> str:
    row = metrics.get(name)
    if not row:
        return "-"
    value = float(row["value"])
    return f"{value:.{decimals}f}"


def _metric_confidence(metrics: dict[str, dict[str, str]]) -> str:
    rows = [row for row in metrics.values() if row.get("confidence")]
    if not rows:
        return "-"
    return f"{sum(float(row['confidence']) for row in rows) / len(rows):.2f}"


def _note_value(notes: str, key: str) -> str:
    prefix = f"{key}="
    for part in notes.split(";"):
        stripped = part.strip()
        if stripped.startswith(prefix):
            return stripped[len(prefix) :]
    return "-"


def _manifest_row(asset_id: str, asset_type: str, path: str, source_artifact: str, is_versioned: bool, notes: str) -> dict[str, Any]:
    return {
        "asset_id": asset_id,
        "asset_type": asset_type,
        "path": path,
        "source_artifact": source_artifact,
        "is_versioned": str(is_versioned).lower(),
        "notes": notes,
    }


def _suffix_type(path: str | Path) -> str:
    suffix = Path(path).suffix.lstrip(".")
    return suffix or "artifact"


def _rel_path(path: str | Path, base_dir: str | Path) -> str:
    return Path(os.path.relpath(Path(path), start=Path(base_dir))).as_posix()


def _esc(value: Any) -> str:
    return html.escape(str(value), quote=True)
