# Plan De Render Local Reel Nivel 3

El MP4 no se versiona. Para renderizarlo localmente desde las capturas ligeras:

```bash
cd experiments/test_034_full_analysis/reel
bash render_reel_local.sh
```

Salida local esperada: `local_outputs/level3_reel/futbotmx_level3_reel.mp4`.

## Segmentos

- `reel_segment_01` rank `1` frames `122-123` thumbnail `reel_thumb_rank_01_video_595_frame_122.png`.
- `reel_segment_02` rank `2` frames `128-129` thumbnail `reel_thumb_rank_02_video_595_frame_128.png`.
- `reel_segment_03` rank `3` frames `133-135` thumbnail `reel_thumb_rank_03_video_595_frame_133.png`.
- `reel_segment_04` rank `4` frames `124-125` thumbnail `reel_thumb_rank_04_video_595_frame_124.png`.

## Notas

- El render usa thumbnails estaticos para evitar versionar video pesado.
- Si se desea un reel con video real, usar los frames/timestamps de `reel_segments.csv` sobre los videos locales fuera de Git.
