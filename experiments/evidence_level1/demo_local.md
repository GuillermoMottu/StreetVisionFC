# Demo local Nivel 1

## Estado

Demo MP4 generado localmente y no versionado por Git.

## Configuracion

- Video fuente: `/home/guillermo/Vídeos/CopaFutMX/17 Abril/video-836_singular_display.mov`
- Tracks: `experiments/test_003_tracking/video_836_real_tracking_120_180/tracks_bytetrack.csv`
- Frames: `120-180`
- FPS demo: `15.0`
- Salida local: `outputs/videos/level1_demo_video_836_120_180.mp4`

## Comando

```bash
python scripts/create_demo_video.py \
  --video "/home/guillermo/Vídeos/CopaFutMX/17 Abril/video-836_singular_display.mov" \
  --tracks experiments/test_003_tracking/video_836_real_tracking_120_180/tracks_bytetrack.csv \
  --output outputs/videos/level1_demo_video_836_120_180.mp4 \
  --summary experiments/evidence_level1/demo_local.md \
  --start-frame 120 --end-frame 180 --fps 15
```

## Politica Git

El archivo `.mp4` queda fuera de Git por `.gitignore`; este resumen documenta como regenerarlo.
