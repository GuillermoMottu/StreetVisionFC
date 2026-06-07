from __future__ import annotations

import csv
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


RULE_VERSION = "activity18_clip_validation_v0.1"

SELECTION_FIELDS = [
    "clip_id",
    "role",
    "pipeline_scope",
    "camera_condition",
    "light_condition",
    "occlusion_condition",
    "ball_visibility",
    "robot_visibility",
    "field_visibility",
    "selection_reason",
    "source_artifacts",
    "no_heavy_files",
]

COMPARISON_FIELDS = [
    "clip_id",
    "role",
    "pipeline_scope",
    "outcome_status",
    "level3_status",
    "level2_status",
    "homography_status",
    "homography_confidence",
    "ball_status",
    "robot_status",
    "field_status",
    "highlight_status",
    "false_highlight_risk",
    "frames_analyzed",
    "highlight_count",
    "interaction_samples",
    "graph_edges",
    "limitation_flags",
    "evidence_paths",
    "notes",
]

FAILURE_FIELDS = [
    "clip_id",
    "failure_type",
    "severity",
    "status",
    "evidence",
    "recommendation",
]

MANIFEST_FIELDS = ["asset_id", "asset_type", "path", "source_artifact", "is_versioned", "role", "notes"]


@dataclass(frozen=True)
class ClipValidationSpec:
    clip_id: str
    role: str
    pipeline_scope: str
    camera_condition: str
    light_condition: str
    occlusion_condition: str
    ball_visibility: str
    robot_visibility: str
    field_visibility: str
    selection_reason: str
    level3_comparison_csv: str = ""
    level2_summary_md: str = ""
    diagnostic_summary_md: str = ""
    notes: str = ""


def build_activity18_package(output_dir: str | Path, specs: list[ClipValidationSpec], config: dict[str, Any] | None = None) -> dict[str, Any]:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    context = build_validation_context(specs)
    write_csv_rows(output / "clip_selection.csv", context["selection_rows"], SELECTION_FIELDS)
    write_csv_rows(output / "clip_validation_comparison.csv", context["comparison_rows"], COMPARISON_FIELDS)
    write_csv_rows(output / "failure_modes.csv", context["failure_rows"], FAILURE_FIELDS)
    for row in context["comparison_rows"]:
        clip_dir = output / str(row["clip_id"])
        clip_dir.mkdir(parents=True, exist_ok=True)
        write_csv_rows(clip_dir / "clip_validation.csv", [row], COMPARISON_FIELDS)
        clip_failures = [failure for failure in context["failure_rows"] if failure["clip_id"] == row["clip_id"]]
        write_csv_rows(clip_dir / "failure_modes.csv", clip_failures, FAILURE_FIELDS)
        write_clip_summary(clip_dir / "summary.md", row, clip_failures)
    write_summary(output / "summary.md", context["comparison_rows"], context["failure_rows"])
    manifest_rows = manifest_rows_for_output(output)
    write_csv_rows(output / "activity18_manifest.csv", manifest_rows, MANIFEST_FIELDS)
    if config is not None:
        snapshot = dict(config)
        snapshot["activity18_clip_validation"] = {
            "rule_version": RULE_VERSION,
            "output_dir": output.as_posix(),
            "clips": [asdict(spec) for spec in specs],
            "outputs": [row["path"] for row in manifest_rows],
        }
        write_yaml_snapshot(snapshot, output / "config.yaml")
        manifest_rows = manifest_rows_for_output(output)
        write_csv_rows(output / "activity18_manifest.csv", manifest_rows, MANIFEST_FIELDS)
    return context


def build_validation_context(specs: list[ClipValidationSpec]) -> dict[str, list[dict[str, Any]]]:
    selection_rows = [selection_row(spec) for spec in specs]
    comparison_rows = [comparison_row(spec, level3_row_for_spec(spec)) for spec in specs]
    failure_rows: list[dict[str, Any]] = []
    for spec, row in zip(specs, comparison_rows):
        failure_rows.extend(failure_rows_for_clip(spec, row))
    return {
        "selection_rows": selection_rows,
        "comparison_rows": comparison_rows,
        "failure_rows": failure_rows,
    }


def selection_row(spec: ClipValidationSpec) -> dict[str, Any]:
    return {
        "clip_id": spec.clip_id,
        "role": spec.role,
        "pipeline_scope": spec.pipeline_scope,
        "camera_condition": spec.camera_condition,
        "light_condition": spec.light_condition,
        "occlusion_condition": spec.occlusion_condition,
        "ball_visibility": spec.ball_visibility,
        "robot_visibility": spec.robot_visibility,
        "field_visibility": spec.field_visibility,
        "selection_reason": spec.selection_reason,
        "source_artifacts": "|".join(existing_sources(spec)),
        "no_heavy_files": "true",
    }


def comparison_row(spec: ClipValidationSpec, level3_row: dict[str, str]) -> dict[str, Any]:
    has_level3 = bool(level3_row)
    level3_status = level3_row.get("pipeline_status", "missing") if has_level3 else "missing"
    level2_status = "available" if spec.level2_summary_md and Path(spec.level2_summary_md).exists() else "missing"
    if spec.diagnostic_summary_md and Path(spec.diagnostic_summary_md).exists():
        level2_status = "diagnostic"
    homography_status = level3_row.get("spatial_status", "not_evaluated") if has_level3 else "not_evaluated"
    homography_confidence = _float(level3_row.get("spatial_confidence")) if has_level3 else 0.0
    highlight_count = _int(level3_row.get("highlight_count")) if has_level3 else 0
    interaction_samples = _float(level3_row.get("interaction_samples")) if has_level3 else 0.0
    graph_edges = _float(level3_row.get("graph_edges")) if has_level3 else 0.0
    frames = _float(level3_row.get("frames_analyzed")) if has_level3 else 0.0
    limitation_flags = level3_row.get("limitation_flags", "no_level3_outputs" if not has_level3 else "none") or "none"
    outcome = classify_outcome(spec, level3_row)
    highlight_status = classify_highlight_status(has_level3, highlight_count, level3_row.get("human_review_status", ""), limitation_flags)
    return {
        "clip_id": spec.clip_id,
        "role": spec.role,
        "pipeline_scope": spec.pipeline_scope,
        "outcome_status": outcome,
        "level3_status": level3_status,
        "level2_status": level2_status,
        "homography_status": homography_status,
        "homography_confidence": round(homography_confidence, 6),
        "ball_status": classify_visibility(spec.ball_visibility),
        "robot_status": classify_visibility(spec.robot_visibility),
        "field_status": classify_visibility(spec.field_visibility),
        "highlight_status": highlight_status,
        "false_highlight_risk": false_highlight_risk(has_level3, level3_row.get("human_review_status", ""), limitation_flags),
        "frames_analyzed": round(frames, 6),
        "highlight_count": highlight_count,
        "interaction_samples": round(interaction_samples, 6),
        "graph_edges": round(graph_edges, 6),
        "limitation_flags": limitation_flags,
        "evidence_paths": "|".join(existing_sources(spec)),
        "notes": notes_for_clip(spec, outcome, limitation_flags),
    }


def classify_outcome(spec: ClipValidationSpec, level3_row: dict[str, str]) -> str:
    ball = classify_visibility(spec.ball_visibility)
    field = classify_visibility(spec.field_visibility)
    if ball == "fallo" or field == "fallo":
        return "fallo_conocido"
    if not level3_row:
        return "degradacion" if spec.level2_summary_md else "fallo_conocido"
    if level3_row.get("pipeline_status") != "generated":
        return "fallo_conocido"
    confidence = _float(level3_row.get("spatial_confidence"))
    rectified_ratio = _float(level3_row.get("rectified_ratio"))
    highlight_count = _int(level3_row.get("highlight_count"))
    flags = set(str(level3_row.get("limitation_flags", "")).split("|"))
    if "homografia_no_usable" in flags or highlight_count == 0:
        return "fallo_conocido"
    if confidence >= 0.8 and rectified_ratio >= 0.95 and highlight_count >= 3:
        return "exito"
    return "degradacion"


def classify_visibility(value: str) -> str:
    normalized = value.strip().lower()
    if normalized in {"alta", "good", "usable", "visible", "stable"}:
        return "exito"
    if normalized in {"media", "partial", "parcial", "unstable", "provisional", "baja"}:
        return "degradacion"
    if normalized in {"none", "missing", "sin_deteccion", "no_detectado", "fallo"}:
        return "fallo"
    return "degradacion"


def classify_highlight_status(has_level3: bool, highlight_count: int, review_status: str, flags: str) -> str:
    if not has_level3:
        return "not_evaluated"
    if highlight_count == 0:
        return "fallo"
    if review_status == "confiable" and "revision_visual_provisional" not in flags:
        return "exito"
    return "degradacion"


def false_highlight_risk(has_level3: bool, review_status: str, flags: str) -> str:
    if not has_level3:
        return "not_evaluated"
    if review_status == "confiable" and "revision_visual_provisional" not in flags:
        return "bajo"
    if "revision_visual_provisional" in flags or "equipos_neutrales" in flags:
        return "medio"
    return "bajo"


def failure_rows_for_clip(spec: ClipValidationSpec, row: dict[str, Any]) -> list[dict[str, Any]]:
    failures = [
        homography_failure_row(spec, row),
        ball_failure_row(spec, row),
        false_highlight_failure_row(spec, row),
    ]
    return [failure for failure in failures if failure]


def homography_failure_row(spec: ClipValidationSpec, row: dict[str, Any]) -> dict[str, Any] | None:
    status = str(row["homography_status"])
    confidence = _float(row["homography_confidence"])
    if status == "usable" and confidence >= 0.8:
        return None
    if status == "not_evaluated":
        severity = "media" if row["outcome_status"] == "degradacion" else "alta"
        state = "not_evaluated"
        evidence = "Sin salida Level 3 espacial versionada para este clip."
    elif status == "usable":
        severity = "media"
        state = "degradacion"
        evidence = f"Homografia usable pero confianza conservadora: {confidence}."
    else:
        severity = "alta"
        state = "fallo_conocido"
        evidence = f"Homografia no usable o fallback: {status}."
    return {
        "clip_id": spec.clip_id,
        "failure_type": "mala_homografia",
        "severity": severity,
        "status": state,
        "evidence": evidence,
        "recommendation": "Usar calibracion manual o descartar metricas espaciales finas para este clip.",
    }


def ball_failure_row(spec: ClipValidationSpec, row: dict[str, Any]) -> dict[str, Any] | None:
    status = str(row["ball_status"])
    if status == "exito":
        return None
    severity = "alta" if status == "fallo" else "media"
    state = "fallo_conocido" if status == "fallo" else "degradacion"
    return {
        "clip_id": spec.clip_id,
        "failure_type": "perdida_de_balon",
        "severity": severity,
        "status": state,
        "evidence": spec.diagnostic_summary_md or spec.level2_summary_md or "clasificacion manual de visibilidad",
        "recommendation": "Reprocesar SAM 3 con prompts de balon y revisar overlays ligeros antes de usar eventos de posesion.",
    }


def false_highlight_failure_row(spec: ClipValidationSpec, row: dict[str, Any]) -> dict[str, Any] | None:
    risk = str(row["false_highlight_risk"])
    if risk in {"bajo", "not_evaluated"}:
        return None
    return {
        "clip_id": spec.clip_id,
        "failure_type": "falsos_highlights",
        "severity": "media",
        "status": "riesgo",
        "evidence": str(row["limitation_flags"]),
        "recommendation": "Mantener highlights como candidatos y revisar visualmente los top antes de narrarlos.",
    }


def level3_row_for_spec(spec: ClipValidationSpec) -> dict[str, str]:
    if not spec.level3_comparison_csv:
        return {}
    path = Path(spec.level3_comparison_csv)
    if not path.exists():
        return {}
    for row in read_csv_rows(path):
        if row.get("clip_id") == spec.clip_id:
            return row
    return {}


def existing_sources(spec: ClipValidationSpec) -> list[str]:
    paths = [spec.level3_comparison_csv, spec.level2_summary_md, spec.diagnostic_summary_md]
    return [path for path in paths if path and Path(path).exists()]


def notes_for_clip(spec: ClipValidationSpec, outcome: str, flags: str) -> str:
    if outcome == "exito":
        return "Clip procesado con evidencia Level 3 reutilizable; conservar lenguaje de demo tactica aproximada."
    if outcome == "degradacion":
        return f"Clip util para robustez, con degradaciones controladas: {flags}."
    if classify_visibility(spec.ball_visibility) == "fallo":
        return "Fallo conocido por perdida/no deteccion de balon; se conserva como caso diagnostico."
    return "Fallo conocido documentado; no usar para afirmaciones tacticas."


def write_clip_summary(path: str | Path, row: dict[str, Any], failures: list[dict[str, Any]]) -> None:
    lines = [
        f"# Actividad 18 - {row['clip_id']}",
        "",
        "## Resultado",
        "",
        f"- Estado: `{row['outcome_status']}`.",
        f"- Alcance pipeline: `{row['pipeline_scope']}`.",
        f"- Homografia: `{row['homography_status']}` confianza `{row['homography_confidence']}`.",
        f"- Balon: `{row['ball_status']}`.",
        f"- Robots: `{row['robot_status']}`.",
        f"- Campo: `{row['field_status']}`.",
        f"- Highlights: `{row['highlight_status']}` riesgo falso positivo `{row['false_highlight_risk']}`.",
        f"- Limitaciones: `{row['limitation_flags']}`.",
        "",
        "## Evidencia",
        "",
    ]
    for item in str(row["evidence_paths"]).split("|"):
        if item:
            lines.append(f"- `{item}`.")
    lines.extend(["", "## Fallos Documentados", ""])
    if failures:
        for failure in failures:
            lines.append(f"- `{failure['failure_type']}` `{failure['status']}`: {failure['evidence']}")
    else:
        lines.append("- Sin fallo bloqueante nuevo en esta validacion.")
    lines.extend(["", "## Nota", "", str(row["notes"])])
    Path(path).write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_summary(path: str | Path, rows: list[dict[str, Any]], failures: list[dict[str, Any]]) -> None:
    counts: dict[str, int] = {}
    for row in rows:
        counts[str(row["outcome_status"])] = counts.get(str(row["outcome_status"]), 0) + 1
    lines = [
        "# Actividad 18 - Validacion Con Mas Clips",
        "",
        "## Resultado",
        "",
        f"- Regla: `{RULE_VERSION}`.",
        f"- Clips seleccionados: `{len(rows)}`.",
        f"- Clasificacion: `{json.dumps(counts, sort_keys=True)}`.",
        "- No se generaron ni versionaron videos, frames masivos ni renders pesados.",
        "",
        "## Comparacion",
        "",
        "| clip | estado | alcance | homografia | balon | highlights | riesgo falso highlight |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        lines.append(
            f"| `{row['clip_id']}` | `{row['outcome_status']}` | `{row['pipeline_scope']}` | "
            f"`{row['homography_status']} ({row['homography_confidence']})` | `{row['ball_status']}` | "
            f"`{row['highlight_status']}` | `{row['false_highlight_risk']}` |"
        )
    lines.extend(
        [
            "",
            "## Fallos Buscados",
            "",
            "- Mala homografia: registrada cuando no hay Level 3 espacial o la confianza queda baja/provisional.",
            "- Perdida de balon: registrada cuando la seleccion o el diagnostico reportan balon parcial o ausente.",
            "- Falsos highlights: registrada como riesgo cuando la revision visual sigue provisional o los equipos son neutrales.",
            "",
            "## Artefactos",
            "",
            "- `clip_selection.csv`",
            "- `clip_validation_comparison.csv`",
            "- `failure_modes.csv`",
            "- `activity18_manifest.csv`",
            "- `<clip_id>/summary.md`",
            "- `<clip_id>/clip_validation.csv`",
            "- `<clip_id>/failure_modes.csv`",
            "",
            "## Fallos Detectados",
            "",
        ]
    )
    if failures:
        for failure in failures:
            lines.append(f"- `{failure['clip_id']}` `{failure['failure_type']}` `{failure['severity']}`: {failure['recommendation']}")
    else:
        lines.append("- Sin fallos adicionales detectados por la regla.")
    Path(path).write_text("\n".join(lines) + "\n", encoding="utf-8")


def manifest_rows_for_output(output_dir: str | Path) -> list[dict[str, Any]]:
    output = Path(output_dir)
    rows: list[dict[str, Any]] = []
    for path in sorted(output.rglob("*")):
        if not path.is_file() or path.name == "activity18_manifest.csv":
            continue
        rel = path.relative_to(output).as_posix()
        rows.append(
            {
                "asset_id": rel.replace("/", "_").replace(".", "_"),
                "asset_type": path.suffix.lstrip(".") or "file",
                "path": rel,
                "source_artifact": "activity18_clip_validation",
                "is_versioned": "true",
                "role": role_from_path(path),
                "notes": f"size_bytes={path.stat().st_size}",
            }
        )
    return rows


def role_from_path(path: Path) -> str:
    name = path.name
    if name == "config.yaml":
        return "configuration"
    if "manifest" in name:
        return "manifest"
    if "selection" in name:
        return "clip_selection"
    if "failure" in name:
        return "failure_analysis"
    if "comparison" in name or "validation" in name:
        return "comparison"
    if name == "summary.md":
        return "summary"
    return "artifact"


def read_csv_rows(path: str | Path) -> list[dict[str, str]]:
    with Path(path).open("r", newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def write_csv_rows(path: str | Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def write_yaml_snapshot(config: dict[str, Any], path: str | Path) -> None:
    from futbotmx.config import write_config_snapshot

    write_config_snapshot(config, path)


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
