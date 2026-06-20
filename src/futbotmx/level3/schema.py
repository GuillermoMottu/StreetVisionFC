from __future__ import annotations

import csv
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable

from futbotmx.artifact_names import (
    ADVANCED_EVENTS_JSON,
    HIGHLIGHTS_CSV,
    LEGACY_ADVANCED_EVENTS_JSON,
    LEGACY_HIGHLIGHTS_CSV,
    LEGACY_NARRATIVE_MD,
    LEGACY_SPATIAL_TRACKS_CSV,
    LEGACY_TACTICAL_METRICS_CSV,
    LEGACY_TACTICAL_METRICS_JSON,
    LEGACY_VISUALIZATION_MANIFEST_CSV,
    NARRATIVE_MD,
    SPATIAL_TRACKS_CSV,
    TACTICAL_METRICS_CSV,
    TACTICAL_METRICS_JSON,
    VISUALIZATION_MANIFEST_CSV,
)


LEVEL3_TRACKS_FIELDS = (
    "clip_id",
    "frame",
    "time_sec",
    "track_id",
    "source_track_id",
    "class_name",
    "team",
    "x",
    "y",
    "bbox_x1",
    "bbox_y1",
    "bbox_x2",
    "bbox_y2",
    "confidence",
    "x_norm",
    "y_norm",
    "zone",
    "calibration_id",
    "calibration_status",
    "calibration_confidence",
    "track_quality",
    "notes",
)

LEVEL3_METRICS_FIELDS = (
    "clip_id",
    "metric_category",
    "entity_type",
    "entity_id",
    "class_name",
    "team",
    "metric_name",
    "value",
    "unit",
    "frame_start",
    "frame_end",
    "confidence",
    "source",
    "notes",
)

LEVEL3_HIGHLIGHTS_FIELDS = (
    "clip_id",
    "highlight_id",
    "rank",
    "score",
    "event_type",
    "frame_start",
    "frame_end",
    "time_start_sec",
    "time_end_sec",
    "primary_track_id",
    "secondary_track_ids",
    "zone",
    "confidence",
    "reliability",
    "reason",
    "source_event_ids",
)

LEVEL3_VISUALIZATION_MANIFEST_FIELDS = (
    "clip_id",
    "asset_id",
    "asset_type",
    "path",
    "source_artifact",
    "frame_start",
    "frame_end",
    "event_id",
    "is_versioned",
    "notes",
)

LEVEL3_EVENTS_FIELDS = (
    "event_id",
    "event_type",
    "event_subtype",
    "clip_id",
    "frame_start",
    "frame_end",
    "time_start_sec",
    "time_end_sec",
    "team",
    "primary_object_id",
    "secondary_object_ids",
    "ball_id",
    "zone",
    "position_start",
    "position_end",
    "confidence",
    "reliability",
    "highlight_score",
    "source_event_ids",
    "interaction_edges",
    "spatial_context",
    "narrative",
    "rule_version",
    "evidence",
)


@dataclass(frozen=True)
class ArtifactSchema:
    artifact_name: str
    artifact_format: str
    required_fields: tuple[str, ...]
    purpose: str
    producer_stage: str
    consumer_stage: str
    notes: str = ""
    legacy_names: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["required_fields"] = list(self.required_fields)
        return data


TACTICAL_ARTIFACT_SCHEMAS = (
    ArtifactSchema(
        SPATIAL_TRACKS_CSV,
        "csv",
        LEVEL3_TRACKS_FIELDS,
        "Tracks con coordenadas rectificadas/fallback y metadatos de calibracion.",
        "Modelo espacial y mini-mapa",
        "Metricas tacticas, eventos avanzados, mini-mapa, Voronoi y dashboard.",
        legacy_names=(LEGACY_SPATIAL_TRACKS_CSV,),
    ),
    ArtifactSchema(
        TACTICAL_METRICS_CSV,
        "csv",
        LEVEL3_METRICS_FIELDS,
        "Metricas tacticas atomicas y comparables por clip, robot, equipo o evento.",
        "Metricas tacticas avanzadas",
        "Dashboard, comparacion multi-clip y cierre tecnico.",
        legacy_names=(LEGACY_TACTICAL_METRICS_CSV,),
    ),
    ArtifactSchema(
        TACTICAL_METRICS_JSON,
        "json",
        (
            "rule_version",
            "source",
            "summary",
            "spatial_control",
            "interactions",
            "pass_chains",
            "highlights",
            "assumptions",
            "limitations",
        ),
        "Resumen legible de metricas tacticas y limitaciones por clip.",
        "Metricas tacticas avanzadas",
        "Dashboard, README y resumen final.",
        legacy_names=(LEGACY_TACTICAL_METRICS_JSON,),
    ),
    ArtifactSchema(
        ADVANCED_EVENTS_JSON,
        "json",
        LEVEL3_EVENTS_FIELDS,
        "Eventos avanzados: cadenas de pases, highlights, presion e interacciones.",
        "Eventos avanzados",
        "Narrativa, overlays, storyboard, dashboard y reel.",
        legacy_names=(LEGACY_ADVANCED_EVENTS_JSON,),
    ),
    ArtifactSchema(
        HIGHLIGHTS_CSV,
        "csv",
        LEVEL3_HIGHLIGHTS_FIELDS,
        "Ranking de jugadas destacadas con score, confianza y razon.",
        "Eventos avanzados",
        "Storyboard, reel final, dashboard y validacion humana.",
        legacy_names=(LEGACY_HIGHLIGHTS_CSV,),
    ),
    ArtifactSchema(
        NARRATIVE_MD,
        "markdown",
        ("title", "clip_id", "event_sections", "limitations"),
        "Narrativa deportiva generada por reglas, con lenguaje conservador.",
        "Eventos avanzados",
        "Dashboard, reel final y README.",
        "Markdown no usa columnas CSV; los campos representan secciones obligatorias.",
        legacy_names=(LEGACY_NARRATIVE_MD,),
    ),
    ArtifactSchema(
        VISUALIZATION_MANIFEST_CSV,
        "csv",
        LEVEL3_VISUALIZATION_MANIFEST_FIELDS,
        "Indice de PNG/GIF/video local asociado a visualizaciones tacticas.",
        "Actividades 5, 6 y 7",
        "Dashboard, cierre tecnico y control anti-archivos-pesados.",
        legacy_names=(LEGACY_VISUALIZATION_MANIFEST_CSV,),
    ),
)

LEVEL3_ARTIFACT_SCHEMAS = TACTICAL_ARTIFACT_SCHEMAS


def schema_manifest_rows(schemas: Iterable[ArtifactSchema] = TACTICAL_ARTIFACT_SCHEMAS) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for schema in schemas:
        rows.append(
            {
                "artifact_name": schema.artifact_name,
                "artifact_format": schema.artifact_format,
                "required_fields": "|".join(schema.required_fields),
                "purpose": schema.purpose,
                "producer_stage": schema.producer_stage,
                "consumer_stage": schema.consumer_stage,
                "notes": schema.notes,
            }
        )
    return rows


def validate_required_fields(row: dict[str, Any], required_fields: Iterable[str]) -> list[str]:
    return [field for field in required_fields if field not in row]


def schema_for_artifact(artifact_name: str, schemas: Iterable[ArtifactSchema] = TACTICAL_ARTIFACT_SCHEMAS) -> ArtifactSchema:
    for schema in schemas:
        if artifact_name == schema.artifact_name or artifact_name in schema.legacy_names:
            return schema
    raise KeyError(f"Unknown tactical artifact schema: {artifact_name}")


def write_csv_artifact(path: str | Path, artifact_name: str, rows: Iterable[dict[str, Any]]) -> None:
    schema = schema_for_artifact(artifact_name)
    if schema.artifact_format != "csv":
        raise ValueError(f"{artifact_name} is not a CSV artifact")

    fieldnames = list(schema.required_fields)
    normalized_rows: list[dict[str, Any]] = []
    for index, row in enumerate(rows):
        missing = validate_required_fields(row, fieldnames)
        if missing:
            raise ValueError(f"{artifact_name} row {index} missing fields: {', '.join(missing)}")
        normalized_rows.append({field: row.get(field, "") for field in fieldnames})

    with Path(path).open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(normalized_rows)


def read_csv_artifact(path: str | Path) -> list[dict[str, str]]:
    with Path(path).open("r", newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def write_schema_manifest(path: str | Path, schemas: Iterable[ArtifactSchema] = TACTICAL_ARTIFACT_SCHEMAS) -> None:
    rows = schema_manifest_rows(schemas)
    fieldnames = ("artifact_name", "artifact_format", "required_fields", "purpose", "producer_stage", "consumer_stage", "notes")
    with Path(path).open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def write_schema_json(path: str | Path, schemas: Iterable[ArtifactSchema] = TACTICAL_ARTIFACT_SCHEMAS) -> None:
    payload = {
        "rule_version": "tactical_data_contract_v0.2",
        "schemas": [schema.to_dict() for schema in schemas],
    }
    Path(path).write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
