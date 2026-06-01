from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Artifact:
    category: str
    artifact: str
    path: str
    kind: str
    git_policy: str
    notes: str


CANONICAL_ARTIFACTS = (
    Artifact("events", "validated_events", "experiments/test_004_events/video_836_real_events_120_180/events.json", "json", "include", "Eventos Nivel 1 recalculados con ByteTrack."),
    Artifact("events", "event_summary", "experiments/test_004_events/video_836_real_events_120_180/summary.md", "markdown", "include", "Resumen de posesion colision zona y descarte de shot."),
    Artifact("events", "event_metrics", "experiments/test_004_events/video_836_real_events_120_180/event_metrics.csv", "csv", "include", "Conteo de eventos generados."),
    Artifact("events", "ball_speed_diagnostic", "experiments/test_004_events/video_836_real_events_120_180/ball_speed.csv", "csv", "include", "Diagnostico de velocidad para umbral de shot."),
    Artifact("events", "nearest_robot_distance", "experiments/test_004_events/video_836_real_events_120_180/nearest_robot_distance.csv", "csv", "include", "Diagnostico de posesion por distancia."),
    Artifact("tracking", "bytetrack_tracks", "experiments/test_003_tracking/video_836_real_tracking_120_180/tracks_bytetrack.csv", "csv", "include", "Tracks recomendados para eventos Nivel 1."),
    Artifact("tracking", "tracking_metrics", "experiments/test_003_tracking/video_836_real_tracking_120_180/metrics.csv", "csv", "include", "Comparacion simple vs ByteTrack."),
    Artifact("tracking", "tracking_summary", "experiments/test_003_tracking/video_836_real_tracking_120_180/summary.md", "markdown", "include", "Resultado de tracking real."),
    Artifact("tracking", "tracking_heatmap", "experiments/test_003_tracking/video_836_real_tracking_120_180/heatmap_bytetrack.png", "png", "include", "Heatmap ligero de tracks ByteTrack."),
    Artifact("segmentation", "temporal_summary", "experiments/test_002_sam3_segmentation/video_836_temporal_stability_120_180/summary.md", "markdown", "include", "Resumen estabilidad temporal."),
    Artifact("segmentation", "temporal_stride1_metrics", "experiments/test_002_sam3_segmentation/video_836_temporal_stability_120_180/stride_1/metrics.csv", "csv", "include", "Metricas por frame stride 1."),
    Artifact("prompts", "prompt_summary", "experiments/test_002_sam3_segmentation/video_836_prompt_comparison_120_180/summary.md", "markdown", "include", "Seleccion de prompts base."),
    Artifact("prompts", "prompt_comparison", "experiments/test_002_sam3_segmentation/video_836_prompt_comparison_120_180/comparison.csv", "csv", "include", "Comparacion cuantitativa de prompts."),
    Artifact("more_videos", "multi_clip_summary", "experiments/test_006_more_copafutmx_videos/summary.md", "markdown", "include", "Expansion a video_480 video_595 video_667."),
    Artifact("more_videos", "multi_clip_metrics", "experiments/test_006_more_copafutmx_videos/metrics.csv", "csv", "include", "Metricas por clip adicional."),
    Artifact("deduplication", "dedup_summary", "experiments/test_009_level1_solidity/deduplication/summary.md", "markdown", "include", "Limpieza NMS/top-k antes de eventos multi-clip."),
    Artifact("deduplication", "video_595_cleaning_metrics", "experiments/test_009_level1_solidity/deduplication/video_595_cleaning_metrics.csv", "csv", "include", "Deduplicacion de balon en video_595."),
    Artifact("deduplication", "video_667_cleaning_metrics", "experiments/test_009_level1_solidity/deduplication/video_667_cleaning_metrics.csv", "csv", "include", "Top-k de robots en video_667."),
    Artifact("benchmark", "msi_benchmark_summary", "experiments/test_007_msi_benchmarks/video_836_sam3/summary.md", "markdown", "include", "Resumen benchmark SAM 3."),
    Artifact("benchmark", "msi_benchmark_metrics", "experiments/test_007_msi_benchmarks/video_836_sam3/metrics.csv", "csv", "include", "Metricas single vs multi-frame."),
    Artifact("benchmark", "msi_benchmark_json", "experiments/test_007_msi_benchmarks/video_836_sam3/benchmark.json", "json", "include", "Snapshot completo de benchmark y entorno."),
    Artifact("demo", "demo_local_summary", "experiments/evidence_level1/demo_local.md", "markdown", "include", "Ruta y configuracion de demo MP4 local no versionada."),
    Artifact("demo", "demo_local_mp4", "outputs/videos/level1_demo_video_836_120_180.mp4", "video", "exclude", "Demo MP4 local ignorada por Git."),
    Artifact("source_video", "video_836", "/home/guillermo/Vídeos/CopaFutMX/17 Abril/video-836_singular_display.mov", "video", "exclude", "Video completo local fuera de Git."),
    Artifact("source_checkpoint", "sam3_checkpoint", "checkpoints/sam3/sam3.pt", "checkpoint", "exclude", "Checkpoint local ignorado por Git."),
)


OVERLAY_REVIEW = (
    ("event_frame_120", "experiments/test_004_events/video_836_real_events_120_180/overlay_event_frame_120.png", "Captura representativa de eventos."),
    ("event_frame_150", "experiments/test_004_events/video_836_real_events_120_180/overlay_event_frame_150.png", "Captura representativa de eventos."),
    ("tracking_bytetrack_frame_120", "experiments/test_003_tracking/video_836_real_tracking_120_180/overlay_bytetrack_frame_120.png", "Captura ByteTrack representativa."),
    ("tracking_bytetrack_frame_150", "experiments/test_003_tracking/video_836_real_tracking_120_180/overlay_bytetrack_frame_150.png", "Captura ByteTrack representativa."),
    ("more_video_595_frame_120", "experiments/test_006_more_copafutmx_videos/video_595_short_window/overlay_frame_120_filtered_roi.png", "Captura de clip adicional con balon robot y cancha."),
    ("more_video_667_frame_120", "experiments/test_006_more_copafutmx_videos/video_667_short_window/overlay_frame_120_filtered_roi.png", "Captura de clip adicional con multiples robots."),
    ("temporal_stride1_frame_150", "experiments/test_002_sam3_segmentation/video_836_temporal_stability_120_180/stride_1/overlay_frame_150_filtered_roi.png", "Captura estabilidad temporal."),
)


def file_size(repo_root: Path, path_text: str) -> int:
    raw_path = Path(path_text)
    path = raw_path if raw_path.is_absolute() else repo_root / raw_path
    return path.stat().st_size if path.exists() else 0


def mib(size_bytes: int) -> str:
    return f"{size_bytes / (1024 * 1024):.2f}"


def png_inventory(repo_root: Path) -> tuple[int, int, int]:
    pngs = list((repo_root / "experiments").glob("**/*.png"))
    sizes = [path.stat().st_size for path in pngs]
    return len(sizes), sum(sizes), max(sizes) if sizes else 0


def write_artifact_manifest(repo_root: Path, output_dir: Path) -> None:
    with (output_dir / "artifact_manifest.csv").open("w", newline="", encoding="utf-8") as handle:
        fieldnames = ["category", "artifact", "path", "kind", "size_bytes", "git_policy", "notes"]
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        for artifact in CANONICAL_ARTIFACTS:
            row = {
                "category": artifact.category,
                "artifact": artifact.artifact,
                "path": artifact.path,
                "kind": artifact.kind,
                "size_bytes": file_size(repo_root, artifact.path),
                "git_policy": artifact.git_policy,
                "notes": artifact.notes,
            }
            writer.writerow(row)


def write_overlay_review(repo_root: Path, output_dir: Path) -> None:
    count, total, maximum = png_inventory(repo_root)
    with (output_dir / "overlay_size_review.csv").open("w", newline="", encoding="utf-8") as handle:
        fieldnames = ["artifact", "path", "size_bytes", "size_mib", "status", "notes"]
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        for artifact, path, notes in OVERLAY_REVIEW:
            size = file_size(repo_root, path)
            writer.writerow(
                {
                    "artifact": artifact,
                    "path": path,
                    "size_bytes": size,
                    "size_mib": mib(size),
                    "status": "ok" if size and size < 3_000_000 else "review",
                    "notes": notes,
                }
            )
        writer.writerow(
            {
                "artifact": "png_inventory_summary",
                "path": "experiments/**/*.png",
                "size_bytes": total,
                "size_mib": mib(total),
                "status": "reviewed",
                "notes": f"Inventario total actual: {count} PNG; maximo individual {maximum} bytes.",
            }
        )


def write_markdown(output_dir: Path) -> None:
    (output_dir / "README.md").write_text(
        "# Evidencia Nivel 1\n\n"
        "Esta carpeta es el indice final de evidencia ligera para la validacion Nivel 1 de FutBotMX con videos reales de CopaFutMX en la laptop MSI.\n\n"
        "## Alcance\n\n"
        "- Segmentacion SAM 3 real en `video_836`.\n"
        "- Filtrado por ROI de cancha.\n"
        "- Comparacion de prompts base.\n"
        "- Tracking real con ByteTrack.\n"
        "- Eventos Nivel 1 sobre tracks reales.\n"
        "- Expansion a tres clips adicionales: `video_480`, `video_595`, `video_667`.\n"
        "- Benchmark MSI de SAM 3.\n\n"
        "## Politica de evidencia ligera\n\n"
        "- No versionar videos completos, checkpoints ni outputs pesados.\n"
        "- Versionar JSON/CSV/Markdown, heatmaps PNG pequenos y capturas PNG representativas.\n"
        "- Mantener los videos locales bajo `/home/guillermo/Vídeos/CopaFutMX/...`.\n"
        "- Mantener el checkpoint local bajo `checkpoints/sam3/sam3.pt`, ignorado por Git.\n"
        "- Usar `artifact_manifest.csv` como indice de artefactos canonicos.\n"
        "- Usar `overlay_size_review.csv` para justificar las capturas versionadas.\n"
        "- Usar `validation_report.md` como validacion automatica previa a Nivel 2.\n\n"
        "## Resultado ejecutivo\n\n"
        "El pipeline Nivel 1 ya produce evidencia real de deteccion, tracking y eventos sobre CopaFutMX. Para la ventana `video_836` frames `120-180`, ByteTrack mantiene IDs mas estables que el tracker simple y permite recalcular eventos Nivel 1 con posesion provisional confiable, colision provisional, zona de actividad confiable y descarte de `shot` por jitter. En clips adicionales, `video_595` y `video_667` son buenos candidatos para continuar tracking/eventos; `video_480` queda para diagnostico de balon ausente/ocluido o recall bajo del prompt.\n\n"
        "## Archivos de esta carpeta\n\n"
        "- `DELIVERY_SUMMARY.md`: resumen final para entrega.\n"
        "- `artifact_manifest.csv`: lista curada de evidencia ligera y rutas.\n"
        "- `overlay_size_review.csv`: revision de tamanos de capturas PNG seleccionadas.\n"
        "- `validation_report.md`: checks automaticos de solidez Nivel 1.\n"
        "- `demo_local.md`: ruta y comando de la demo MP4 local no versionada.\n",
        encoding="utf-8",
    )
    (output_dir / "DELIVERY_SUMMARY.md").write_text(
        "# Resumen de entrega Nivel 1\n\n"
        "## Estado\n\n"
        "Nivel 1 queda respaldado con artefactos ligeros versionables: detecciones SAM 3, tracking, eventos, comparacion de prompts, pruebas en mas clips y benchmark MSI.\n\n"
        "## Hallazgos principales\n\n"
        "- SAM 3 funciona sobre video real CopaFutMX con checkpoint local `checkpoints/sam3/sam3.pt`.\n"
        "- ROI rectangular inicial `x=0..1360`, `y=620..1808` reduce falsos positivos fuera de cancha sin perder el balon en la ventana base.\n"
        "- Prompts base seleccionados: `green soccer field`, `small robot`, `ball`.\n"
        "- En `video_836` frames `120-180`, SAM 3 detecta balon en `59/61` frames y robots en `61/61`.\n"
        "- ByteTrack mejora continuidad frente al tracker simple: balon en `1` track y robots en `3` tracks sin inicios tardios en la ventana validada.\n"
        "- Eventos Nivel 1 recalculados: `2` posesiones provisionales confiables, `1` colision provisional, `1` zona de actividad confiable.\n"
        "- `shot` queda descartado en esa ventana: con umbral `350px/s` no genera candidatos y evita falsos positivos por jitter.\n"
        "- En clips adicionales, `video_595` y `video_667` detectan balon/robots/cancha en `5/5` frames de muestra.\n"
        "- `video_480` detecta robots/cancha en `5/5`, pero no balon en la muestra; requiere diagnostico antes de usarlo para eventos.\n"
        "- Benchmark MSI: carga SAM 3 `15.5693s`; multi-frame `1.2031s/frame`; pico CUDA reserved aproximado `4236 MB`.\n\n"
        "## Evidencia canonica\n\n"
        "La lista canonica esta en `artifact_manifest.csv`. No se duplican videos ni checkpoints en esta carpeta; se referencian artefactos ya generados en `experiments/test_*`.\n\n"
        "## Recomendacion siguiente\n\n"
        "Para trabajo posterior, usar `video_595` y `video_667` como siguientes candidatos para tracking/eventos reales, y abrir una prueba especifica de recuperacion de balon en `video_480`.\n",
        encoding="utf-8",
    )


def build_package(repo_root: Path, output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    write_markdown(output_dir)
    write_artifact_manifest(repo_root, output_dir)
    write_overlay_review(repo_root, output_dir)


def main() -> int:
    parser = argparse.ArgumentParser(description="Rebuild the lightweight Level 1 evidence package.")
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--output-dir", default="experiments/evidence_level1")
    args = parser.parse_args()
    build_package(Path(args.repo_root), Path(args.output_dir))
    print(f"Wrote Level 1 evidence package to {args.output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
