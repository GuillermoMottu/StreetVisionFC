from __future__ import annotations

import csv
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


RULE_VERSION = "level3_multiclip_v0.1"


COMPARISON_FIELDS = [
    "clip_id",
    "role",
    "pipeline_status",
    "spatial_status",
    "spatial_confidence",
    "rows",
    "rectified_rows",
    "rectified_ratio",
    "frames_analyzed",
    "highlight_count",
    "top_highlight_score",
    "mean_highlight_confidence",
    "provisional_highlights",
    "doubtful_highlights",
    "interaction_samples",
    "graph_edges",
    "mean_control_entropy",
    "control_tracks",
    "mean_track_control_percent",
    "human_review_status",
    "limitation_flags",
    "artifact_dir",
    "dashboard_path",
]

HUMAN_REVIEW_FIELDS = [
    "clip_id",
    "highlight_id",
    "rank",
    "frame_start",
    "frame_end",
    "asset_path",
    "confidence",
    "review_status",
    "reviewer",
    "notes",
]


@dataclass(frozen=True)
class ClipMulticlipArtifacts:
    clip_id: str
    role: str
    artifact_dir: str
    spatial_validation_csv: str
    metrics_csv: str
    metrics_json: str
    interaction_edges_csv: str
    highlights_csv: str
    overlay_validation_csv: str
    human_review_csv: str
    dashboard_html: str


def read_csv_rows(path: str | Path) -> list[dict[str, str]]:
    with Path(path).open("r", newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


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


def write_multiclip_manifest(path: str | Path, artifacts: list[ClipMulticlipArtifacts]) -> None:
    fieldnames = list(asdict(artifacts[0]).keys()) if artifacts else list(ClipMulticlipArtifacts.__dataclass_fields__)
    write_csv_rows(path, [asdict(item) for item in artifacts], fieldnames)


def summarize_clip_artifacts(artifacts: ClipMulticlipArtifacts) -> dict[str, Any]:
    spatial_rows = read_csv_rows(artifacts.spatial_validation_csv)
    metric_rows = read_csv_rows(artifacts.metrics_csv)
    metrics_json = read_json(artifacts.metrics_json)
    edge_rows = read_csv_rows(artifacts.interaction_edges_csv)
    highlight_rows = read_csv_rows(artifacts.highlights_csv)
    overlay_rows = read_csv_rows(artifacts.overlay_validation_csv)

    spatial = next((row for row in spatial_rows if row.get("clip_id") == artifacts.clip_id), spatial_rows[0] if spatial_rows else {})
    clip_metrics = {
        str(row["metric_name"]): row
        for row in metric_rows
        if row.get("entity_type") == "clip" and row.get("clip_id") == artifacts.clip_id
    }
    control_rows = [
        row
        for row in metric_rows
        if row.get("metric_name") == "mean_control_percent" and row.get("clip_id") == artifacts.clip_id
    ]
    highlights = [row for row in highlight_rows if row.get("clip_id") == artifacts.clip_id]
    provisional = sum(1 for row in highlights if row.get("reliability") == "provisional")
    doubtful = sum(1 for row in highlights if row.get("reliability") in {"dudoso", "doubtful"})
    top_score = max((_float(row.get("score")) for row in highlights), default=0.0)
    mean_highlight_confidence = _mean(_float(row.get("confidence")) for row in highlights)
    mean_control = _mean(_float(row.get("value")) for row in control_rows)
    rectified_rows = _int(spatial.get("rectified_rows"))
    rows = _int(spatial.get("rows"))
    spatial_status = str(spatial.get("calibration_status", "missing") or "missing")
    spatial_confidence = _float(spatial.get("calibration_confidence"))
    review_rows = build_human_review_rows(artifacts.clip_id, overlay_rows, highlights)
    review_status = aggregate_review_status(review_rows)
    flags = limitation_flags(
        spatial_status=spatial_status,
        spatial_confidence=spatial_confidence,
        highlight_count=len(highlights),
        review_status=review_status,
        graph_edges=len(edge_rows),
        metrics_json=metrics_json,
    )
    return {
        "clip_id": artifacts.clip_id,
        "role": artifacts.role,
        "pipeline_status": "generated" if rows and metric_rows and highlights else "incomplete",
        "spatial_status": spatial_status,
        "spatial_confidence": round(spatial_confidence, 6),
        "rows": rows,
        "rectified_rows": rectified_rows,
        "rectified_ratio": round(rectified_rows / rows, 6) if rows else 0.0,
        "frames_analyzed": _metric_value(clip_metrics, "frames_analyzed"),
        "highlight_count": len(highlights),
        "top_highlight_score": round(top_score, 6),
        "mean_highlight_confidence": round(mean_highlight_confidence, 6),
        "provisional_highlights": provisional,
        "doubtful_highlights": doubtful,
        "interaction_samples": _metric_value(clip_metrics, "interaction_samples"),
        "graph_edges": _metric_value(clip_metrics, "graph_edges"),
        "mean_control_entropy": round(_metric_value(clip_metrics, "mean_control_entropy"), 6),
        "control_tracks": len(control_rows),
        "mean_track_control_percent": round(mean_control, 6),
        "human_review_status": review_status,
        "limitation_flags": "|".join(flags) if flags else "none",
        "artifact_dir": artifacts.artifact_dir,
        "dashboard_path": artifacts.dashboard_html,
        "human_review_rows": review_rows,
    }


def build_human_review_rows(
    clip_id: str,
    overlay_rows: list[dict[str, str]],
    highlight_rows: list[dict[str, str]],
) -> list[dict[str, Any]]:
    highlights_by_id = {str(row.get("highlight_id", "")): row for row in highlight_rows}
    review_rows: list[dict[str, Any]] = []
    for row in overlay_rows:
        highlight = highlights_by_id.get(str(row.get("highlight_id", "")), {})
        confidence = _float(row.get("confidence") or highlight.get("confidence"))
        has_asset = bool(row.get("asset_path")) and row.get("status") == "generated"
        reason = str(highlight.get("reason", ""))
        status = classify_review_status(confidence, has_asset, reason)
        review_rows.append(
            {
                "clip_id": clip_id,
                "highlight_id": row.get("highlight_id", ""),
                "rank": row.get("rank", ""),
                "frame_start": row.get("frame_start", ""),
                "frame_end": row.get("frame_end", ""),
                "asset_path": row.get("asset_path", ""),
                "confidence": round(confidence, 6),
                "review_status": status,
                "reviewer": "rule_based_human_check_proxy",
                "notes": review_notes(status, confidence, has_asset, reason),
            }
        )
    if not review_rows:
        return [
            {
                "clip_id": clip_id,
                "highlight_id": "",
                "rank": "",
                "frame_start": "",
                "frame_end": "",
                "asset_path": "",
                "confidence": 0.0,
                "review_status": "descartado",
                "reviewer": "rule_based_human_check_proxy",
                "notes": "Sin overlay ligero para revisar; se descarta como evidencia visual top.",
            }
        ]
    return review_rows


def classify_review_status(confidence: float, has_asset: bool, reason: str) -> str:
    if not has_asset or confidence < 0.45:
        return "descartado"
    if confidence >= 0.86 and "respaldo_level2" in reason:
        return "confiable"
    return "provisional"


def review_notes(status: str, confidence: float, has_asset: bool, reason: str) -> str:
    if status == "descartado":
        return "Evidencia insuficiente: falta overlay ligero o la confianza queda por debajo del umbral conservador."
    if status == "confiable":
        return "Overlay generado, confianza alta y respaldo Nivel 2; aun se trata como highlight tactico aproximado."
    if "presion_o_disputa" in reason:
        return "Overlay generado con presion/disputa candidata; mantener como provisional por homografia aproximada."
    return "Overlay generado; provisional por falta de equipos confiables y validacion humana frame a frame."


def aggregate_review_status(rows: list[dict[str, Any]]) -> str:
    statuses = {str(row.get("review_status", "")) for row in rows}
    if "descartado" in statuses and len(statuses) == 1:
        return "descartado"
    if statuses == {"confiable"}:
        return "confiable"
    return "provisional"


def limitation_flags(
    spatial_status: str,
    spatial_confidence: float,
    highlight_count: int,
    review_status: str,
    graph_edges: int,
    metrics_json: Any,
) -> list[str]:
    flags: list[str] = []
    if spatial_status != "usable":
        flags.append("homografia_no_usable")
    elif spatial_confidence < 0.75:
        flags.append("homografia_provisional")
    if highlight_count < 3:
        flags.append("pocos_highlights")
    if review_status != "confiable":
        flags.append("revision_visual_provisional")
    if graph_edges == 0:
        flags.append("sin_aristas_interaccion")
    if isinstance(metrics_json, dict):
        tracks = metrics_json.get("spatial_control", {}).get("aggregate_by_track", [])
        if tracks and all(str(row.get("team", "")).lower() in {"", "neutral", "unknown"} for row in tracks):
            flags.append("equipos_neutrales")
    return flags


def write_clip_human_review(path: str | Path, rows: list[dict[str, Any]]) -> None:
    write_csv_rows(path, rows, HUMAN_REVIEW_FIELDS)


def write_multiclip_comparison(path: str | Path, rows: list[dict[str, Any]]) -> None:
    clean_rows = [{field: row.get(field, "") for field in COMPARISON_FIELDS} for row in rows]
    write_csv_rows(path, clean_rows, COMPARISON_FIELDS)


def _metric_value(metrics: dict[str, dict[str, str]], name: str) -> float:
    return _float(metrics.get(name, {}).get("value"))


def _mean(values: Any) -> float:
    items = [float(value) for value in values]
    return sum(items) / len(items) if items else 0.0


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
