"""
Phase 4 — Team assignment for video_836 (frames 120-180).

Converts tracks_bytetrack.csv to level3 format, runs initial_side_fallback
team assignment, saves an editable team_assignment.csv and a robot crop
contactsheet for human validation.

Human-in-the-loop requirement: the user must review the contactsheet and
validate (or edit) team_assignment.csv before teams are considered final.

Usage:
    python scripts/run_phase4_team_assignment.py \
        --video "/home/guillermo/Vídeos/CopaFutMX/17 Abril/video-836_singular_display.mov"
"""
from __future__ import annotations

import csv
import json
from pathlib import Path
import sys

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from futbotmx.level3.team_assignment import (
    TeamAssignmentConfig,
    build_team_assignment_package,
    write_json_summary as write_team_assignment_json_summary,
)

CLIP_ID = "video_836"
FPS = 59.707724425887264
IMG_W, IMG_H = 1360, 1808
SOURCE_TRACKS = Path("experiments/test_003_tracking/video_836_real_tracking_120_180/tracks_bytetrack.csv")
EXPERIMENT_DIR = Path("experiments/current_evaluation/phase4_team_assignment")
LEVEL3_TRACKS_TMP = EXPERIMENT_DIR / "level3_tracks_video836.csv"

LEVEL3_FIELDS = [
    "clip_id", "frame", "time_sec", "track_id", "source_track_id",
    "class_name", "team", "x", "y",
    "bbox_x1", "bbox_y1", "bbox_x2", "bbox_y2", "confidence",
    "x_norm", "y_norm", "zone",
    "calibration_id", "calibration_status", "calibration_confidence",
    "track_quality", "notes",
]

# Team colors for contactsheet overlay
TEAM_COLORS = {
    "team_left":  (80, 180, 255),  # blue
    "team_right": (80, 255, 100),  # green
    "unknown":    (180, 180, 180),
}


def bytetrack_to_level3(source: Path, clip_id: str, fps: float, w: int, h: int) -> list[dict]:
    rows = []
    with source.open("r", newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            frame = int(float(row["frame"]))
            x = float(row["x"])
            y = float(row["y"])
            rows.append({
                "clip_id": clip_id,
                "frame": frame,
                "time_sec": round(frame / fps, 6),
                "track_id": row["track_id"],
                "source_track_id": row["track_id"],
                "class_name": row["class_name"],
                "team": row.get("team", "neutral"),
                "x": x,
                "y": y,
                "bbox_x1": row["bbox_x1"],
                "bbox_y1": row["bbox_y1"],
                "bbox_x2": row["bbox_x2"],
                "bbox_y2": row["bbox_y2"],
                "confidence": row["confidence"],
                "x_norm": round(x / w, 6),
                "y_norm": round(y / h, 6),
                "zone": "unknown",
                "calibration_id": "none",
                "calibration_status": "uncalibrated",
                "calibration_confidence": "0.0",
                "track_quality": "usable",
                "notes": "",
            })
    return rows


def write_level3_csv(rows: list[dict], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=LEVEL3_FIELDS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def generate_contactsheet(
    video_path: str,
    assignments: list[dict],
    source_tracks: list[dict],
    out_path: Path,
    contact_frame: int = 143,
) -> None:
    """Extract robot crops from contact_frame and assemble a labelled contactsheet."""
    cap = cv2.VideoCapture(video_path)
    cap.set(cv2.CAP_PROP_POS_FRAMES, contact_frame)
    ok, bgr = cap.read()
    cap.release()
    if not ok:
        print(f"  WARNING: Could not read frame {contact_frame} for contactsheet")
        return

    team_by_id = {row["track_id"]: row["team"] for row in assignments}

    # collect robot rows for this frame
    frame_rows = [r for r in source_tracks
                  if int(float(r["frame"])) == contact_frame and "robot" in str(r["class_name"])]

    CROP_H, CROP_W = 180, 180
    PAD = 8

    crops: list[np.ndarray] = []
    for row in sorted(frame_rows, key=lambda r: r["track_id"]):
        tid = str(row["track_id"])
        team = team_by_id.get(tid, "unknown")
        color = TEAM_COLORS.get(team, (200, 200, 200))

        x1 = max(0, int(float(row["bbox_x1"])))
        y1 = max(0, int(float(row["bbox_y1"])))
        x2 = min(IMG_W, int(float(row["bbox_x2"])))
        y2 = min(IMG_H, int(float(row["bbox_y2"])))

        crop = bgr[y1:y2, x1:x2]
        if crop.size == 0:
            crop = np.zeros((CROP_H, CROP_W, 3), dtype=np.uint8)
        crop = cv2.resize(crop, (CROP_W, CROP_H))

        # colored border for team
        cv2.rectangle(crop, (0, 0), (CROP_W - 1, CROP_H - 1), color, 4)

        # labels
        label1 = tid
        label2 = f"team: {team}"
        cv2.putText(crop, label1, (4, 16), cv2.FONT_HERSHEY_SIMPLEX, 0.40, (255, 255, 255), 1, cv2.LINE_AA)
        cv2.putText(crop, label2, (4, CROP_H - 6), cv2.FONT_HERSHEY_SIMPLEX, 0.38, color, 1, cv2.LINE_AA)

        crops.append(crop)

    if not crops:
        print("  No robot crops found for contactsheet")
        return

    # add legend
    legend_h = 50
    sheet_w = len(crops) * (CROP_W + PAD) + PAD
    sheet = np.zeros((CROP_H + legend_h + PAD * 2, sheet_w, 3), dtype=np.uint8)

    for i, crop in enumerate(crops):
        x_off = PAD + i * (CROP_W + PAD)
        sheet[PAD: PAD + CROP_H, x_off: x_off + CROP_W] = crop

    # legend row
    ly = CROP_H + PAD + 20
    cv2.putText(sheet, f"Frame {contact_frame} | Asignacion tentativa — REQUIERE VALIDACION HUMANA",
                (PAD, ly), cv2.FONT_HERSHEY_SIMPLEX, 0.38, (200, 200, 200), 1)
    for team, col in [("team_left", TEAM_COLORS["team_left"]), ("team_right", TEAM_COLORS["team_right"])]:
        ly += 18
        cv2.rectangle(sheet, (PAD, ly - 10), (PAD + 14, ly + 2), col, -1)
        cv2.putText(sheet, team, (PAD + 18, ly), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (200, 200, 200), 1)
        PAD_next = PAD + 90
        PAD = PAD_next  # shift right for next legend item — avoid mutation
        break

    out_path.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(out_path), sheet)
    print(f"  Contactsheet → {out_path}")


def apply_teams_to_bytetrack(source: Path, assignments: list[dict], out: Path) -> int:
    """Write tracks_bytetrack_with_teams.csv — same format + team column updated."""
    team_by_id = {row["track_id"]: row["team"] for row in assignments}
    updated = 0
    rows_out = []
    fieldnames = []
    with source.open("r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames or []
        for row in reader:
            new_row = dict(row)
            tid = row["track_id"]
            if tid in team_by_id:
                new_row["team"] = team_by_id[tid]
                updated += 1
            rows_out.append(new_row)

    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows_out)
    return updated


def main() -> int:
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--video", required=True)
    parser.add_argument("--contact-frame", type=int, default=143)
    args = parser.parse_args()

    EXPERIMENT_DIR.mkdir(parents=True, exist_ok=True)

    print("[1/5] Converting bytetrack → level3 format")
    source_tracks_l3 = bytetrack_to_level3(SOURCE_TRACKS, CLIP_ID, FPS, IMG_W, IMG_H)
    write_level3_csv(source_tracks_l3, LEVEL3_TRACKS_TMP)
    robot_count = sum(1 for r in source_tracks_l3 if "robot" in r["class_name"])
    robot_ids = sorted({r["track_id"] for r in source_tracks_l3 if "robot" in r["class_name"]})
    print(f"  {len(source_tracks_l3)} rows, {robot_count} robot rows, robots: {robot_ids}")

    print("[2/5] Running team assignment (initial_side_fallback + x_norm axis)")
    config = TeamAssignmentConfig(
        tracks_csv=str(LEVEL3_TRACKS_TMP),
        manual_assignment_csv="",
        output_dir=str(EXPERIMENT_DIR),
        fallback_split_axis="x_norm",
        fallback_left_team="team_left",
        fallback_right_team="team_right",
        initial_window_frames=10,
        min_side_spread_norm=0.10,
    )
    outputs = build_team_assignment_package(config)
    assignments = outputs["assignments"]
    strategy_rows = outputs["strategy_rows"]

    write_team_assignment_json_summary(
        EXPERIMENT_DIR / "team_assignment_summary.json",
        assignments,
        strategy_rows,
    )

    print("[3/5] Team assignment results:")
    for row in assignments:
        print(f"  {row['track_id']:20s} → team={row['team']:12s}  conf={row['confidence']:.2f}  source={row['source']}")

    print("[4/5] Applying teams to bytetrack tracks")
    out_tracks = EXPERIMENT_DIR / "tracks_bytetrack_with_teams.csv"
    updated = apply_teams_to_bytetrack(SOURCE_TRACKS, assignments, out_tracks)
    print(f"  Updated {updated} rows → {out_tracks}")

    print("[5/5] Generating robot crop contactsheet")
    bytetrack_rows_raw = []
    with SOURCE_TRACKS.open("r", newline="", encoding="utf-8") as f:
        bytetrack_rows_raw = list(csv.DictReader(f))
    generate_contactsheet(
        args.video,
        assignments,
        bytetrack_rows_raw,
        EXPERIMENT_DIR / "robot_contactsheet.png",
        contact_frame=args.contact_frame,
    )

    # write human-validation instructions
    instructions = EXPERIMENT_DIR / "VALIDACION_EQUIPOS.md"
    instructions.write_text(
        "# Validacion de Equipos — video_836\n\n"
        "## Asignacion tentativa (initial_side_fallback, x_norm)\n\n"
        "| track_id | team tentativo | confianza | notas |\n"
        "|---|---|---|---|\n"
        + "".join(
            f"| {r['track_id']} | {r['team']} | {r['confidence']:.2f} | {r['notes']} |\n"
            for r in assignments
        )
        + "\n## Instrucciones\n\n"
        "1. Abre `robot_contactsheet.png` y compara los crops de cada robot.\n"
        "2. Si la asignacion es correcta, escribe 'Confirmado' en el issue/respuesta.\n"
        "3. Si necesitas corregir, edita `team_assignment.csv`:\n"
        "   - Cambia el campo `team` de cada `track_id` al equipo correcto.\n"
        "   - Usa exactamente `team_left` o `team_right` (u otro nombre consistente).\n"
        "4. Vuelve a ejecutar este script con `--manual-assignment` apuntando al CSV editado.\n\n"
        "## Metodo usado\n\n"
        "Estrategia: `initial_side_fallback` — se asigna equipo basado en la posicion "
        "horizontal (x_norm) inicial del robot respecto al punto medio de todos los robots. "
        "**No es deteccion visual de uniformes.** Declarado como aproximacion heuristica.\n",
        encoding="utf-8",
    )
    print(f"\nInstrucciones de validacion → {instructions}")
    print("\n[HUMANO EN EL LOOP] Revisar robot_contactsheet.png y confirmar equipos.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
