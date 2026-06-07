from __future__ import annotations

import csv
import html
import os
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from futbotmx.config import write_config_snapshot


RULE_VERSION = "activity20_final_report_v0.1"

MANIFEST_FIELDS = ["asset_id", "asset_type", "path", "source_artifact", "is_versioned", "role", "notes"]
LINK_VALIDATION_FIELDS = ["link_id", "label", "path", "absolute_path", "exists", "required", "notes"]
HEAVY_OUTPUT_EXTENSIONS = {
    ".avi",
    ".m4v",
    ".mkv",
    ".mov",
    ".mp4",
    ".npy",
    ".npz",
    ".pdf",
}


@dataclass(frozen=True)
class FinalReportConfig:
    output_dir: str = "experiments/test_038_final_report"
    project_name: str = "FutBotMX"
    report_title: str = "Reporte Final FutBotMX"
    project_readme_md: str = "README.md"
    dashboard_html: str = "experiments/test_035_human_review/dashboard/dashboard.html"
    reel_html: str = "experiments/test_035_human_review/reel/reel_demo.html"
    review_panel_html: str = "experiments/test_035_human_review/human_review_panel.html"
    final_demo_report_html: str = "experiments/final_demo_report/FINAL_DEMO_REPORT.html"
    closure_summary_md: str = "experiments/test_027_level3_closure/LEVEL3_CLOSURE_SUMMARY.md"
    closure_checks_csv: str = "experiments/test_027_level3_closure/closure_checks.csv"
    full_analysis_summary_md: str = "experiments/test_034_full_analysis/summary.md"
    full_analysis_manifest_csv: str = "experiments/test_034_full_analysis/full_analysis_manifest.csv"
    multiclip_comparison_csv: str = "experiments/test_026_level3_multiclip/level3_multiclip_comparison.csv"
    activity18_summary_md: str = "experiments/test_036_activity18_clip_validation/summary.md"
    activity18_comparison_csv: str = "experiments/test_036_activity18_clip_validation/clip_validation_comparison.csv"
    activity18_failure_modes_csv: str = "experiments/test_036_activity18_clip_validation/failure_modes.csv"
    activity19_summary_md: str = "experiments/test_037_activity19_video_overlay/summary.md"
    activity19_segments_csv: str = "experiments/test_037_activity19_video_overlay/video_overlay_segments.csv"
    activity19_contact_sheet_png: str = "experiments/test_037_activity19_video_overlay/video_overlay_contact_sheet.png"
    activity19_render_plan_md: str = "experiments/test_037_activity19_video_overlay/render_overlay_clip_plan.md"
    local_pdf_path: str = "local_outputs/activity20/futbotmx_final_report.pdf"


def build_final_report_package(config: FinalReportConfig, base_config: dict[str, Any] | None = None) -> dict[str, Any]:
    output_dir = Path(config.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    write_config(output_dir / "config.yaml", config, base_config)
    write_pdf_export_plan(output_dir / "pdf_export_plan.md", config)
    render_script = output_dir / "render_final_report_pdf.sh"
    write_pdf_render_script(render_script, config)
    render_script.chmod(0o755)
    context = build_final_report_context(config)
    (output_dir / "final_report.html").write_text(render_final_report_html(context), encoding="utf-8")
    write_csv_rows(output_dir / "link_validation.csv", context["link_validation"], LINK_VALIDATION_FIELDS)
    manifest = final_report_manifest_rows(config, context)
    write_csv_rows(output_dir / "final_report_manifest.csv", manifest, MANIFEST_FIELDS)
    context["manifest"] = manifest
    context["heavy_outputs"] = scan_heavy_outputs(output_dir)
    if context["heavy_outputs"]:
        heavy_list = ", ".join(context["heavy_outputs"])
        raise ValueError(f"Heavy outputs must stay outside Git: {heavy_list}")
    write_summary(output_dir / "summary.md", context)
    return context


def build_final_report_context(config: FinalReportConfig) -> dict[str, Any]:
    closure_checks = read_csv_rows(config.closure_checks_csv)
    multiclip_rows = read_csv_rows(config.multiclip_comparison_csv)
    activity18_rows = read_csv_rows(config.activity18_comparison_csv)
    failure_rows = read_csv_rows(config.activity18_failure_modes_csv)
    overlay_segments = read_csv_rows(config.activity19_segments_csv)
    links = report_links(config)
    link_validation = validate_report_links(links, config.output_dir)
    return {
        "config": config,
        "rule_version": RULE_VERSION,
        "closure_checks": closure_checks,
        "multiclip_rows": multiclip_rows,
        "activity18_rows": activity18_rows,
        "failure_rows": failure_rows,
        "overlay_segments": overlay_segments,
        "links": links,
        "link_validation": link_validation,
        "summary": summarize_report(closure_checks, multiclip_rows, activity18_rows, failure_rows, overlay_segments, link_validation),
    }


def summarize_report(
    closure_checks: list[dict[str, str]],
    multiclip_rows: list[dict[str, str]],
    activity18_rows: list[dict[str, str]],
    failure_rows: list[dict[str, str]],
    overlay_segments: list[dict[str, str]],
    link_validation: list[dict[str, str]],
) -> dict[str, Any]:
    closure_counts = Counter(row.get("status", "unknown") for row in closure_checks)
    outcome_counts = Counter(row.get("outcome_status", "unknown") for row in activity18_rows)
    return {
        "closure_pass": int(closure_counts.get("pass", 0)),
        "closure_fail": sum(count for status, count in closure_counts.items() if status != "pass"),
        "clips": len(multiclip_rows),
        "generated_clips": sum(1 for row in multiclip_rows if row.get("pipeline_status") == "generated"),
        "total_highlights": sum(_int(row.get("highlight_count")) for row in multiclip_rows),
        "top_score": max((_float(row.get("top_highlight_score")) for row in multiclip_rows), default=0.0),
        "validation_clips": len(activity18_rows),
        "validation_success": int(outcome_counts.get("exito", 0)),
        "validation_degraded": int(outcome_counts.get("degradacion", 0)),
        "validation_known_failures": int(outcome_counts.get("fallo_conocido", 0)),
        "failure_modes": len(failure_rows),
        "overlay_segments": len(overlay_segments),
        "overlay_duration_sec": round(sum(_float(row.get("duration_sec")) for row in overlay_segments), 3),
        "overlay_top_score": max((_float(row.get("score")) for row in overlay_segments), default=0.0),
        "links": len(link_validation),
        "missing_links": sum(1 for row in link_validation if row.get("exists") != "true"),
    }


def report_links(config: FinalReportConfig) -> list[dict[str, Any]]:
    output_dir = Path(config.output_dir)
    return [
        _link("project_readme", "README principal", config.project_readme_md, True, "Entrada del proyecto y regla principal."),
        _link("final_demo_report", "Reporte ejecutivo Nivel 3", config.final_demo_report_html, True, "Reporte HTML previo para evaluadores."),
        _link("dashboard", "Dashboard revisado", config.dashboard_html, True, "Dashboard local con revision humana."),
        _link("reel", "Reel demo revisado", config.reel_html, True, "Reel HTML con segmentos destacados."),
        _link("review_panel", "Panel de revision humana", config.review_panel_html, True, "Panel local para editar estados de highlights."),
        _link("closure_summary", "Cierre Nivel 3", config.closure_summary_md, True, "Resumen de cierre tecnico."),
        _link("closure_checks", "Checks de cierre", config.closure_checks_csv, True, "Gate tecnico Nivel 3."),
        _link("full_analysis_summary", "Resumen analisis completo", config.full_analysis_summary_md, True, "Resumen del orquestador completo local."),
        _link("full_analysis_manifest", "Manifest analisis completo", config.full_analysis_manifest_csv, True, "Manifest del pipeline completo."),
        _link("multiclip_comparison", "Comparacion multi-clip", config.multiclip_comparison_csv, True, "Metricas comparadas de clips Nivel 3."),
        _link("activity18_summary", "Resumen actividad 18", config.activity18_summary_md, True, "Validacion ligera de clips."),
        _link("activity18_comparison", "Comparacion actividad 18", config.activity18_comparison_csv, True, "Estados exito/degradacion/fallo."),
        _link("activity18_failures", "Fallos actividad 18", config.activity18_failure_modes_csv, True, "Modos de fallo documentados."),
        _link("activity19_summary", "Resumen actividad 19", config.activity19_summary_md, True, "Overlay corto local."),
        _link("activity19_segments", "Segmentos overlay", config.activity19_segments_csv, True, "Timeline reproducible para MP4 local."),
        _link("activity19_contact_sheet", "Contact sheet overlay", config.activity19_contact_sheet_png, True, "Evidencia visual ligera del overlay."),
        _link("activity19_render_plan", "Plan render overlay", config.activity19_render_plan_md, True, "Render MP4 local fuera de Git."),
        _link("pdf_export_plan", "Plan PDF local", output_dir / "pdf_export_plan.md", True, "Instrucciones para PDF local no versionado."),
        _link("pdf_render_script", "Script PDF local", output_dir / "render_final_report_pdf.sh", True, "Ayuda local para imprimir PDF fuera de Git."),
    ]


def validate_report_links(links: list[dict[str, Any]], output_dir: str | Path) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for item in links:
        target = Path(item["path"])
        rows.append(
            {
                "link_id": str(item["link_id"]),
                "label": str(item["label"]),
                "path": _rel_path(target, output_dir),
                "absolute_path": target.resolve().as_posix(),
                "exists": str(target.exists()).lower(),
                "required": str(bool(item.get("required", True))).lower(),
                "notes": str(item.get("notes", "")),
            }
        )
    return rows


def render_final_report_html(context: dict[str, Any]) -> str:
    config: FinalReportConfig = context["config"]
    return "\n".join(
        [
            "<!doctype html>",
            '<html lang="es">',
            "<head>",
            '<meta charset="utf-8">',
            '<meta name="viewport" content="width=device-width, initial-scale=1">',
            f"<title>{_esc(config.report_title)}</title>",
            f"<style>{_report_css()}</style>",
            "</head>",
            "<body>",
            "<main>",
            _cover_html(context),
            _quick_links_html(context),
            _summary_cards_html(context),
            _mission_html(),
            _metric_tables_html(context),
            _overlay_html(context),
            _evidence_table_html(context),
            _pdf_policy_html(context),
            "</main>",
            "</body>",
            "</html>",
        ]
    ) + "\n"


def write_config(path: Path, config: FinalReportConfig, base_config: dict[str, Any] | None) -> None:
    snapshot = dict(base_config or {})
    snapshot["final_report"] = {
        "rule_version": RULE_VERSION,
        **asdict(config),
        "outputs": [
            "config.yaml",
            "final_report.html",
            "summary.md",
            "link_validation.csv",
            "final_report_manifest.csv",
            "pdf_export_plan.md",
            "render_final_report_pdf.sh",
        ],
    }
    write_config_snapshot(snapshot, path)


def write_summary(path: str | Path, context: dict[str, Any]) -> None:
    config: FinalReportConfig = context["config"]
    summary = context["summary"]
    lines = [
        "# Actividad 20 - Exportacion A Reporte PDF/HTML",
        "",
        "## Resultado",
        "",
        "- Estado: `generado`.",
        f"- Regla: `{RULE_VERSION}`.",
        "- HTML imprimible: `final_report.html`.",
        f"- Links verificados: `{summary['links']}`.",
        f"- Links faltantes: `{summary['missing_links']}`.",
        f"- Archivos pesados duplicados en el paquete: `{len(context.get('heavy_outputs', []))}`.",
        f"- PDF local esperado: `{config.local_pdf_path}`.",
        "- PDF no generado ni versionado por defecto.",
        "",
        "## Metricas",
        "",
        f"- Checks cierre Nivel 3 pass: `{summary['closure_pass']}`.",
        f"- Checks cierre Nivel 3 fail: `{summary['closure_fail']}`.",
        f"- Clips Nivel 3 generados: `{summary['generated_clips']}` de `{summary['clips']}`.",
        f"- Highlights comparados: `{summary['total_highlights']}`.",
        f"- Clips validados actividad 18: `{summary['validation_clips']}`.",
        f"- Segmentos overlay actividad 19: `{summary['overlay_segments']}`.",
        "",
        "## Artefactos",
        "",
        "- `config.yaml`",
        "- `final_report.html`",
        "- `summary.md`",
        "- `link_validation.csv`",
        "- `final_report_manifest.csv`",
        "- `pdf_export_plan.md`",
        "- `render_final_report_pdf.sh`",
        "",
        "## Politica PDF",
        "",
        "- El PDF se genera solo localmente bajo `local_outputs/`.",
        "- `local_outputs/` esta fuera de Git.",
        "- El reporte HTML enlaza evidencias existentes y no copia videos, checkpoints, frames masivos ni mascaras.",
    ]
    Path(path).write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_pdf_export_plan(path: str | Path, config: FinalReportConfig) -> None:
    lines = [
        "# Plan PDF Local - Reporte Final",
        "",
        "El PDF es una salida local opcional y no se versiona. El artefacto versionado es `final_report.html`.",
        "",
        "## Salida local esperada",
        "",
        f"- `{config.local_pdf_path}`",
        "",
        "## Opcion recomendada",
        "",
        "```bash",
        f"cd {config.output_dir}",
        "bash render_final_report_pdf.sh",
        "```",
        "",
        "## Alternativa manual",
        "",
        "Abrir `final_report.html` en un navegador local y usar imprimir/guardar como PDF.",
        "",
        "## Politica",
        "",
        "- No subir PDFs a Git.",
        "- No copiar videos, checkpoints, frames masivos ni mascaras al paquete del reporte.",
        "- Mantener los links relativos hacia la evidencia versionada.",
    ]
    Path(path).write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_pdf_render_script(path: str | Path, config: FinalReportConfig) -> None:
    local_pdf = _rel_path(config.local_pdf_path, config.output_dir)
    local_pdf_dir = Path(local_pdf).parent.as_posix()
    lines = [
        "#!/usr/bin/env bash",
        "set -euo pipefail",
        "",
        "BROWSER=\"${BROWSER:-}\"",
        "if [ -z \"$BROWSER\" ]; then",
        "  if command -v chromium >/dev/null 2>&1; then",
        "    BROWSER=\"chromium\"",
        "  elif command -v chromium-browser >/dev/null 2>&1; then",
        "    BROWSER=\"chromium-browser\"",
        "  elif command -v google-chrome >/dev/null 2>&1; then",
        "    BROWSER=\"google-chrome\"",
        "  else",
        "    echo \"No se encontro chromium/chromium-browser/google-chrome en PATH\" >&2",
        "    exit 1",
        "  fi",
        "fi",
        "",
        f"mkdir -p \"{local_pdf_dir}\"",
        f"\"$BROWSER\" --headless --disable-gpu \"--print-to-pdf={local_pdf}\" final_report.html",
        f"echo \"PDF local escrito en {local_pdf}\"",
    ]
    Path(path).write_text("\n".join(lines) + "\n", encoding="utf-8")


def final_report_manifest_rows(config: FinalReportConfig, context: dict[str, Any]) -> list[dict[str, Any]]:
    output_dir = Path(config.output_dir)
    rows = [
        _manifest_row("config", "yaml", "config.yaml", "configs/default.yaml", True, "configuration", "Configuration snapshot."),
        _manifest_row("final_report", "html", "final_report.html", "|".join(str(link["path"]) for link in context["links"]), True, "report", "Printable final report."),
        _manifest_row("summary", "md", "summary.md", "final_report.html", True, "summary", "Activity 20 package summary."),
        _manifest_row("link_validation", "csv", "link_validation.csv", "final_report.html", True, "validation", "All report links checked for existence."),
        _manifest_row("final_report_manifest", "csv", "final_report_manifest.csv", "final_report.html", True, "manifest", "Report package manifest."),
        _manifest_row("pdf_export_plan", "md", "pdf_export_plan.md", "final_report.html", True, "pdf_plan", "Local PDF export notes."),
        _manifest_row("pdf_render_script", "sh", "render_final_report_pdf.sh", "pdf_export_plan.md", True, "pdf_helper", "Optional local PDF helper."),
        _manifest_row("local_pdf", "pdf", _rel_path(config.local_pdf_path, output_dir), "render_final_report_pdf.sh", False, "local_output", "Optional PDF outside Git."),
    ]
    generated_links = {"pdf_export_plan", "pdf_render_script"}
    for link in context["links"]:
        if str(link["link_id"]) in generated_links:
            continue
        path = Path(link["path"])
        rows.append(
            _manifest_row(
                str(link["link_id"]),
                path.suffix.lstrip(".") or "artifact",
                _rel_path(path, output_dir),
                str(link["path"]),
                True,
                "linked_evidence",
                str(link.get("notes", "")),
            )
        )
    return rows


def scan_heavy_outputs(output_dir: str | Path) -> list[str]:
    base = Path(output_dir)
    if not base.exists():
        return []
    heavy: list[str] = []
    for path in base.rglob("*"):
        if path.is_file() and path.suffix.lower() in HEAVY_OUTPUT_EXTENSIONS:
            heavy.append(path.relative_to(base).as_posix())
    return sorted(heavy)


def read_csv_rows(path: str | Path) -> list[dict[str, str]]:
    with Path(path).open("r", newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def write_csv_rows(path: str | Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows([{field: row.get(field, "") for field in fieldnames} for row in rows])


def config_to_dict(config: FinalReportConfig) -> dict[str, Any]:
    return asdict(config)


def _cover_html(context: dict[str, Any]) -> str:
    config: FinalReportConfig = context["config"]
    summary = context["summary"]
    return f"""
<header class="cover">
  <p>{_esc(config.project_name)} Nivel 3</p>
  <h1>{_esc(config.report_title)}</h1>
  <span>Entrega local reproducible | regla {_esc(context['rule_version'])}</span>
  <dl>
    <div><dt>Checks pass</dt><dd>{_esc(summary["closure_pass"])}</dd></div>
    <div><dt>Clips Nivel 3</dt><dd>{_esc(summary["generated_clips"])}/{_esc(summary["clips"])}</dd></div>
    <div><dt>Links OK</dt><dd>{_esc(summary["links"] - summary["missing_links"])}/{_esc(summary["links"])}</dd></div>
  </dl>
</header>"""


def _quick_links_html(context: dict[str, Any]) -> str:
    config: FinalReportConfig = context["config"]
    labels = {
        "dashboard",
        "reel",
        "review_panel",
        "activity19_contact_sheet",
        "pdf_export_plan",
    }
    links = [
        link
        for link in context["links"]
        if link["link_id"] in labels
    ]
    anchors = "".join(
        f'<a href="{_esc(_rel_path(link["path"], config.output_dir))}">{_esc(link["label"])}</a>'
        for link in links
    )
    return f'<nav class="quick-links" aria-label="Evidencia principal">{anchors}</nav>'


def _summary_cards_html(context: dict[str, Any]) -> str:
    summary = context["summary"]
    cards = [
        ("Highlights", summary["total_highlights"], "comparados multi-clip"),
        ("Score top", f"{summary['top_score']:.1f}", "ranking Nivel 3"),
        ("Clips validados", summary["validation_clips"], "actividad 18"),
        ("Fallo conocido", summary["validation_known_failures"], "caso diagnostico"),
        ("Overlay", f"{summary['overlay_segments']} seg.", f"{summary['overlay_duration_sec']:.1f}s sugeridos"),
        ("Links faltantes", summary["missing_links"], "validacion HTML"),
    ]
    items = "".join(
        f"<li><span>{_esc(label)}</span><strong>{_esc(value)}</strong><em>{_esc(note)}</em></li>"
        for label, value, note in cards
    )
    return f'<ul class="summary-grid" aria-label="Resumen del reporte">{items}</ul>'


def _mission_html() -> str:
    return """
<section class="text-band">
  <h2>Resumen</h2>
  <p>Este reporte consolida la entrega local de FutBotMX despues del cierre Nivel 3: pipeline reproducible, dashboard, reel, revision humana ligera, validacion multi-clip, overlay corto y evidencia enlazada.</p>
  <p>El alcance se mantiene conservador: analisis aproximado de futbol robotico, sin arbitraje oficial, sin SaaS, sin streaming en tiempo real y sin versionar archivos pesados.</p>
</section>"""


def _metric_tables_html(context: dict[str, Any]) -> str:
    return "\n".join(
        [
            '<section class="table-band">',
            '<div class="section-heading"><h2>Metricas principales</h2><p>Fuentes CSV versionadas.</p></div>',
            _multiclip_table_html(context["multiclip_rows"]),
            _activity18_table_html(context["activity18_rows"]),
            "</section>",
        ]
    )


def _multiclip_table_html(rows: list[dict[str, str]]) -> str:
    body = "\n".join(
        "<tr>"
        f"<th>{_esc(row.get('clip_id', ''))}</th>"
        f"<td>{_esc(row.get('role', ''))}</td>"
        f"<td>{_esc(row.get('pipeline_status', ''))}</td>"
        f"<td>{_esc(row.get('highlight_count', ''))}</td>"
        f"<td>{_float(row.get('top_highlight_score')):.1f}</td>"
        f"<td>{_esc(row.get('interaction_samples', ''))}</td>"
        f"<td>{_esc(row.get('spatial_status', ''))} ({_float(row.get('spatial_confidence')):.2f})</td>"
        "</tr>"
        for row in rows
    )
    return f"""
<h3>Comparacion multi-clip</h3>
<table>
  <thead><tr><th>Clip</th><th>Rol</th><th>Pipeline</th><th>Highlights</th><th>Score top</th><th>Interacciones</th><th>Homografia</th></tr></thead>
  <tbody>{body}</tbody>
</table>"""


def _activity18_table_html(rows: list[dict[str, str]]) -> str:
    body = "\n".join(
        "<tr>"
        f"<th>{_esc(row.get('clip_id', ''))}</th>"
        f"<td>{_esc(row.get('outcome_status', ''))}</td>"
        f"<td>{_esc(row.get('pipeline_scope', ''))}</td>"
        f"<td>{_esc(row.get('homography_status', ''))} ({_float(row.get('homography_confidence')):.2f})</td>"
        f"<td>{_esc(row.get('ball_status', ''))}</td>"
        f"<td>{_esc(row.get('highlight_status', ''))}</td>"
        f"<td>{_esc(row.get('limitation_flags', ''))}</td>"
        "</tr>"
        for row in rows
    )
    return f"""
<h3>Validacion actividad 18</h3>
<table>
  <thead><tr><th>Clip</th><th>Resultado</th><th>Alcance</th><th>Homografia</th><th>Balon</th><th>Highlights</th><th>Limitaciones</th></tr></thead>
  <tbody>{body}</tbody>
</table>"""


def _overlay_html(context: dict[str, Any]) -> str:
    config: FinalReportConfig = context["config"]
    rows = "\n".join(
        "<tr>"
        f"<th>{_esc(row.get('segment_id', ''))}</th>"
        f"<td>{_esc(row.get('clip_id', ''))}</td>"
        f"<td>{_esc(row.get('frame_start', ''))}-{_esc(row.get('frame_end', ''))}</td>"
        f"<td>{_float(row.get('score')):.1f}</td>"
        f"<td>{_float(row.get('confidence')):.2f}</td>"
        f"<td>{_esc(row.get('event_label', ''))}</td>"
        "</tr>"
        for row in context["overlay_segments"]
    )
    contact_sheet = _rel_path(config.activity19_contact_sheet_png, config.output_dir)
    return f"""
<section class="visual-band">
  <div class="section-heading">
    <h2>Evidencia visual final</h2>
    <p>Overlay corto local documentado en actividad 19.</p>
  </div>
  <figure>
    <a href="{_esc(contact_sheet)}"><img src="{_esc(contact_sheet)}" alt="Contact sheet overlay actividad 19"></a>
    <figcaption>Contact sheet del overlay corto. El MP4 se renderiza localmente y queda fuera de Git.</figcaption>
  </figure>
  <table>
    <thead><tr><th>Segmento</th><th>Clip</th><th>Frames</th><th>Score</th><th>Conf.</th><th>Etiqueta</th></tr></thead>
    <tbody>{rows}</tbody>
  </table>
</section>"""


def _evidence_table_html(context: dict[str, Any]) -> str:
    validation_by_id = {row["link_id"]: row for row in context["link_validation"]}
    config: FinalReportConfig = context["config"]
    rows = "\n".join(
        "<tr>"
        f"<th>{_esc(link['label'])}</th>"
        f'<td><a href="{_esc(_rel_path(link["path"], config.output_dir))}">{_esc(_rel_path(link["path"], config.output_dir))}</a></td>'
        f"<td>{_esc(validation_by_id[str(link['link_id'])]['exists'])}</td>"
        f"<td>{_esc(link.get('notes', ''))}</td>"
        "</tr>"
        for link in context["links"]
    )
    return f"""
<section class="table-band">
  <div class="section-heading">
    <h2>Evidencias enlazadas</h2>
    <p>Todos los links son relativos al HTML final.</p>
  </div>
  <table>
    <thead><tr><th>Evidencia</th><th>Ruta</th><th>Existe</th><th>Uso</th></tr></thead>
    <tbody>{rows}</tbody>
  </table>
</section>"""


def _pdf_policy_html(context: dict[str, Any]) -> str:
    config: FinalReportConfig = context["config"]
    return f"""
<section class="text-band policy">
  <h2>PDF local</h2>
  <p>El PDF es opcional y se genera fuera del repositorio en <code>{_esc(config.local_pdf_path)}</code>. El paquete versionado conserva HTML, CSV, Markdown, configuracion y scripts ligeros.</p>
  <p>No se copian videos, checkpoints, frames masivos, mascaras ni renders pesados. El reporte enlaza la evidencia existente para mantener la entrega reproducible y liviana.</p>
</section>"""


def _report_css() -> str:
    return """
:root {
  --ink: #18201c;
  --muted: #5c675f;
  --line: #cad5ce;
  --paper: #fbfcfa;
  --panel: #ffffff;
  --field: #eaf3ec;
  --green: #2e6a4f;
  --blue: #315f9b;
  --amber: #9a6a24;
  --red: #9b4444;
}
* { box-sizing: border-box; }
@page { size: A4; margin: 14mm; }
body {
  margin: 0;
  background: var(--paper);
  color: var(--ink);
  font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
}
main {
  width: min(1120px, calc(100vw - 32px));
  margin: 0 auto;
  padding: 22px 0 40px;
}
.cover {
  min-height: 58vh;
  display: grid;
  align-content: center;
  border-bottom: 2px solid var(--line);
  padding: 18px 0 24px;
}
.cover p {
  margin: 0 0 8px;
  color: var(--green);
  font-size: 13px;
  font-weight: 800;
  text-transform: uppercase;
}
h1 {
  margin: 0 0 10px;
  font-size: 46px;
  line-height: 1.03;
  letter-spacing: 0;
}
h2 {
  margin: 0 0 9px;
  font-size: 22px;
  letter-spacing: 0;
}
h3 {
  margin: 18px 0 8px;
  font-size: 16px;
  color: var(--green);
  letter-spacing: 0;
}
.cover span,
p,
li,
td,
figcaption,
.summary-grid em,
.section-heading p {
  color: var(--muted);
}
.cover dl {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
  margin: 28px 0 0;
}
.cover dl div,
.summary-grid li {
  border-left: 4px solid var(--green);
  background: var(--panel);
  padding: 13px;
}
.cover dt,
.summary-grid span {
  color: var(--muted);
  font-size: 12px;
  font-weight: 800;
  text-transform: uppercase;
}
.cover dd {
  margin: 7px 0 0;
  font-size: 28px;
  font-weight: 800;
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
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: 10px;
  padding: 16px 0;
  margin: 0;
  list-style: none;
}
.summary-grid li {
  min-height: 92px;
  display: grid;
  align-content: space-between;
}
.summary-grid li:nth-child(2n) { border-left-color: var(--blue); }
.summary-grid li:nth-child(3n) { border-left-color: var(--amber); }
.summary-grid li:nth-child(6n) { border-left-color: var(--red); }
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
figure {
  margin: 0 0 14px;
  background: var(--panel);
  border: 1px solid var(--line);
}
img {
  width: 100%;
  max-height: 520px;
  object-fit: contain;
  display: block;
  background: var(--field);
}
figcaption {
  border-top: 1px solid var(--line);
  padding: 8px;
  font-size: 13px;
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
code {
  color: var(--green);
}
.policy {
  border-bottom: 2px solid var(--line);
}
@media (max-width: 860px) {
  .cover dl {
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
    width: min(100vw - 20px, 1120px);
  }
  h1 {
    font-size: 32px;
  }
}
@media print {
  body {
    background: #ffffff;
  }
  main {
    width: 100%;
    padding: 0;
  }
  .cover {
    min-height: 230mm;
    page-break-after: always;
  }
  a {
    color: #1f4f84;
  }
  section,
  table,
  figure {
    break-inside: avoid;
  }
}
"""


def _link(link_id: str, label: str, path: str | Path, required: bool, notes: str) -> dict[str, Any]:
    return {
        "link_id": link_id,
        "label": label,
        "path": Path(path),
        "required": required,
        "notes": notes,
    }


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


def _esc(value: Any) -> str:
    return html.escape(str(value), quote=True)


def _int(value: Any) -> int:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return 0


def _float(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0
