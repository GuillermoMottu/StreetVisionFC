from __future__ import annotations

import csv
import html
import os
import shutil
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from futbotmx.config import write_config_snapshot
from futbotmx.ui import shared_css, ui_body_attrs


RULE_VERSION = "executive_report_v0.1"
MANIFEST_FIELDS = ["asset_id", "asset_type", "path", "source_artifact", "is_versioned", "role", "notes"]


@dataclass(frozen=True)
class ExecutiveReportConfig:
    output_dir: str = "experiments/final_demo_report"
    dashboard_html: str = "experiments/test_035_human_review/dashboard/dashboard.html"
    reel_html: str = "experiments/test_035_human_review/reel/reel_demo.html"
    review_panel_html: str = "experiments/test_035_human_review/human_review_panel.html"
    closure_summary_md: str = "experiments/test_027_level3_closure/LEVEL3_CLOSURE_SUMMARY.md"
    closure_checks_csv: str = "experiments/test_027_level3_closure/closure_checks.csv"
    multiclip_comparison_csv: str = "experiments/test_026_level3_multiclip/level3_multiclip_comparison.csv"
    narrative_md: str = "experiments/test_034_full_analysis/level3_events/level3_narrative.md"
    storyboard_png: str = "experiments/test_034_full_analysis/level3_visualizations/highlight_storyboard.png"
    interaction_graph_png: str = "experiments/test_034_full_analysis/level3_visualizations/interaction_graph.png"
    reel_contact_sheet_png: str = "experiments/test_035_human_review/reel/reel_contact_sheet.png"


def build_executive_report_package(config: ExecutiveReportConfig, base_config: dict[str, Any] | None = None) -> dict[str, Any]:
    output_dir = Path(config.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    context = build_executive_report_context(config)
    write_config(output_dir / "config.yaml", config, base_config)
    (output_dir / "FINAL_DEMO_REPORT.html").write_text(render_report_html(context), encoding="utf-8")
    write_summary(output_dir / "summary.md", context)
    manifest = report_manifest_rows(config, context)
    write_csv_rows(output_dir / "final_demo_report_manifest.csv", manifest, MANIFEST_FIELDS)
    context["manifest"] = manifest
    return context


def build_executive_report_context(config: ExecutiveReportConfig) -> dict[str, Any]:
    output_dir = Path(config.output_dir)
    closure_checks = read_csv_rows(config.closure_checks_csv)
    multiclip_rows = read_csv_rows(config.multiclip_comparison_csv)
    narrative_text = read_text(config.narrative_md)
    captures = copy_capture_assets(config)
    closure_counts = Counter(row.get("status", "unknown") for row in closure_checks)
    summary = {
        "closure_pass": int(closure_counts.get("pass", 0)),
        "closure_fail": sum(count for status, count in closure_counts.items() if status != "pass"),
        "clips": len(multiclip_rows),
        "generated_clips": sum(1 for row in multiclip_rows if row.get("pipeline_status") == "generated"),
        "total_highlights": sum(_int(row.get("highlight_count")) for row in multiclip_rows),
        "top_score": max((_float(row.get("top_highlight_score")) for row in multiclip_rows), default=0.0),
        "capture_count": sum(1 for item in captures if item["status"] == "copied"),
    }
    source_paths = {
        "dashboard_html": config.dashboard_html,
        "reel_html": config.reel_html,
        "review_panel_html": config.review_panel_html,
        "closure_summary_md": config.closure_summary_md,
        "closure_checks_csv": config.closure_checks_csv,
        "multiclip_comparison_csv": config.multiclip_comparison_csv,
        "narrative_md": config.narrative_md,
    }
    return {
        "config": config,
        "rule_version": RULE_VERSION,
        "output_dir": output_dir,
        "summary": summary,
        "closure_checks": closure_checks,
        "multiclip_rows": multiclip_rows,
        "captures": captures,
        "narrative_example": narrative_example(narrative_text),
        "source_paths": source_paths,
    }


def copy_capture_assets(config: ExecutiveReportConfig) -> list[dict[str, str]]:
    output_dir = Path(config.output_dir)
    assets_dir = output_dir / "assets"
    assets_dir.mkdir(parents=True, exist_ok=True)
    specs = [
        ("storyboard", "Storyboard de highlights", config.storyboard_png, "highlight_storyboard.png"),
        ("interaction_graph", "Grafo de interaccion", config.interaction_graph_png, "interaction_graph.png"),
        ("reel_contact_sheet", "Contact sheet del reel", config.reel_contact_sheet_png, "reel_contact_sheet.png"),
    ]
    rows: list[dict[str, str]] = []
    for asset_id, title, source, filename in specs:
        source_path = Path(source)
        target = assets_dir / filename
        status = "missing"
        if source_path.exists():
            shutil.copyfile(source_path, target)
            status = "copied"
        rows.append(
            {
                "asset_id": asset_id,
                "title": title,
                "source": source,
                "path": f"assets/{filename}",
                "status": status,
            }
        )
    return rows


def render_report_html(context: dict[str, Any]) -> str:
    config: ExecutiveReportConfig = context["config"]
    output_dir = Path(config.output_dir)
    summary = context["summary"]
    return "\n".join(
        [
            "<!doctype html>",
            '<html lang="es">',
            "<head>",
            '<meta charset="utf-8">',
            '<meta name="viewport" content="width=device-width, initial-scale=1">',
            "<title>FutBotMX Reporte Ejecutivo</title>",
            f"<style>{_report_css()}</style>",
            "</head>",
            f'<body {ui_body_attrs("report", "executive-report-page")}>',
            '<main class="fb-shell">',
            _header_html(context),
            _link_strip_html(context, output_dir),
            _summary_html(summary),
            _overview_html(),
            _capture_gallery_html(context),
            _multiclip_table_html(context),
            _narrative_html(context),
            _limitations_html(),
            _evidence_html(context, output_dir),
            "</main>",
            "</body>",
            "</html>",
        ]
    ) + "\n"


def write_summary(path: Path, context: dict[str, Any]) -> None:
    summary = context["summary"]
    lines = [
        "# Resumen Ejecutivo Para Evaluadores",
        "",
        "## Resultado",
        "",
        "- Estado: `generado`.",
        f"- Regla: `{RULE_VERSION}`.",
        f"- Checks de cierre Nivel 3 pass: `{summary['closure_pass']}`.",
        f"- Checks de cierre Nivel 3 fail: `{summary['closure_fail']}`.",
        f"- Clips multi-clip generados: `{summary['generated_clips']}` de `{summary['clips']}`.",
        f"- Highlights comparados: `{summary['total_highlights']}`.",
        f"- Capturas Nivel 3 incluidas: `{summary['capture_count']}`.",
        "",
        "## Lectura",
        "",
        "- `FINAL_DEMO_REPORT.html` es la entrada local para evaluadores.",
        "- El reporte enlaza dashboard, reel, panel de revision, cierre Nivel 3, tabla multi-clip y narrativa.",
        "- Los links son relativos a artefactos versionados y las capturas se copian en `assets/`.",
        "- El lenguaje se mantiene conservador: analisis aproximado, no arbitraje oficial.",
        "",
        "## Artefactos",
        "",
        "- `config.yaml`",
        "- `FINAL_DEMO_REPORT.html`",
        "- `summary.md`",
        "- `final_demo_report_manifest.csv`",
        "- `assets/highlight_storyboard.png`",
        "- `assets/interaction_graph.png`",
        "- `assets/reel_contact_sheet.png`",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_config(path: Path, config: ExecutiveReportConfig, base_config: dict[str, Any] | None) -> None:
    snapshot = dict(base_config or {})
    snapshot["executive_report"] = {
        "rule_version": RULE_VERSION,
        **asdict(config),
        "outputs": [
            "config.yaml",
            "FINAL_DEMO_REPORT.html",
            "summary.md",
            "final_demo_report_manifest.csv",
            "assets/*.png",
        ],
    }
    write_config_snapshot(snapshot, path)


def report_manifest_rows(config: ExecutiveReportConfig, context: dict[str, Any]) -> list[dict[str, Any]]:
    output_dir = Path(config.output_dir)
    rows = [
        _manifest_row("config", "yaml", "config.yaml", "configs/default.yaml", True, "configuration", "Configuration snapshot."),
        _manifest_row("final_demo_report", "html", "FINAL_DEMO_REPORT.html", "|".join(context["source_paths"].values()), True, "report", "Executive local report."),
        _manifest_row("summary", "md", "summary.md", "FINAL_DEMO_REPORT.html", True, "summary", "Report package summary."),
        _manifest_row("manifest", "csv", "final_demo_report_manifest.csv", "FINAL_DEMO_REPORT.html", True, "manifest", "Report asset manifest."),
    ]
    for capture in context["captures"]:
        rows.append(
            _manifest_row(
                capture["asset_id"],
                "png",
                capture["path"],
                capture["source"],
                capture["status"] == "copied",
                "capture",
                capture["title"],
            )
        )
    for asset_id, path in context["source_paths"].items():
        rows.append(
            _manifest_row(
                asset_id,
                Path(path).suffix.lstrip(".") or "artifact",
                _rel_path(path, output_dir),
                path,
                True,
                "linked_evidence",
                "Relative link to versioned evidence.",
            )
        )
    return rows


def narrative_example(text: str) -> list[str]:
    lines = [line.strip() for line in text.splitlines()]
    bullets = [line for line in lines if line.startswith("- Rank ") or line.startswith("- `")]
    return bullets[:3]


def read_csv_rows(path: str | Path) -> list[dict[str, str]]:
    with Path(path).open("r", newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def read_text(path: str | Path) -> str:
    return Path(path).read_text(encoding="utf-8")


def write_csv_rows(path: str | Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows([{field: row.get(field, "") for field in fieldnames} for row in rows])


def config_to_dict(config: ExecutiveReportConfig) -> dict[str, Any]:
    return asdict(config)


def _header_html(context: dict[str, Any]) -> str:
    return f"""
<header class="report-header fb-topbar">
  <p class="fb-eyebrow">FutBotMX Nivel 3</p>
  <h1>Reporte ejecutivo para evaluadores</h1>
  <span>Regla {_esc(context['rule_version'])} | demo local reproducible</span>
</header>"""


def _link_strip_html(context: dict[str, Any], output_dir: Path) -> str:
    links = [
        ("Dashboard", context["source_paths"]["dashboard_html"]),
        ("Reel", context["source_paths"]["reel_html"]),
        ("Revision", context["source_paths"]["review_panel_html"]),
        ("Cierre Nivel 3", context["source_paths"]["closure_summary_md"]),
    ]
    anchors = "".join(f'<a href="{_esc(_rel_path(path, output_dir))}">{_esc(label)}</a>' for label, path in links)
    return f'<nav class="quick-links fb-quick-links" aria-label="Evidencia principal">{anchors}</nav>'


def _summary_html(summary: dict[str, Any]) -> str:
    cards = [
        ("Checks pass", summary["closure_pass"], "cierre Nivel 3"),
        ("Clips", f"{summary['generated_clips']}/{summary['clips']}", "multi-clip"),
        ("Highlights", summary["total_highlights"], "comparados"),
        ("Score top", f"{summary['top_score']:.1f}", "ranking"),
        ("Capturas", summary["capture_count"], "Nivel 3"),
    ]
    items = "".join(f"<li><span>{_esc(label)}</span><strong>{_esc(value)}</strong><em>{_esc(note)}</em></li>" for label, value, note in cards)
    return f'<ul class="summary-grid" aria-label="Resumen ejecutivo">{items}</ul>'


def _overview_html() -> str:
    return """
<section class="text-band">
  <h2>Objetivo</h2>
  <p>Presentar una demo avanzada y reproducible de analisis de futbol robotico con SAM 3 como base de segmentacion, tracking, eventos, visualizaciones tacticas, dashboard, reel y revision humana ligera.</p>
  <h2>Resultado</h2>
  <p>El flujo Nivel 3 esta cerrado tecnicamente y produce evidencia versionada: CSV, JSON, Markdown, HTML y PNGs ligeros. Las etapas pesadas siguen documentadas como trabajo de laptop/GPU y los videos/checkpoints quedan fuera de Git.</p>
</section>"""


def _capture_gallery_html(context: dict[str, Any]) -> str:
    figures = []
    for capture in context["captures"]:
        if capture["status"] != "copied":
            figures.append(f'<figure><div class="missing">sin captura</div><figcaption>{_esc(capture["title"])}</figcaption></figure>')
            continue
        figures.append(
            "<figure>"
            f'<a href="{_esc(capture["path"])}"><img src="{_esc(capture["path"])}" alt="{_esc(capture["title"])}"></a>'
            f"<figcaption>{_esc(capture['title'])}</figcaption>"
            "</figure>"
        )
    return f"""
<section class="visual-band">
  <div class="section-heading">
    <h2>Capturas Nivel 3</h2>
    <p>Storyboard, grafo de interaccion y reel revisado.</p>
  </div>
  <div class="visual-grid">{"".join(figures)}</div>
</section>"""


def _multiclip_table_html(context: dict[str, Any]) -> str:
    rows = "\n".join(
        "<tr>"
        f"<th>{_esc(row.get('clip_id', ''))}</th>"
        f"<td>{_esc(row.get('role', ''))}</td>"
        f"<td>{_esc(row.get('pipeline_status', ''))}</td>"
        f"<td>{_esc(row.get('highlight_count', ''))}</td>"
        f"<td>{float(row.get('top_highlight_score') or 0):.1f}</td>"
        f"<td>{_esc(row.get('interaction_samples', ''))}</td>"
        f"<td>{_esc(row.get('spatial_status', ''))} ({float(row.get('spatial_confidence') or 0):.2f})</td>"
        f"<td>{_esc(row.get('human_review_status', ''))}</td>"
        f"<td>{_esc(row.get('limitation_flags', ''))}</td>"
        "</tr>"
        for row in context["multiclip_rows"]
    )
    return f"""
<section class="table-band">
  <div class="section-heading">
    <h2>Tabla multi-clip</h2>
    <p>Comparacion ligera de clips procesados con las mismas reglas Nivel 3.</p>
  </div>
  <table>
    <thead><tr><th>Clip</th><th>Rol</th><th>Pipeline</th><th>Highlights</th><th>Score top</th><th>Interacciones</th><th>Homografia</th><th>Revision</th><th>Limitaciones</th></tr></thead>
    <tbody>{rows}</tbody>
  </table>
</section>"""


def _narrative_html(context: dict[str, Any]) -> str:
    bullets = "".join(f"<li>{_esc(line.lstrip('- '))}</li>" for line in context["narrative_example"])
    return f"""
<section class="text-band">
  <h2>Narrativa ejemplo</h2>
  <ul class="narrative-list">{bullets}</ul>
</section>"""


def _limitations_html() -> str:
    return """
<section class="text-band">
  <h2>Limitaciones</h2>
  <ul>
    <li>El analisis es aproximado y no funciona como arbitraje oficial.</li>
    <li>La homografia, posesion, control espacial, pases e interacciones son heuristicas de demo.</li>
    <li>SAM 3, videos completos, checkpoints, mascaras masivas y MP4 final permanecen fuera de Git.</li>
    <li>Los highlights son candidatos revisables; `human_review.csv` permite descartar falsos positivos sin borrar evidencia original.</li>
  </ul>
</section>"""


def _evidence_html(context: dict[str, Any], output_dir: Path) -> str:
    rows = "\n".join(
        "<tr>"
        f"<td>{_esc(asset_id)}</td>"
        f'<td><a href="{_esc(_rel_path(path, output_dir))}">{_esc(_rel_path(path, output_dir))}</a></td>'
        "<td>versionado</td>"
        "</tr>"
        for asset_id, path in context["source_paths"].items()
    )
    return f"""
<section class="table-band">
  <div class="section-heading">
    <h2>Evidencia enlazada</h2>
    <p>Rutas relativas a artefactos versionados.</p>
  </div>
  <table>
    <thead><tr><th>Fuente</th><th>Ruta</th><th>Estado</th></tr></thead>
    <tbody>{rows}</tbody>
  </table>
</section>"""


def _report_css() -> str:
    return shared_css() + """
:root {
  --ink: #05261d;
  --muted: #52665d;
  --line: #c7e2d1;
  --paper: #f5f9ef;
  --panel: #ffffff;
  --field: #e9ffd8;
  --green: #00d25b;
  --blue: #00c853;
  --amber: #d6ad38;
  --red: #b7f300;
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
  padding: 20px 0 38px;
}
.report-header {
  border: 1px solid var(--line);
  border-bottom: 4px solid var(--red);
  border-radius: 8px;
  padding: 16px;
  background: linear-gradient(135deg, #004b3a, #00c853);
  color: #ffffff;
}
.report-header p {
  margin: 0 0 5px;
  color: #eaffd6;
  font-size: 13px;
  font-weight: 700;
  text-transform: uppercase;
}
h1 {
  margin: 0 0 8px;
  font-size: 40px;
  color: inherit;
  line-height: 1.03;
  letter-spacing: 0;
}
h2 {
  margin: 0 0 8px;
  font-size: 20px;
  letter-spacing: 0;
}
.report-header span,
.section-heading p,
p,
li,
td,
figcaption,
.summary-grid em {
  color: var(--muted);
}
.quick-links {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  padding: 14px 0 0;
}
.quick-links a {
  border: 1px solid var(--line);
  background: var(--panel);
  padding: 8px 10px;
  color: var(--blue);
}
.summary-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(145px, 1fr));
  gap: 10px;
  padding: 16px 0;
  margin: 0;
  list-style: none;
}
.summary-grid li {
  background: var(--panel);
  border-left: 4px solid var(--green);
  padding: 12px;
  min-height: 92px;
  display: grid;
  align-content: space-between;
}
.summary-grid li:nth-child(2n) { border-left-color: var(--blue); }
.summary-grid li:nth-child(3n) { border-left-color: var(--amber); }
.summary-grid li:nth-child(5n) { border-left-color: var(--red); }
.summary-grid span {
  color: var(--muted);
  font-size: 12px;
  font-weight: 700;
  text-transform: uppercase;
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
  border-top: 1px solid var(--line);
  padding: 18px 0 24px;
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
.visual-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
}
figure {
  margin: 0;
  background: var(--panel);
  border: 1px solid var(--line);
  display: grid;
  grid-template-rows: minmax(190px, 310px) auto;
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
  font-size: 13px;
}
.missing {
  display: grid;
  place-items: center;
  min-height: 190px;
  background: var(--field);
  color: var(--muted);
}
table {
  width: 100%;
  border-collapse: collapse;
  background: var(--panel);
  font-size: 13px;
}
th,
td {
  border-bottom: 1px solid var(--line);
  padding: 8px 9px;
  text-align: left;
  vertical-align: top;
}
thead th {
  color: var(--green);
  background: var(--field);
  font-size: 12px;
  text-transform: uppercase;
}
a {
  color: var(--blue);
  text-underline-offset: 2px;
}
.narrative-list {
  background: var(--panel);
  border-left: 4px solid var(--amber);
  margin: 0;
  padding: 12px 16px 12px 28px;
}
@media (max-width: 920px) {
  .visual-grid {
    grid-template-columns: 1fr;
  }
  .section-heading {
    display: block;
  }
  .section-heading p {
    text-align: left;
  }
  table {
    display: block;
    overflow-x: auto;
    white-space: nowrap;
  }
}
@media (max-width: 640px) {
  main {
    width: min(100vw - 20px, 1180px);
  }
  h1 {
    font-size: 30px;
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


def _rel_path(path: str | Path, base_dir: str | Path) -> str:
    return Path(os.path.relpath(Path(path), start=Path(base_dir))).as_posix()


def _float(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _int(value: Any) -> int:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return 0


def _esc(value: Any) -> str:
    return html.escape(str(value), quote=True)
