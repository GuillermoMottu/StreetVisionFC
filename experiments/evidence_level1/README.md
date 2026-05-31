# Evidencia Nivel 1

Esta carpeta es el indice final de evidencia ligera para la validacion Nivel 1 de FutBotMX con videos reales de CopaFutMX en la laptop MSI.

## Alcance

- Segmentacion SAM 3 real en `video_836`.
- Filtrado por ROI de cancha.
- Comparacion de prompts base.
- Tracking real con ByteTrack.
- Eventos Nivel 1 sobre tracks reales.
- Expansion a tres clips adicionales: `video_480`, `video_595`, `video_667`.
- Benchmark MSI de SAM 3.

## Politica de evidencia ligera

- No versionar videos completos, checkpoints ni outputs pesados.
- Versionar JSON/CSV/Markdown, heatmaps PNG pequenos y capturas PNG representativas.
- Mantener los videos locales bajo `/home/guillermo/Vídeos/CopaFutMX/...`.
- Mantener el checkpoint local bajo `checkpoints/sam3/sam3.pt`, ignorado por Git.
- Usar `artifact_manifest.csv` como indice de artefactos canonicos.
- Usar `overlay_size_review.csv` para justificar las capturas versionadas.

## Resultado ejecutivo

El pipeline Nivel 1 ya produce evidencia real de deteccion, tracking y eventos sobre CopaFutMX. Para la ventana `video_836` frames `120-180`, ByteTrack mantiene IDs mas estables que el tracker simple y permite recalcular eventos Nivel 1 con posesion provisional confiable, colision provisional, zona de actividad confiable y descarte de `shot` por jitter. En clips adicionales, `video_595` y `video_667` son buenos candidatos para continuar tracking/eventos; `video_480` queda para diagnostico de balon ausente/ocluido o recall bajo del prompt.

## Archivos de esta carpeta

- `DELIVERY_SUMMARY.md`: resumen final para entrega.
- `artifact_manifest.csv`: lista curada de evidencia ligera y rutas.
- `overlay_size_review.csv`: revision de tamanos de capturas PNG seleccionadas.
