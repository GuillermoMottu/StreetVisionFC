"""
Pipeline unificado: Grounded-SAM → full_analysis → live_playback.

Etapas:
  1. Segmentación con OWLv2+SAM3 (Grounded-SAM) → detections.json
  2. Análisis completo de 12 etapas: tracking, Level3 Voronoi, grafos de
     interacción, asignación de equipos, dashboard, reel
  3. App de visualización en tiempo real (navegador en http://localhost:8766)

Usage:
    # Pipeline completo (primera vez):
    PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True \\
    python scripts/run_unified_analysis.py \\
      --video /ruta/video.mp4 \\
      --clip-id video_836 \\
      --start-frame 120 --end-frame 180

    # Usar detecciones ya calculadas (omitir segmentación):
    python scripts/run_unified_analysis.py \\
      --video /ruta/video.mp4 --clip-id video_836 \\
      --start-frame 120 --end-frame 180 \\
      --detections experiments/mi_analisis/detections.json

    # Solo relanzar visualización (sin re-segmentar ni re-analizar):
    python scripts/run_unified_analysis.py \\
      --video /ruta/video.mp4 --clip-id video_836 \\
      --start-frame 120 --end-frame 180 \\
      --experiment experiments/mi_analisis \\
      --skip-segmentation --skip-analysis

    # Con stride (1 de cada 5 frames — más rápido, menos resolución temporal):
    python scripts/run_unified_analysis.py \\
      --video /ruta/video.mp4 --clip-id video_836 \\
      --start-frame 0 --end-frame 600 --stride 5
"""
from __future__ import annotations

import argparse
import subprocess
import sys
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


def _get_video_metadata(video_path: str) -> tuple[float, int, int]:
    """Devuelve (fps, width, height) del video."""
    import cv2
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print(f"ERROR: no se pudo abrir el video: {video_path}", file=sys.stderr)
        sys.exit(1)
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    cap.release()
    return fps, width, height


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    # Video y rango de frames
    p.add_argument("--video", required=True, help="Ruta al video a analizar")
    p.add_argument("--clip-id", required=True, help="Identificador del clip (ej: video_836)")
    p.add_argument("--start-frame", type=int, required=True)
    p.add_argument("--end-frame", type=int, required=True)

    # Segmentación Grounded-SAM
    p.add_argument("--stride", type=int, default=1,
                   help="Procesar 1 de cada N frames en segmentación (default: 1 = todos)")
    p.add_argument("--detections", default=None,
                   help="JSON de detecciones existente — omite el paso de segmentación")
    p.add_argument("--owlv2-path", default="checkpoints/owlv2-base")
    p.add_argument("--sam3-checkpoint", default=None)
    p.add_argument("--confidence", type=float, default=0.1,
                   help="Umbral de confianza para OWLv2 (default: 0.1)")
    p.add_argument("--prompts", nargs="+",
                   default=["small robot", "ball", "green soccer field", "yellow goalpost"],
                   help="Prompts de texto para OWLv2")

    # Control de pipeline
    p.add_argument("--experiment", default=None,
                   help="Carpeta de salida. Se genera automáticamente si no se especifica.")
    p.add_argument("--config", default="configs/default.yaml")
    p.add_argument("--level2-root", default="experiments/test_017_level2_closure")
    p.add_argument("--skip-segmentation", action="store_true",
                   help="Saltar segmentación (requiere --detections o detections.json en --experiment)")
    p.add_argument("--skip-analysis", action="store_true",
                   help="Saltar full_analysis (relanza solo la app de visualización)")

    # Live playback
    p.add_argument("--allow-gpu", action="store_true",
                   help="Habilitar modos de inferencia con GPU en live playback")
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--port", type=int, default=8766)
    p.add_argument("--no-browser", action="store_true",
                   help="No abrir el navegador automáticamente")
    p.add_argument("--no-serve", action="store_true",
                   help="Omitir el paso de live playback (solo segmentación + análisis)")
    return p.parse_args()


def main() -> int:
    args = parse_args()

    print(f"\n{'='*62}")
    print("  FutBotMX — Pipeline Unificado")
    print(f"{'='*62}")
    print(f"  Video     : {args.video}")
    print(f"  Clip      : {args.clip_id}")
    print(f"  Frames    : {args.start_frame}–{args.end_frame}")
    if args.stride > 1:
        print(f"  Stride    : {args.stride} (1 de cada {args.stride} frames)")
    print()

    # ── [0/3] Metadatos del video ──────────────────────────────────────
    fps, width, height = _get_video_metadata(args.video)
    print(f"[0/3] Video: {width}×{height} @ {fps:.2f} fps")

    from futbotmx.full_analysis import next_experiment_dir
    if args.experiment:
        experiment = Path(args.experiment)
    else:
        experiment = next_experiment_dir(ROOT, args.clip_id, args.start_frame, args.end_frame)
    experiment.mkdir(parents=True, exist_ok=True)
    print(f"      Experimento: {experiment}")

    # ── [1/3] Segmentación Grounded-SAM ───────────────────────────────
    if args.detections:
        detections_json = Path(args.detections)
    else:
        detections_json = experiment / "detections.json"

    if args.skip_segmentation:
        if not detections_json.exists():
            print(
                f"ERROR: --skip-segmentation pero no se encontró: {detections_json}",
                file=sys.stderr,
            )
            return 1
        print(f"[1/3] Segmentación omitida → {detections_json}")
    else:
        print(f"\n[1/3] Segmentación Grounded-SAM (OWLv2 + SAM3)…")
        from futbotmx.segmentation import GroundedSAMSegmenter
        from futbotmx.io.detections import save_detections
        import time

        mask_dir = experiment / "masks"
        frame_indices = list(range(args.start_frame, args.end_frame + 1, args.stride))
        print(f"      Frames: {len(frame_indices)}  prompts: {args.prompts}")

        t0 = time.monotonic()
        seg = GroundedSAMSegmenter(
            owlv2_model_path=args.owlv2_path,
            sam3_checkpoint=args.sam3_checkpoint,
            owlv2_confidence_threshold=args.confidence,
            sam3_confidence_threshold=0.05,
            mask_output_dir=str(mask_dir),
        )
        all_frames = seg.segment_video(
            video_path=args.video,
            frame_indices=frame_indices,
            prompts=args.prompts,
            clip_id=args.clip_id,
        )
        elapsed = time.monotonic() - t0

        save_detections(all_frames, detections_json)
        total_dets = sum(len(fd.detections) for fd in all_frames)
        print(
            f"      {len(all_frames)} frames · {total_dets} detecciones "
            f"· {elapsed:.1f}s ({elapsed/max(1,len(all_frames)):.2f}s/frame)"
        )
        print(f"      Guardado → {detections_json}")

    # ── [2/3] Análisis completo (12 etapas) ───────────────────────────
    if args.skip_analysis:
        print(f"\n[2/3] Análisis omitido → usando {experiment}")
    else:
        print(f"\n[2/3] Análisis completo (tracking, Level3, Voronoi, grafos, dashboard)…")
        cmd = [
            sys.executable,
            str(ROOT / "scripts" / "run_full_analysis.py"),
            "--video", args.video,
            "--clip-id", args.clip_id,
            "--start-frame", str(args.start_frame),
            "--end-frame", str(args.end_frame),
            "--experiment", str(experiment),
            "--config", args.config,
            "--level2-root", args.level2_root,
            "--detections", str(detections_json),
        ]
        result = subprocess.run(cmd, cwd=str(ROOT), check=False)
        if result.returncode != 0:
            print(
                "WARN: full_analysis terminó con errores — "
                "continuando con los artefactos disponibles…"
            )

    # ── [3/3] Live Playback App ────────────────────────────────────────
    tracks_csv = experiment / "level3_spatial" / "level3_tracks.csv"
    events_json_path = experiment / "level3_events" / "level3_events.json"
    highlights_csv = experiment / "level3_events" / "level3_highlights.csv"

    if args.no_serve:
        print(f"\n[3/3] Live playback omitido (--no-serve).")
        print(f"      Para lanzarlo manualmente:")
        print(f"        python scripts/run_live_playback_app.py \\")
        print(f"          --video \"{args.video}\" --clip-id {args.clip_id} \\")
        print(f"          --tracks-csv {tracks_csv} \\")
        print(f"          --events-json {events_json_path} \\")
        print(f"          --highlights-csv {highlights_csv}")
        return 0

    print(f"\n[3/3] Iniciando live playback…")

    for path, label in [
        (tracks_csv, "tracks (level3_tracks.csv)"),
        (events_json_path, "events (level3_events.json)"),
        (highlights_csv, "highlights (level3_highlights.csv)"),
    ]:
        status = "OK" if path.exists() else "FALTANTE"
        print(f"      [{status}] {label}")

    from futbotmx.live_playback import (
        LivePlaybackConfig,
        build_live_playback_package,
        make_handler,
    )
    from http.server import ThreadingHTTPServer

    live_output = experiment / "live_playback"
    live_output.mkdir(parents=True, exist_ok=True)

    playback_config = LivePlaybackConfig(
        clip_id=args.clip_id,
        video_path=args.video,
        fps=fps,
        width=width,
        height=height,
        start_frame=args.start_frame,
        end_frame=args.end_frame,
        tracks_csv=tracks_csv.as_posix(),
        events_json=events_json_path.as_posix(),
        highlights_csv=highlights_csv.as_posix(),
        output_dir=live_output.as_posix(),
        allow_gpu=args.allow_gpu,
    )

    context = build_live_playback_package(ROOT, Path(args.config), playback_config)
    summary = context["summary"]
    print(f"      Tracks    : {summary['track_rows']}")
    print(f"      Eventos   : {summary['event_count']}")
    print(f"      Highlights: {summary['highlight_count']}")

    handler = make_handler(ROOT, context)
    server = ThreadingHTTPServer((args.host, args.port), handler)
    actual_host, actual_port = server.server_address
    display_host = args.host if args.host != "0.0.0.0" else actual_host
    url = f"http://{display_host}:{actual_port}"

    print(f"\n{'='*62}")
    print(f"  FutBotMX Live Playback: {url}")
    print(f"  Clip    : {args.clip_id}  ({args.start_frame}–{args.end_frame})")
    print(f"  Ctrl+C para detener")
    print(f"{'='*62}\n")

    if not args.no_browser:
        webbrowser.open(url)

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nDeteniendo FutBotMX live playback…")
    finally:
        server.server_close()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
