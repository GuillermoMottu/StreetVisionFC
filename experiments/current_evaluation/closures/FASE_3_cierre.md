# Cierre de Fase 3 — Overlays, visualización y video demo

## 1. Resumen de cambios

- **Video demo generado** `outputs/videos/futbotmx_demo_h264.mp4`:
  - Duración: 46.6 segundos (≤ 120 s — requisito cumplido)
  - Tamaño: 2.3 MB (H.264, CRF 22)
  - Resolución: 680 × 904 px (50% de los 1360 × 1808 originales)
  - FPS de salida: 15 fps
- **Script principal** `scripts/create_phase3_demo.py` — genera el demo completo con 5 secciones:
  1. Title card (4 s)
  2. SAM 3 segmentación pixel-level frame 143 (13 s)
  3. ByteTrack tracking frames 120-180 (12 s)
  4. Eventos nivel 2 (8 s)
  5. Heatmap táctica + métricas (10 s)
- **`ARTIFACTS_INDEX.md`** creado — índice de todos los artefactos no versionables con comandos de regeneración
- **`scripts/visualize_detections.py`** — generador de visualizaciones estáticas de detecciones + masks

## 2. Archivos creados/modificados

| Archivo | Cambio | Motivo |
|---|---|---|
| `scripts/create_phase3_demo.py` | Nuevo — pipeline de demo completo | Entregable D1/D2 de Fase 3 |
| `scripts/visualize_detections.py` | Nuevo — overlays estáticos desde JSON | Herramienta de QA visual |
| `ARTIFACTS_INDEX.md` | Nuevo — índice de artefactos | Entregable D3 de Fase 3 |
| `outputs/videos/futbotmx_demo_h264.mp4` | Generado — no versionado (en .gitignore) | Demo final para evaluador |

## 3. Contenido del demo (D2 — elementos técnicos)

| Elemento | Presente | Evidencia |
|---|---|---|
| Frames reales del video | Sí | Secciones 2, 3, 4 |
| Bounding boxes + tracks | Sí | Sección 3 — tracks_bytetrack.csv |
| Mask SAM 3 visible | Sí | Sección 2 — 8 masks pixel-level (incl. portería) |
| Portería identificada | Sí | Frame 143, goalpost conf=0.96 amarillo |
| Métricas principales | Sí | Sección 5 — possession, track_count, fps |
| Visualización táctica | Sí | Sección 5 — heatmap de posiciones (ByteTrack) |

## 4. Pruebas QA

| Criterio | Estado | Evidencia |
|---|---|---|
| `ffprobe` confirma duración ≤ 120 s | Cumplido | 46.6 s |
| Video reproducible como H.264 | Cumplido | CRF 22, yuv420p, libx264 |
| Al menos 1 mask SAM 3 visible | Cumplido | 8 masks en sección 2 |
| Portería detectada/fallback visible | Cumplido | goalpost mask box-prompt |
| Heatmap táctico incluido | Cumplido | Sección 5 |
| Métricas incluidas | Cumplido | Sección 5 — 6 métricas |
| ARTIFACTS_INDEX documenta regeneración | Cumplido | `ARTIFACTS_INDEX.md` |

## 5. Tareas pendientes del usuario (humano en el loop — D4)

> **REQUERIDO**: El usuario debe revisar el video `outputs/videos/futbotmx_demo_h264.mp4` y confirmar que es correcto y presentable antes de considerar la Fase 3 como completada.

Comando de reproducción:
```bash
xdg-open outputs/videos/futbotmx_demo_h264.mp4
# o bien:
vlc outputs/videos/futbotmx_demo_h264.mp4
```

## 6. Riesgos o pendientes

- El video demo usa `team=neutral` en la sección de tracking — los equipos no están asignados aún (Fase 4).
- Las masks son únicamente del frame 143. Una versión final del demo (Fase posterior) podría incluir masks en múltiples frames.
- El heatmap cubre solo frames 120-180 (61 frames = 1 segundo de juego real).

## 7. Espera de aprobación

No continuaré con la Fase 4 hasta que el usuario confirme visualmente el video demo (D4) y apruebe explícitamente la Fase 3.
