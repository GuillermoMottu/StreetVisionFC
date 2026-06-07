# Actividad 19 - Overlay De Video Corto

## Resultado

- Estado: `generado`.
- Regla: `activity19_video_overlay_v0.1`.
- Segmentos seleccionados: `3`.
- Clips incluidos: `video_595`.
- Duracion sugerida: `7.5` segundos.
- MP4 local esperado: `local_outputs/activity19/video_595_overlay_clip.mp4`.
- MP4 generado localmente y no versionado.

## Segmentos

- `overlay_segment_01` rank `1` `video_595` frames `122-123` score `82.9` conf `0.89`.
- `overlay_segment_02` rank `2` `video_595` frames `128-129` score `81.4` conf `0.83`.
- `overlay_segment_03` rank `3` `video_595` frames `133-135` score `81.1` conf `0.81`.

## Render Local

```bash
cd experiments/test_037_activity19_video_overlay
bash render_overlay_clip.sh
```

## Artefactos

- `video_overlay_segments.csv`
- `video_overlay_manifest.csv`
- `video_overlay_contact_sheet.png`
- `overlay_thumb_rank_*.png`
- `video_overlay_ffmpeg_inputs.txt`
- `render_overlay_clip.sh`
- `render_overlay_clip_plan.md`

## Limitaciones

- El paquete versiona evidencia visual ligera, no el MP4 final.
- Los eventos siguen siendo highlights candidatos con lenguaje conservador.
