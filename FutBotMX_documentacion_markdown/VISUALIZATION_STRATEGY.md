# FutBotMX — Visualization Strategy

## 1. Objetivo narrativo

Las visualizaciones de FutBotMX deben mostrar de forma clara:

- Qué detectó el sistema.
- Cómo se movieron robots y balón.
- Qué eventos ocurrieron.
- Qué equipo tuvo más posesión o actividad.
- Por qué el análisis aporta valor frente al video original.

---

# 2. Visualizaciones por nivel

## Nivel 1 — MVP obligatorio

- Overlay de segmentación/tracking.
- IDs de robots y balón.
- Trails simples.
- Mapa de calor básico.
- Anotaciones simples de eventos.
- Capturas ligeras para GitHub.

## Nivel 2 — Intermedio

- Timeline de posesión.
- Timeline de eventos.
- Mapas de calor separados.
- Métricas visuales.
- Mejores anotaciones.

## Nivel 3 — Avanzado

- Voronoi.
- Grafos de interacción.
- Dashboard.
- Highlights.
- Narrativa deportiva.
- Reel final.

---

# 3. Visualizaciones ligeras para GitHub

Estas sí pueden subirse:

```text
screenshots/
thumbnails/
PNG comparativos
GIFs pequeños si pesan poco
reportes markdown
metrics.csv
events.json
summary.md
```

Ejemplos:

```text
experiments/test_003_tracking/screenshots/frame_001.png
experiments/test_004_events/event_timeline.png
experiments/test_005_heatmap/heatmap_ball.png
```

---

# 4. Visualizaciones pesadas fuera de GitHub

No subir directamente:

```text
videos completos anotados
clips largos
overlays pesados
renders finales grandes
frames completos
máscaras completas
```

Estos archivos pueden generarse localmente en la laptop MSI y documentarse mediante:

- Capturas.
- Thumbnails.
- Métricas.
- Rutas locales.
- Resumen markdown.
- Link externo si se decide usar almacenamiento externo.

---

# 5. Responsabilidad por equipo

## Laptop MSI

Debe generar:

- Overlays pesados.
- Videos anotados.
- Segmentaciones visuales.
- Tracking visual.
- Benchmarks.
- Capturas de evidencia.

## Escritorio

Debe preparar:

- README visual.
- Reportes.
- Dashboard ligero.
- Reel o demo final usando outputs generados por laptop.
- Análisis de CSV/JSON.
- Narrativa de resultados.

---

# 6. Qué debe verse en el video final

El video final local debe mostrar:

- Campo segmentado.
- Robots identificados.
- Balón identificado.
- IDs.
- Trails.
- Estado de posesión.
- Eventos relevantes.
- Anotaciones legibles.

El video completo puede quedarse fuera de GitHub si es pesado.

---

# 7. Qué debe verse en README

El README debe incluir:

- Captura del overlay.
- Captura de tracking.
- Mapa de calor.
- Fragmento de JSON de eventos.
- Tabla de métricas.
- Explicación del flujo de dos equipos.
- Estado de Nivel 1, Nivel 2 y Nivel 3.

---

# 8. Relación evento-visualización

| Evento | Visualización |
|---|---|
| Posesión | Timeline, indicador en overlay |
| Pase | Flecha entre robots |
| Tiro | Flecha hacia portería |
| Gol | Marcador destacado |
| Intercepción | Alerta de cambio de posesión |
| Colisión | Círculo o alerta |
| Recuperación | Cambio de equipo |
| Zona de actividad | Heatmap |
| Jugada destacada | Clip local o timestamp |

---

# 9. Configuración sugerida

```yaml
visualization:
  draw_masks: true
  draw_bboxes: true
  draw_ids: true
  draw_centroids: true
  draw_trails: true
  trail_length: 30
  draw_events: true
  draw_possession_status: true
  export_screenshots: true
  export_video: true
  export_heatmap: true
  export_timeline: true
```

---

# 10. Regla de evidencia

Toda visualización usada para afirmar avance debe estar respaldada por:

- Commit hash.
- Configuración.
- Captura ligera.
- Summary markdown.
- Equipo usado.
- Fecha.
