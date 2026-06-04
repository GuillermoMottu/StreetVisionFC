from __future__ import annotations

import argparse
import csv
import json
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from futbotmx.level3 import LEVEL3_ARTIFACT_SCHEMAS, write_schema_json, write_schema_manifest
from futbotmx.tracking import read_tracks_csv


DEFAULT_SOURCE_DIR = Path("experiments/test_017_level2_closure")
DEFAULT_OUTPUT_DIR = Path("experiments/test_019_level3_data_contract")
DEFAULT_CLIPS = ("video_595", "video_667")


@dataclass(frozen=True)
class Level2Audit:
    clip_id: str
    tracks_columns: str
    metrics_columns: str
    event_fields: str
    metrics_json_sections: str
    observed_frames: int
    track_count: int
    event_count: int
    class_names: str
    team_values: str
    missing_for_level3: str
    limitations: str


def read_csv(path: str | Path) -> list[dict[str, str]]:
    with Path(path).open("r", newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def read_json(path: str | Path) -> Any:
    with Path(path).open("r", encoding="utf-8") as handle:
        return json.load(handle)


def csv_columns(path: str | Path) -> tuple[str, ...]:
    with Path(path).open("r", newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        return tuple(reader.fieldnames or ())


def json_event_fields(events: Any) -> tuple[str, ...]:
    if not isinstance(events, list):
        return ()
    fields: set[str] = set()
    for event in events:
        if isinstance(event, dict):
            fields.update(str(key) for key in event.keys())
    return tuple(sorted(fields))


def missing_level3_inputs(
    tracks_columns: tuple[str, ...],
    metrics_columns: tuple[str, ...],
    event_fields: tuple[str, ...],
    tracks_rows: list[dict[str, Any]],
) -> list[str]:
    missing: list[str] = []
    for field in ("clip_id", "time_sec", "source_track_id", "x_norm", "y_norm", "zone", "calibration_id", "calibration_status"):
        if field not in tracks_columns:
            missing.append(f"tracks:{field}")
    for field in ("confidence", "source"):
        if field not in metrics_columns:
            missing.append(f"metrics:{field}")
    for field in ("event_subtype", "secondary_object_ids", "highlight_score", "source_event_ids", "interaction_edges", "spatial_context", "narrative"):
        if field not in event_fields:
            missing.append(f"events:{field}")
    team_values = {row.get("team", "unknown") for row in tracks_rows}
    if not any(team not in {"", "neutral", "unknown"} for team in team_values):
        missing.append("tracks:non_neutral_team_assignment")
    return missing


def audit_clip(root: Path, clip_id: str) -> Level2Audit:
    clip_dir = root / DEFAULT_SOURCE_DIR / clip_id
    tracks_path = clip_dir / "tracks_level2.csv"
    metrics_csv_path = clip_dir / "level2_metrics.csv"
    metrics_json_path = clip_dir / "level2_metrics.json"
    events_path = clip_dir / "level2_events.json"

    tracks_columns = csv_columns(tracks_path)
    metrics_columns = csv_columns(metrics_csv_path)
    tracks_rows = read_tracks_csv(tracks_path)
    metrics_json = read_json(metrics_json_path)
    events = read_json(events_path)
    event_fields = json_event_fields(events)
    missing = missing_level3_inputs(tracks_columns, metrics_columns, event_fields, tracks_rows)

    class_names = sorted({row.get("class_name", "") for row in tracks_rows if row.get("class_name")})
    team_values = sorted({row.get("team", "unknown") or "unknown" for row in tracks_rows})
    summary = metrics_json.get("summary", {}) if isinstance(metrics_json, dict) else {}
    limitations = metrics_json.get("limitations", []) if isinstance(metrics_json, dict) else []
    return Level2Audit(
        clip_id=clip_id,
        tracks_columns="|".join(tracks_columns),
        metrics_columns="|".join(metrics_columns),
        event_fields="|".join(event_fields),
        metrics_json_sections="|".join(metrics_json.keys()) if isinstance(metrics_json, dict) else "",
        observed_frames=int(summary.get("observed_frames", 0)),
        track_count=len({row.get("track_id", "") for row in tracks_rows if row.get("track_id")}),
        event_count=len(events) if isinstance(events, list) else 0,
        class_names="|".join(class_names),
        team_values="|".join(team_values),
        missing_for_level3="|".join(missing),
        limitations=" | ".join(str(item) for item in limitations),
    )


def write_audit_csv(audits: list[Level2Audit], path: Path) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(asdict(audits[0]).keys()), lineterminator="\n")
        writer.writeheader()
        for audit in audits:
            writer.writerow(asdict(audit))


def write_config(output_dir: Path, clips: tuple[str, ...]) -> None:
    lines = [
        "level3_data_contract:",
        "  rule_version: level3_data_contract_v0.1",
        f"  source_experiment: {DEFAULT_SOURCE_DIR.as_posix()}",
        "  clips:",
    ]
    for clip_id in clips:
        lines.append(f"    - {clip_id}")
    lines.extend(
        [
            "  outputs:",
            "    - level2_audit.csv",
            "    - level3_schema_manifest.csv",
            "    - level3_schema.json",
            "    - summary.md",
            "  contract_notes:",
            "    - level3_tracks_csv_extends_level2_tracks_csv",
            "    - homography_fields_are_declared_but_not_computed_until_activity_2",
            "    - team_assignment_remains_provisional_until_explicitly_resolved",
        ]
    )
    (output_dir / "config.yaml").write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_summary(audits: list[Level2Audit], output_dir: Path) -> None:
    total_events = sum(audit.event_count for audit in audits)
    total_tracks = sum(audit.track_count for audit in audits)
    missing_items = sorted({item for audit in audits for item in audit.missing_for_level3.split("|") if item})
    lines = [
        "# Contrato De Datos Nivel 3",
        "",
        "## Resultado",
        "",
        "- Estado: `definido`.",
        f"- Clips auditados: `{len(audits)}`.",
        f"- Tracks unicos heredados: `{total_tracks}`.",
        f"- Eventos Nivel 2 heredados: `{total_events}`.",
        f"- Esquemas Nivel 3 definidos: `{len(LEVEL3_ARTIFACT_SCHEMAS)}`.",
        "",
        "## Auditoria Nivel 2",
        "",
    ]
    for audit in audits:
        lines.extend(
            [
                f"### {audit.clip_id}",
                "",
                f"- Frames observados: `{audit.observed_frames}`.",
                f"- Tracks unicos: `{audit.track_count}`.",
                f"- Eventos heredados: `{audit.event_count}`.",
                f"- Clases: `{audit.class_names}`.",
                f"- Equipos exportados: `{audit.team_values}`.",
                f"- Faltantes para Nivel 3: `{audit.missing_for_level3}`.",
                "",
            ]
        )

    lines.extend(
        [
            "## Esquemas Definidos",
            "",
            "- `level3_tracks.csv`: conserva coordenadas originales y agrega coordenadas rectificadas/fallback.",
            "- `level3_metrics.csv`: metricas tacticas atomicas con confianza y fuente.",
            "- `level3_metrics.json`: resumen legible para dashboard y README.",
            "- `level3_events.json`: eventos avanzados con contexto espacial, narrativa y fuentes.",
            "- `level3_highlights.csv`: ranking de jugadas con score y razon.",
            "- `level3_narrative.md`: narrativa deportiva generada por reglas.",
            "- `level3_visualization_manifest.csv`: indice de assets visuales ligeros o locales.",
            "",
            "## Campos Faltantes A Resolver En Actividades Siguientes",
            "",
        ]
    )
    for item in missing_items:
        lines.append(f"- `{item}`")
    lines.extend(
        [
            "",
            "## Limitaciones",
            "",
            "- Nivel 2 usa coordenadas en pixeles; Nivel 3 requiere homografia o fallback documentado.",
            "- Las etiquetas de equipo siguen siendo neutrales/unknown en los clips auditados.",
            "- El contrato define campos de interaccion, narrativa y highlight avanzado, pero su calculo empieza en Actividades 3 y 4.",
            "- Actividad 1 no ejecuta inferencia SAM 3 nueva ni genera archivos pesados.",
            "",
            "## Artefactos",
            "",
            "- `config.yaml`",
            "- `level2_audit.csv`",
            "- `level3_schema_manifest.csv`",
            "- `level3_schema.json`",
            "- `summary.md`",
        ]
    )
    (output_dir / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def build_contract(root: Path, output_dir: Path, clips: tuple[str, ...]) -> list[Level2Audit]:
    output_dir.mkdir(parents=True, exist_ok=True)
    audits = [audit_clip(root, clip_id) for clip_id in clips]
    write_audit_csv(audits, output_dir / "level2_audit.csv")
    write_schema_manifest(output_dir / "level3_schema_manifest.csv")
    write_schema_json(output_dir / "level3_schema.json")
    write_config(output_dir, clips)
    write_summary(audits, output_dir)
    return audits


def main() -> int:
    parser = argparse.ArgumentParser(description="Build the FutBotMX Level 3 data contract evidence.")
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--clips", nargs="+", default=list(DEFAULT_CLIPS))
    args = parser.parse_args()

    root = Path(args.repo_root).resolve()
    output_dir = root / args.output_dir
    clips = tuple(args.clips)
    build_contract(root, output_dir, clips)
    print(f"Wrote Level 3 data contract to {output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
