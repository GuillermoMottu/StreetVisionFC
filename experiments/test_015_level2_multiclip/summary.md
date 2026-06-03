# test_015_level2_multiclip

## Objetivo

Ejecutar tracking/eventos Nivel 2 en clips reales adicionales y compararlos contra `video_836`.

## Clips

- `video_595` (`candidate`): frames `5`, tracks `3`, posesion `0.502386s`, eventos recovery/interception/highlight `1/1/1`.
- `video_667` (`candidate`): frames `5`, tracks `4`, posesion `0.0s`, eventos recovery/interception/highlight `0/1/1`.
- `video_836` (`baseline`): frames `61`, tracks `4`, posesion `0.904406s`, eventos recovery/interception/highlight `4/1/1`.
- `video_480` (`diagnostic`): frames `0`, tracks `0`, posesion `0s`, eventos recovery/interception/highlight `0/0/0`.

## Comparacion Contra video_836

- `video_836` conserva la referencia mas densa: tracks ByteTrack en frames `120-180` y eventos ya validados.
- `video_595` y `video_667` usan muestras sparse cada 30 frames; las metricas temporales son aproximadas y no equivalen a tracking denso.
- `video_595` muestra desplazamiento fuerte del balon hacia zona de ataque, por eso genera candidato de highlight.
- `video_667` conserva buen recall de balon pero multiples robots por frame; la deduplicacion/top-k reduce ruido antes de tracking.
- `video_480` queda como diagnostico de balon: robot/cancha estables, balon no detectado en la muestra, sin eventos deportivos.

## Diferencias Por Camara, Iluminacion Y Oclusion

- `video_595`: perspectiva vertical similar pero resolucion `1344x1792`; duplicados puntuales sugieren ambiguedad visual/occlusion local.
- `video_667`: resolucion `1360x1808`; robots mas numerosos o mas visibles elevan candidatos por frame y riesgo de cambios de ID.
- `video_836`: ventana densa y ByteTrack reducen fragmentacion, por lo que es la mejor referencia para comparar.
- `video_480`: probable ausencia, oclusion o bajo recall del prompt de balon; se reserva para diagnostico antes de eventos.

## Politica De Archivos

- No se generaron ni versionaron videos completos.
- Solo se versionan CSV/JSON/Markdown ligeros.

## Baseline

- Tracks base: `experiments/test_003_tracking/video_836_real_tracking_120_180/tracks_bytetrack.csv`.
