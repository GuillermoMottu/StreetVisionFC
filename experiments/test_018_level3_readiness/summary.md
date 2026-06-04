# Readiness Nivel 3

## Resultado

- Estado: `desbloqueado`.
- Checks pass: `10`.
- Checks fail: `0`.

## Seleccion De Clips

- `video_595`: `principal` / `selected`; evidencia `experiments/test_017_level2_closure/video_595`; motivo: Mejor candidato narrativo: 61 frames observados, ByteTrack denso y highlight provisional con confianza 0.717.
- `video_667`: `secundario` / `selected`; evidencia `experiments/test_017_level2_closure/video_667`; motivo: Clip de contraste multi-clip: 61 frames observados, mas robots visibles y eventos descartados utiles para validar degradacion.
- `video_480`: `diagnostico` / `kept`; evidencia `experiments/test_017_level2_closure/video_480`; motivo: Se mantiene como diagnostico porque la muestra existente no detecta balon y requiere prompts pesados en MSI.

## Checks

- `level3_decision_registered`: `pass`; evidencia `FutBotMX_documentacion_markdown/DECISIONS.md`; nota: DEC-012 debe formalizar el inicio controlado de Nivel 3.
- `level2_closure_report_present`: `pass`; evidencia `experiments/test_017_level2_closure/summary.md`; nota: closure report present
- `level2_closure_summary_ready`: `pass`; evidencia `experiments/test_017_level2_closure/LEVEL2_CLOSURE_SUMMARY.md`; nota: Nivel 2 debe estar cerrado y Nivel 3 listo para gate/decision.
- `level2_closure_checks_green`: `pass`; evidencia `experiments/test_017_level2_closure/closure_checks.csv`; nota: 8 closure checks pass
- `no_tracked_heavy_files`: `pass`; evidencia `git ls-files`; nota: Videos, checkpoints, modelos y renders pesados deben quedar fuera de Git.
- `primary_clip_video_595_ready`: `pass`; evidencia `experiments/test_017_level2_closure/video_595`; nota: observed_frames=61, tracks=206, events=2
- `secondary_clip_video_667_ready`: `pass`; evidencia `experiments/test_017_level2_closure/video_667`; nota: observed_frames=61, tracks=306, events=2
- `minimum_two_dense_clips`: `pass`; evidencia `experiments/test_017_level2_closure/video_595, experiments/test_017_level2_closure/video_667`; nota: dense_clips_ready=2, expected>=2
- `diagnostic_clip_video_480_ready`: `pass`; evidencia `experiments/test_017_level2_closure/video_480`; nota: diagnostic summary present
- `level3_clip_selection_defined`: `pass`; evidencia `experiments/test_018_level3_readiness/clip_selection.csv`; nota: primary=video_595, secondary=video_667, diagnostic=video_480

## Decision

Nivel 3 queda desbloqueado para implementacion controlada desde Actividad 1.

## Alcance

- Actividad 0 no requiere inferencia SAM 3 nueva.
- `video_595` sera el clip principal para demo Nivel 3.
- `video_667` sera el clip secundario para validacion multi-clip.
- `video_480` se conserva como diagnostico por inestabilidad de balon.
- Los siguientes pasos deben producir solo evidencia ligera versionable.
