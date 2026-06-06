# FutBotMX — Events Definition

## 1. Propósito

Este documento define los eventos deportivos que FutBotMX debe detectar a partir de segmentación, tracking y análisis geométrico.

La lógica de eventos puede desarrollarse principalmente en escritorio usando CSV/JSON generados por la laptop MSI. La inferencia visual base debe ejecutarse en la laptop.

---

# 2. Flujo recomendado para validar eventos

1. La laptop MSI ejecuta SAM 3.
2. La laptop genera detecciones, tracking y resultados preliminares.
3. La laptop sube a GitHub archivos ligeros:
   - `tracks.csv`
   - `events.json`
   - `metrics.csv`
   - capturas ligeras
   - `summary.md`
4. El escritorio hace pull.
5. El escritorio analiza los CSV/JSON con Codex o Claude Desktop.
6. Se ajustan reglas heurísticas de eventos.
7. Los cambios se suben a GitHub.
8. La laptop vuelve a validar visualmente.

---

# 3. Regla de evidencia

Cada evento probado debe tener evidencia en:

```text
experiments/test_xxx/
```

Evidencia mínima:

```text
summary.md
config.yaml
tracks.csv
events.json
screenshots/
```

No se debe declarar un evento como validado sin evidencia.

---

# 4. Esquema JSON estándar

```json
{
  "event_id": "evt_000001",
  "event_type": "pass",
  "frame_start": 120,
  "frame_end": 168,
  "time_start_sec": 4.0,
  "time_end_sec": 5.6,
  "team": "ally",
  "primary_object_id": "robot_ally_02",
  "secondary_object_id": "robot_ally_04",
  "ball_id": "ball_01",
  "zone": "middle_third",
  "position_start": {
    "x": 420,
    "y": 310
  },
  "position_end": {
    "x": 610,
    "y": 295
  },
  "confidence": 0.72,
  "reliability": "provisional",
  "rule_version": "events_v0.1",
  "evidence": {
    "source_experiment": "experiments/test_004_event_detection",
    "tracks_file": "tracks.csv",
    "config_file": "config.yaml",
    "notes": "Ball moved from robot_ally_02 proximity to robot_ally_04 proximity"
  }
}
```

---

# 5. Eventos mínimos Nivel 1

| Evento | Nivel | Estado |
|---|---|---|
| Posesión | Nivel 1 | Validado inicial con tracks reales |
| Pase simple | Nivel 1 | Implementado; no observado como confiable en ventana base |
| Tiro aproximado | Nivel 1 | Implementado; descartado en ventana base por jitter |
| Colisión básica | Nivel 1 | Validado provisional con tracks reales |
| Zona de actividad básica | Nivel 1 | Validado con tracks reales |

---

# 6. Eventos Nivel 2

| Evento | Nivel | Estado |
|---|---|---|
| Intercepción | Nivel 2 | Implementado inicial |
| Recuperación | Nivel 2 | Implementado inicial |
| Jugada destacada | Nivel 2 | Implementado inicial |
| Timeline de posesión | Nivel 2 | Implementado |

---

# 7. Eventos Nivel 3

| Evento | Nivel | Estado |
|---|---|---|
| Cadena de pases | Nivel 3 | Implementada como candidata/dudosa cuando falta equipo confiable |
| Highlight avanzado | Nivel 3 | Implementado con ranking, score y confianza |
| Narrativa deportiva | Nivel 3 | Implementada por reglas conservadoras |
| Grafo de interacción | Nivel 3 | Implementado por proximidad, posesion candidata, presion y disputa |
| Revision visual ligera | Nivel 3 | Implementada con overlays y estado `confiable`, `provisional` o `descartado` |

---

# 8. Definiciones principales

## 8.1 Posesión

Un robot tiene posesión cuando el balón permanece dentro de un radio de proximidad durante un número mínimo de frames.

### Entradas

- `tracks.csv`
- Posición del balón.
- Posiciones de robots.
- Umbral de distancia.
- FPS.

### Lógica inicial

1. Calcular distancia robot-balón.
2. Elegir robot más cercano.
3. Verificar umbral.
4. Confirmar duración mínima.
5. Registrar posesión.

---

## 8.2 Pase

Un pase ocurre cuando el balón cambia de proximidad/control desde un robot hacia otro robot del mismo equipo.

### Entradas

- Eventos de posesión.
- Tracks de balón.
- Tracks de robots.
- Equipo de cada robot.

### Lógica inicial

1. Detectar posesión inicial.
2. Detectar salida del balón.
3. Detectar nueva proximidad.
4. Confirmar mismo equipo.
5. Registrar pase.

---

## 8.3 Tiro

Un tiro ocurre cuando el balón se mueve desde un robot hacia la zona de portería con velocidad suficiente.

### Entradas

- Trayectoria del balón.
- Zona de portería.
- Velocidad del balón.
- Último robot cercano.

### Lógica inicial

1. Detectar aumento de velocidad.
2. Calcular vector de movimiento.
3. Verificar dirección hacia portería.
4. Registrar tiro.

---

## 8.4 Colisión

Una colisión ocurre cuando dos robots están demasiado cerca o sus máscaras/bounding boxes se superponen durante varios frames.

### Entradas

- Bounding boxes.
- Máscaras si existen.
- Distancias entre robots.
- Duración.

### Lógica inicial

1. Calcular distancia.
2. Revisar intersección.
3. Confirmar duración.
4. Registrar colisión.

---

## 8.5 Zona de actividad

Una zona de actividad representa una región del campo con alta concentración de posiciones o eventos.

### Entradas

- Tracks.
- División del campo.
- Ventana temporal.

### Lógica inicial

1. Dividir campo en zonas.
2. Acumular posiciones.
3. Calcular densidad.
4. Registrar zona dominante.

---

## 8.6 Recuperacion de balon

Una recuperacion ocurre cuando un robot vuelve a quedar dentro del umbral de posesion despues de un tramo libre, desconocido o sin posesion asignada.

### Entradas

- `tracks.csv`
- Posicion del balon.
- Posiciones de robots.
- Umbral de posesion.
- Minimo de frames para aceptar la recuperacion.

### Lógica inicial

1. Calcular el robot mas cercano al balon por frame.
2. Construir tramos de posesion por robot.
3. Marcar recuperacion cuando inicia un tramo de posesion.
4. Usar `confiable` si el tramo es largo y cercano, `provisional` si cumple minimo, `descartado` si no alcanza el minimo.

---

## 8.7 Intercepcion aproximada

Una intercepcion aproximada ocurre cuando el balon cambia de robot poseedor en una ventana corta y con velocidad suficiente.

### Entradas

- Tramos de posesion.
- Velocidad aproximada del balon.
- Gap maximo entre posesiones.
- Equipo del robot cuando exista.

### Lógica inicial

1. Comparar tramos consecutivos de posesion.
2. Verificar cambio de robot.
3. Medir gap entre salida y nueva posesion.
4. Revisar velocidad del balon durante el cambio.
5. Marcar `provisional` si cumple; `descartado` si no hay cambio valido o si los robots son del mismo equipo confirmado.

---

## 8.8 Jugada destacada

Una jugada destacada inicial se marca cuando existe velocidad alta del balon, zona relevante o cambio de posesion.

### Entradas

- Velocidad del balon por segmento.
- Zona del campo.
- Cambios de posesion.

### Lógica inicial

1. Encontrar el segmento con mayor velocidad del balon.
2. Revisar si supera el umbral configurado.
3. Registrar zona del balon.
4. Marcar `provisional` hasta tener validacion visual humana; `descartado` si no supera umbral.

---

## 8.9 Cadena de pases Nivel 3

Una cadena de pases Nivel 3 agrupa tramos consecutivos de posesion candidata cuando el balon cambia de robot dentro de una ventana corta.

### Entradas

- `level3_tracks.csv`.
- `interaction_metrics.csv`.
- Posesion candidata por proximidad.
- Equipo del robot cuando exista.

### Logica actual

1. Reutilizar posesiones Nivel 2 cuando existan.
2. Usar fallback desde interacciones Nivel 3 si no hay timeline reutilizable.
3. Agrupar cambios de poseedor dentro de `max_pass_gap_frames`.
4. Marcar como `same_team_chain` solo si el equipo esta identificado.
5. Marcar como `dudoso_sin_equipo` cuando los tracks sigan `neutral` o `unknown`.

---

## 8.10 Highlight avanzado Nivel 3

Un highlight avanzado combina velocidad normalizada del balon, posesion candidata, presion/disputa, zona y respaldo Nivel 2.

### Entradas

- `level3_tracks.csv`.
- `interaction_metrics.csv`.
- `interaction_edges.csv`.
- `level2_events.json`.

### Logica actual

1. Calcular segmentos de velocidad del balon en coordenadas normalizadas.
2. Sumar peso por presion, disputa o posesion candidata en la ventana del evento.
3. Sumar peso por zona critica y respaldo Nivel 2.
4. Penalizar baja confianza.
5. Exportar `level3_highlights.csv` con `rank`, `score`, `confidence`, `reliability` y `reason`.

---

## 8.11 Narrativa deportiva Nivel 3

La narrativa Nivel 3 genera texto breve y conservador para highlights y cadenas candidatas.

### Salida

- `experiments/test_022_level3_advanced_events/level3_narrative.md`.

### Regla de lenguaje

La narrativa puede decir `highlight provisional`, `posesion candidata`, `presion/disputa candidata` o `secuencia compatible`, pero no debe afirmar goles, faltas, pases oficiales ni decisiones arbitrales sin evidencia suficiente.

---

## 8.12 Grafo de interaccion Nivel 3

El grafo de interaccion agrega aristas entre robots y balon cuando hay proximidad, posesion candidata, presion o disputa durante varios frames.

### Salidas

- `interaction_graph.json`.
- `interaction_edges.csv`.
- `interaction_graph.png`.

### Logica actual

1. Crear nodos por robot y balon.
2. Agregar aristas por tipo de interaccion.
3. Ponderar por duracion, distancia y confianza.
4. Usar el grafo para dashboard, visualizaciones y comparacion multi-clip.

---

# 9. Limitaciones

- Los eventos son heurísticos.
- La precisión depende de SAM 3 y del tracking.
- La posesión puede confundirse con proximidad.
- Los tiros pueden confundirse con despejes.
- Las colisiones pueden ser falsas por perspectiva.
- Las recuperaciones e intercepciones Nivel 2 dependen de continuidad de IDs y pueden fallar con oclusion.
- Los eventos Nivel 3 dependen de homografia aproximada, proximidad y equipos frecuentemente neutrales.
- Las cadenas de pase Nivel 3 siguen siendo dudosas si no hay asignacion confiable de equipo.
- Los highlights Nivel 3 son candidatos rankeados para demo y revision, no hechos deportivos oficiales.
- La confiabilidad `confiable`, `provisional` o `descartado` no reemplaza validacion visual humana.
- No se debe afirmar precisión final sin validación humana.

---

# 10. Regla de actualización

Si se cambia una regla de evento:

1. Actualizar este documento.
2. Actualizar configuración YAML.
3. Registrar razón del cambio.
4. Ejecutar nueva prueba.
5. Guardar evidencia en `experiments/`.
