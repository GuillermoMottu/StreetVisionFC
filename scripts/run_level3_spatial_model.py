from __future__ import annotations

import argparse
import copy
import csv
import json
from pathlib import Path
import re
import sys
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from futbotmx.config import load_config, write_config_snapshot
from futbotmx.level3 import (
    LEVEL3_SPATIAL_RULE_VERSION,
    ClipCalibration,
    ClipSpatialSpec,
    FieldModel,
    build_calibration_from_tracks,
    draw_minimap_base,
    draw_minimap_tracks,
    rectify_track_rows,
    summarize_rectified_tracks,
    solve_homography,
    write_calibration_json,
    write_level3_tracks,
    write_spatial_validation_csv,
)
from futbotmx.tracking import read_tracks_csv


DEFAULT_SOURCE_DIR = Path("experiments/test_017_level2_closure")
DEFAULT_OUTPUT_DIR = Path("experiments/test_020_level3_spatial_model")
DEFAULT_CLIPS = ("video_595", "video_667")


def clip_specs_from_config(config: dict[str, Any], selected_clips: tuple[str, ...]) -> dict[str, ClipSpatialSpec]:
    specs: dict[str, ClipSpatialSpec] = {}
    closure_clips = config.get("level2_closure", {}).get("clips", [])
    for raw in closure_clips:
        clip_id = str(raw["clip_id"])
        if clip_id not in selected_clips:
            continue
        specs[clip_id] = ClipSpatialSpec(
            clip_id=clip_id,
            width=int(raw["width"]),
            height=int(raw["height"]),
            fps=float(raw["fps"]),
            role=str(raw.get("role", "dense_candidate")),
        )

    multiclip = config.get("level2_multiclip", {}).get("clips", [])
    for raw in multiclip:
        clip_id = str(raw["clip_id"])
        if clip_id in selected_clips and clip_id not in specs:
            specs[clip_id] = ClipSpatialSpec(
                clip_id=clip_id,
                width=int(raw["width"]),
                height=int(raw["height"]),
                fps=float(raw["fps"]),
                role=str(raw.get("role", "candidate")),
            )
    missing = [clip_id for clip_id in selected_clips if clip_id not in specs]
    if missing:
        raise ValueError(f"Missing clip metadata in config for: {', '.join(missing)}")
    return specs


def write_spatial_config(
    config: dict[str, Any],
    output_dir: Path,
    source_dir: Path,
    clips: tuple[str, ...],
    min_field_confidence: float,
    min_field_coverage: float,
    manual_calibration_path: Path | None,
) -> None:
    snapshot = copy.deepcopy(config)
    snapshot["level3_spatial_model"] = {
        "rule_version": LEVEL3_SPATIAL_RULE_VERSION,
        "source_experiment": source_dir.as_posix(),
        "output_dir": output_dir.as_posix(),
        "clips": list(clips),
        "coordinate_system": {
            "origin": "top_left_visible_field",
            "direction": "x_norm left_to_right, y_norm top_to_bottom",
            "units": "normalized_visible_field",
            "zone_axis": "y",
        },
        "calibration": {
            "method": "field_bbox_homography_seed",
            "manual_four_corner_override_supported": True,
            "manual_calibration_input": manual_calibration_path.as_posix() if manual_calibration_path else "",
            "min_field_confidence": min_field_confidence,
            "min_field_coverage": min_field_coverage,
            "fallback": "image_extent_normalization",
        },
        "outputs": [
            "field_calibration.json",
            "level3_tracks.csv",
            "minimap_base.png",
            "minimap_tracks.png",
            "overlay_comparison.csv",
            "spatial_validation.csv",
            "summary.md",
        ],
    }
    write_config_snapshot(snapshot, output_dir / "config.yaml")


def _manual_points(raw_points: list[dict[str, Any]]) -> tuple[tuple[float, float], ...]:
    points: list[tuple[float, float]] = []
    for point in raw_points:
        if "x" in point and "y" in point:
            points.append((float(point["x"]), float(point["y"])))
        elif "x_norm" in point and "y_norm" in point:
            points.append((float(point["x_norm"]), float(point["y_norm"])))
    return tuple(points)


def load_manual_calibrations(path: Path | None, specs: dict[str, ClipSpatialSpec]) -> dict[str, ClipCalibration]:
    if path is None:
        return {}
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    raw_clips = payload.get("clips", {}) if isinstance(payload, dict) else {}
    calibrations: dict[str, ClipCalibration] = {}
    for clip_id, spec in specs.items():
        raw = raw_clips.get(clip_id)
        if not isinstance(raw, dict):
            continue
        image_points = _manual_points(raw.get("image_points", []))
        field_points = _manual_points(raw.get("field_points", []))
        if len(image_points) < 4 or len(field_points) < 4:
            continue
        homography = solve_homography(image_points, field_points)
        calibrations[clip_id] = ClipCalibration(
            clip_id=clip_id,
            calibration_id=str(raw.get("calibration_id", f"{clip_id}_manual_homography_v0.1")),
            method=str(raw.get("method", "manual_four_corner_homography")),
            status="usable",
            confidence=float(raw.get("confidence", 0.7)),
            image_width=spec.width,
            image_height=spec.height,
            image_points=image_points,
            field_points=field_points,
            homography=homography,
            notes=str(raw.get("notes", f"Manual four-corner calibration loaded from {path.as_posix()}.")),
        )
    return calibrations


def write_overlay_comparison_csv(path: Path, source_dir: Path, clips: tuple[str, ...]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for clip_id in clips:
        clip_dir = source_dir / clip_id
        overlays_by_frame: dict[int, Path] = {}
        for overlay in sorted(clip_dir.glob("overlay_*_frame_*.png")):
            match = re.search(r"_frame_(\d+)\.png$", overlay.name)
            if not match:
                continue
            frame = int(match.group(1))
            overlays_by_frame.setdefault(frame, overlay)
        for frame, overlay in list(sorted(overlays_by_frame.items()))[:5]:
            rows.append(
                {
                    "clip_id": clip_id,
                    "frame": frame,
                    "original_overlay": overlay.as_posix(),
                    "minimap_reference": "minimap_tracks.png",
                    "level3_tracks": "level3_tracks.csv",
                    "assessment": "consistent_trace_reference",
                    "notes": "Original overlay is reused from Level 2 closure; Level 3 preserves frame, ID, x/y and adds x_norm/y_norm for the same track rows.",
                }
            )

    fieldnames = ["clip_id", "frame", "original_overlay", "minimap_reference", "level3_tracks", "assessment", "notes"]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    return rows


def write_summary(
    path: Path,
    source_dir: Path,
    clips: tuple[str, ...],
    calibrations: dict[str, ClipCalibration],
    validation_rows: list[dict[str, Any]],
    overlay_rows: list[dict[str, Any]],
) -> None:
    primary_clip = clips[0] if clips else ""
    primary_row = next((row for row in validation_rows if row["clip_id"] == primary_clip), None)
    primary_ok = bool(primary_row and primary_row["calibration_status"] == "usable" and int(primary_row["rectified_rows"]) > 0)
    total_rows = sum(int(row["rows"]) for row in validation_rows)
    total_rectified = sum(int(row["rectified_rows"]) for row in validation_rows)

    lines = [
        "# Rectificacion Espacial Y Mini-Mapa Nivel 3",
        "",
        "## Resultado",
        "",
        f"- Estado: `{'usable' if primary_ok else 'provisional'}`.",
        f"- Regla: `{LEVEL3_SPATIAL_RULE_VERSION}`.",
        f"- Fuente Nivel 2: `{source_dir.as_posix()}`.",
        f"- Clips procesados: `{', '.join(clips)}`.",
        f"- Filas exportadas: `{total_rows}`.",
        f"- Filas rectificadas por homografia: `{total_rectified}`.",
        "",
        "## Modelo De Cancha",
        "",
        "- Coordenadas: `x_norm` y `y_norm` en rango `[0, 1]` sobre la cancha visible aproximada.",
        "- Origen: esquina superior izquierda de la cancha visible calibrada.",
        "- Direccion: `x_norm` crece de izquierda a derecha; `y_norm` crece de arriba hacia abajo.",
        "- Zonas tacticas: `defensive_third`, `middle_third`, `attacking_third` calculadas sobre `y_norm`, conservando la direccion de `zone_axis: y` de Nivel 2.",
        "- Porterias relativas: lineas centradas en `y_norm=0` y `y_norm=1`, con ancho normalizado `0.22`.",
        "",
        "## Calibracion",
        "",
    ]
    for clip_id in clips:
        calibration = calibrations[clip_id]
        lines.extend(
            [
                f"### {clip_id}",
                "",
                f"- Metodo: `{calibration.method}`.",
                f"- Estado: `{calibration.status}`.",
                f"- Confianza: `{calibration.confidence}`.",
                f"- ID calibracion: `{calibration.calibration_id}`.",
                f"- Notas: {calibration.notes}",
                "",
            ]
        )

    lines.extend(
        [
            "## Validacion Visual Ligera",
            "",
            "- `minimap_base.png` muestra el modelo normalizado de cancha, tercios y porterias relativas.",
            "- `minimap_tracks.png` dibuja trayectorias rectificadas de robots y balon por clip.",
            "- `spatial_validation.csv` resume rangos, filas rectificadas, fallback y calidad por clip.",
            f"- `overlay_comparison.csv` referencia `{len(overlay_rows)}` overlays originales ligeros de Nivel 2 para comparar frames seleccionados.",
            "- No se abrieron videos completos ni se genero overlay pesado nuevo; `level3_tracks.csv` conserva `x`, `y`, bboxes, frames e IDs para trazabilidad contra los overlays Nivel 2.",
            "",
            "## Limitaciones Y Supuestos",
            "",
            "- La homografia usa una semilla de caja mediana de `green_soccer_field`; es suficiente para demo tactica aproximada, no para medicion oficial.",
            "- La orientacion real de equipos sigue desconocida, por lo que `defensive_third` y `attacking_third` son convenciones de eje, no lados reales de equipo.",
            "- Si la cancha visible es insuficiente o la caja cae bajo umbral, el script conserva fallback `image_extent_normalization` y marca filas con baja calidad.",
            "",
            "## Artefactos",
            "",
            "- `config.yaml`",
            "- `field_calibration.json`",
            "- `level3_tracks.csv`",
            "- `minimap_base.png`",
            "- `minimap_tracks.png`",
            "- `overlay_comparison.csv`",
            "- `spatial_validation.csv`",
            "- `summary.md`",
            "",
            "## Comando",
            "",
            "```bash",
            ".venv/bin/python scripts/run_level3_spatial_model.py",
            "```",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run_spatial_model(
    config_path: str | Path,
    source_dir: Path,
    output_dir: Path,
    clips: tuple[str, ...],
    min_field_confidence: float,
    min_field_coverage: float,
    manual_calibration_path: Path | None = None,
) -> list[dict[str, Any]]:
    config = load_config(config_path)
    specs = clip_specs_from_config(config, clips)
    output_dir.mkdir(parents=True, exist_ok=True)
    field_model = FieldModel(zone_axis=str(config.get("level2_events", {}).get("zone_axis", "y")))
    manual_calibrations = load_manual_calibrations(manual_calibration_path, specs)

    all_level3_rows: list[dict[str, Any]] = []
    calibrations: dict[str, ClipCalibration] = {}
    for clip_id in clips:
        tracks_path = source_dir / clip_id / "tracks_level2.csv"
        if not tracks_path.exists():
            raise FileNotFoundError(f"Missing Level 2 tracks for {clip_id}: {tracks_path}")
        rows = read_tracks_csv(tracks_path)
        spec = specs[clip_id]
        calibration = manual_calibrations.get(clip_id)
        if calibration is None:
            calibration = build_calibration_from_tracks(
                clip_id,
                rows,
                spec,
                min_field_confidence=min_field_confidence,
                min_field_coverage=min_field_coverage,
            )
        calibrations[clip_id] = calibration
        all_level3_rows.extend(rectify_track_rows(clip_id, rows, spec, calibration, field_model))

    validation_rows = summarize_rectified_tracks(all_level3_rows, calibrations)
    write_spatial_config(config, output_dir, source_dir, clips, min_field_confidence, min_field_coverage, manual_calibration_path)
    write_calibration_json(output_dir / "field_calibration.json", field_model, calibrations.values())
    write_level3_tracks(output_dir / "level3_tracks.csv", all_level3_rows)
    write_spatial_validation_csv(output_dir / "spatial_validation.csv", validation_rows)
    draw_minimap_base(output_dir / "minimap_base.png", field_model)
    draw_minimap_tracks(all_level3_rows, output_dir / "minimap_tracks.png", field_model)
    overlay_rows = write_overlay_comparison_csv(output_dir / "overlay_comparison.csv", source_dir, clips)
    write_summary(output_dir / "summary.md", source_dir, clips, calibrations, validation_rows, overlay_rows)
    return validation_rows


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate Level 3 spatial rectification and minimap evidence.")
    parser.add_argument("--config", default="configs/default.yaml")
    parser.add_argument("--source-dir", default=str(DEFAULT_SOURCE_DIR))
    parser.add_argument("--experiment", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--clips", nargs="+", default=list(DEFAULT_CLIPS))
    parser.add_argument("--calibration-json", default=None)
    parser.add_argument("--min-field-confidence", type=float, default=0.55)
    parser.add_argument("--min-field-coverage", type=float, default=0.35)
    args = parser.parse_args()

    validation_rows = run_spatial_model(
        args.config,
        Path(args.source_dir),
        Path(args.experiment),
        tuple(args.clips),
        min_field_confidence=args.min_field_confidence,
        min_field_coverage=args.min_field_coverage,
        manual_calibration_path=Path(args.calibration_json) if args.calibration_json else None,
    )
    usable = sum(1 for row in validation_rows if row["calibration_status"] == "usable")
    print(f"Wrote Level 3 spatial model to {args.experiment} ({usable}/{len(validation_rows)} clips usable)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
