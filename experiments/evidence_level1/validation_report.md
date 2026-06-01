# Validacion Nivel 1

## Resumen

- Checks pass: `10`.
- Checks warn: `0`.
- Checks fail: `0`.

## Checks

- `field_prompt_real`: `pass`; field_detected_frames = `5/6`; esperado `>= 5/6`.
- `temporal_ball_recall`: `pass`; ball_detected_frames_stride1 = `59/61`; esperado `>= 58/61`.
- `temporal_robot_recall`: `pass`; robot_detected_frames_stride1 = `61/61`; esperado `>= 60/61`.
- `bytetrack_stability`: `pass`; robot_tracks_and_jump = `3 tracks, 33.7px max step`; esperado `<= 4 tracks and < 95.7px max step`.
- `events_level1_real`: `pass`; event_types = `activity_zone, collision, possession`; esperado `possession/collision/activity_zone and no shot`.
- `additional_clip_readiness`: `pass`; clips_with_ball_robot_5_of_5 = `video_595 video_667`; esperado `video_595 and video_667`.
- `msi_benchmark_margin`: `pass`; multi_frame_perf_vram = `1.2031s/frame, 4236MB reserved`; esperado `< 2.2370s/frame and < 5000MB reserved`.
- `deduplication_ready`: `pass`; removed_duplicates = `video_595 ball=1, video_667 robots=3`; esperado `video_595 ball=1 and video_667 robots=3`.
- `local_demo_ready`: `pass`; demo_summary_and_local_mp4 = `summary=True, mp4=True`; esperado `summary=True, mp4=True`.
- `heavy_files_policy`: `pass`; tracked_heavy_files = `none`; esperado `none`.

## Recomendaciones

- No hay bloqueadores de Nivel 1 en los checks automaticos.
