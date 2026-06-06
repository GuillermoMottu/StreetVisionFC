from __future__ import annotations

import argparse
import copy
from collections import Counter
from pathlib import Path
import sys
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from futbotmx.config import load_config, write_config_snapshot
from futbotmx.level3 import (
    LEVEL3_ADVANCED_EVENTS_RULE_VERSION,
    AdvancedEventsConfig,
    advanced_events_config_to_dict,
    build_advanced_events,
    write_level3_events,
    write_level3_highlights,
    write_narrative,
    write_overlay_validation,
)


DEFAULT_OUTPUT_DIR = Path("experiments/test_022_level3_advanced_events")


def write_config(config: dict[str, Any], output_dir: Path, advanced_config: AdvancedEventsConfig) -> None:
    snapshot = copy.deepcopy(config)
    snapshot["level3_advanced_events"] = {
        "rule_version": LEVEL3_ADVANCED_EVENTS_RULE_VERSION,
        **advanced_events_config_to_dict(advanced_config),
        "outputs": [
            "level3_events.json",
            "level3_highlights.csv",
            "level3_narrative.md",
            "overlay_validation.csv",
            "overlay_highlight_*.png",
            "summary.md",
        ],
    }
    write_config_snapshot(snapshot, output_dir / "config.yaml")


def write_summary(path: Path, outputs: dict[str, Any], overlay_rows: list[dict[str, Any]]) -> None:
    config: AdvancedEventsConfig = outputs["config"]
    events = outputs["events"]
    highlight_rows = outputs["highlight_rows"]
    possessions = outputs["possession_segments"]
    level2_possessions = outputs["level2_possession_segments"]
    fallback_possessions = outputs["fallback_possession_segments"]
    speeds = outputs["ball_speed_segments"]
    level2_events = outputs["level2_events"]
    event_counts = Counter(str(event["event_type"]) for event in events)
    reliability_counts = Counter(str(event.get("reliability", "unknown")) for event in events)
    primary_highlights = [row for row in highlight_rows if row["clip_id"] == config.primary_clip]
    top_primary = sorted(primary_highlights, key=lambda row: int(row["rank"]))[:3]
    top_all = sorted(highlight_rows, key=lambda row: int(row["rank"]))[:6]

    lines = [
        "# Eventos Avanzados Nivel 3",
        "",
        "## Resultado",
        "",
        "- Estado: `generado`.",
        f"- Regla: `{LEVEL3_ADVANCED_EVENTS_RULE_VERSION}`.",
        f"- Tracks fuente: `{config.tracks_csv}`.",
        f"- Eventos avanzados: `{len(events)}`.",
        f"- Highlights rankeados: `{len(highlight_rows)}`.",
        f"- Segmentos de posesion candidata: `{len(possessions)}`.",
        f"- Segmentos de posesion Nivel 2 reutilizables: `{len(level2_possessions)}`.",
        f"- Segmentos fallback desde interacciones Nivel 3: `{len(fallback_possessions)}`.",
        f"- Segmentos de velocidad de balon: `{len(speeds)}`.",
        f"- Overlays ligeros generados: `{len(overlay_rows)}`.",
        "",
        "## Eventos Por Tipo",
        "",
    ]
    for event_type, count in sorted(event_counts.items()):
        lines.append(f"- `{event_type}`: `{count}`.")
    lines.extend(["", "## Confiabilidad", ""])
    for reliability, count in sorted(reliability_counts.items()):
        lines.append(f"- `{reliability}`: `{count}`.")
    lines.extend(["", f"## Highlights Clip Principal `{config.primary_clip}`", ""])
    if len(primary_highlights) >= 3:
        lines.append("- Criterio cumplido: al menos tres highlights rankeados para el clip principal.")
    else:
        lines.append(f"- Criterio no completo: solo `{len(primary_highlights)}` highlights para el clip principal; se conserva evidencia y limitacion.")
    for row in top_primary:
        lines.append(
            f"- Rank `{row['rank']}` frames `{row['frame_start']}-{row['frame_end']}` "
            f"score `{row['score']}` confianza `{row['confidence']}`: {row['reason']}."
        )
    lines.extend(["", "## Top Highlights Globales", ""])
    for row in top_all:
        lines.append(
            f"- Rank `{row['rank']}` `{row['clip_id']}` frames `{row['frame_start']}-{row['frame_end']}` "
            f"score `{row['score']}` confiabilidad `{row['reliability']}`."
        )
    lines.extend(["", "## Cadenas De Pase", ""])
    if level2_possessions:
        lines.append("- Se reutilizaron segmentos de `level2_metrics.json` para cadenas de posesion.")
    else:
        lines.append("- `level2_metrics.json` no trae `possession_timeline` reutilizable en estos clips; se usa fallback desde `interaction_metrics.csv`.")
    lines.append("- Como las etiquetas de equipo siguen `neutral/unknown`, las cadenas se marcan como `dudoso_sin_equipo` cuando no hay cambio confiable del mismo equipo.")
    lines.extend(["", "## Fuentes Nivel 2", ""])
    for clip_id, clip_events in sorted(level2_events.items()):
        lines.append(f"- `{clip_id}` eventos Nivel 2 usados como respaldo: `{len(clip_events)}`.")
    lines.extend(
        [
            "",
            "## Limitaciones",
            "",
            "- La narrativa no afirma goles, faltas, tiros oficiales ni pases confirmados sin evidencia suficiente.",
            "- Los highlights son candidatos por reglas: velocidad normalizada, presion/interaccion, zona y confianza.",
            "- Los overlays son mini-mapas de validacion generados desde tracks rectificados, no frames de video pesado.",
            "",
            "## Artefactos",
            "",
            "- `config.yaml`",
            "- `level3_events.json`",
            "- `level3_highlights.csv`",
            "- `level3_narrative.md`",
            "- `overlay_validation.csv`",
            "- `overlay_highlight_*.png`",
            "- `summary.md`",
            "",
            "## Comando",
            "",
            "```bash",
            ".venv/bin/python scripts/run_level3_advanced_events.py",
            "```",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run_advanced_events(config_path: str | Path, output_dir: Path, advanced_config: AdvancedEventsConfig) -> dict[str, Any]:
    config = load_config(config_path)
    output_dir.mkdir(parents=True, exist_ok=True)
    outputs = build_advanced_events(advanced_config)
    write_config(config, output_dir, advanced_config)
    write_level3_events(output_dir / "level3_events.json", outputs["events"])
    write_level3_highlights(output_dir / "level3_highlights.csv", outputs["highlight_rows"])
    write_narrative(output_dir / "level3_narrative.md", outputs["events"], outputs["highlight_rows"], advanced_config)
    overlay_rows = write_overlay_validation(output_dir / "overlay_validation.csv", output_dir, outputs["tracks"], outputs["highlight_rows"])
    write_summary(output_dir / "summary.md", outputs, overlay_rows)
    return outputs


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate Level 3 advanced events, highlights and narrative.")
    parser.add_argument("--config", default="configs/default.yaml")
    parser.add_argument("--experiment", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--tracks", default="experiments/test_020_level3_spatial_model/level3_tracks.csv")
    parser.add_argument("--interaction-metrics", default="experiments/test_021_level3_tactical_metrics/interaction_metrics.csv")
    parser.add_argument("--interaction-edges", default="experiments/test_021_level3_tactical_metrics/interaction_edges.csv")
    parser.add_argument("--level2-root", default="experiments/test_017_level2_closure")
    parser.add_argument("--primary-clip", default="video_595")
    parser.add_argument("--highlight-top-n", type=int, default=6)
    args = parser.parse_args()

    advanced_config = AdvancedEventsConfig(
        tracks_csv=args.tracks,
        interaction_metrics_csv=args.interaction_metrics,
        interaction_edges_csv=args.interaction_edges,
        level2_root=args.level2_root,
        primary_clip=args.primary_clip,
        highlight_top_n=args.highlight_top_n,
    )
    outputs = run_advanced_events(args.config, Path(args.experiment), advanced_config)
    print(
        "Wrote Level 3 advanced events to "
        f"{args.experiment} ({len(outputs['events'])} events, {len(outputs['highlight_rows'])} highlights)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
