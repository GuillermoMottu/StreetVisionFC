# Decisiones Tecnicas — Playback Vivo Y Analisis Online

Registro de decisiones tomadas durante el desarrollo de la extension Post-Nivel 3 (Actividades 21-35).

---

## Decision 1: Playback Precomputado Como Primer Paso

**Contexto:** Al iniciar la extension, existian tres opciones: (a) implementar inferencia online directamente con SAM 3, (b) construir un simulador de streaming, o (c) comenzar con artefactos precomputados existentes como primera demo funcional.

**Decision:** Comenzar con modo `playback_precomputado`.

**Razones:**

- Reutiliza artefactos ya validados del pipeline batch: `level3_tracks.csv`, `level3_events.json`, `level3_highlights.csv` y calibracion espacial.
- No introduce riesgo de latencia o bloqueo de UI en la primera demo.
- Permite validar toda la capa visual (canvas, overlays, trails, mini-mapa) sin depender de GPU.
- Reduce el tiempo de feedback: la experiencia funciona en cualquier equipo con Python.
- Deja la arquitectura lista para recibir datos incrementales sin cambiar la interfaz de datos.

**Consecuencias:**

- El modo precomputado queda como fallback para todos los modos mas avanzados.
- Los datos normalizados (`live_tracks.csv`, `live_events.json`) son compatibles con el modo streaming.
- La frontera entre precomputado y online queda definida por `IncrementalTrackerSession` y `StreamEventDetector`.

---

## Decision 2: SSE Sobre WebSocket Para El Canal Backend/Frontend

**Contexto:** El canal de comunicacion backend→frontend podia implementarse con WebSockets (bidireccional, requiere upgrade HTTP) o con Server-Sent Events (unidireccional, HTTP nativo).

**Decision:** Usar SSE (`text/event-stream`) implementado sobre `http.server` de stdlib.

**Razones:**

- El flujo de datos es unidireccional: el backend envia overlays y el frontend solo consume.
- SSE funciona nativamente con `EventSource` en el navegador sin librerias adicionales.
- `http.server` de stdlib es suficiente para el caso de uso local; no se requiere `asyncio`, `websockets` ni frameworks externos.
- Menor complejidad de implementacion y menor superficie de fallo.
- Reconnect automatico del navegador ante caidas del servidor sin codigo adicional.

**Consecuencias:**

- El frontend no puede enviar comandos al backend por el mismo canal (aceptable: los controles de reproduccion son locales al navegador).
- La latencia de SSE en local es equivalente a WebSocket para el caso de uso.
- Cambiar a WebSocket en el futuro requiere agregar una libreria y modificar el manejador del servidor.

---

## Decision 3: Tres Modos De Inferencia Con Compuerta GPU

**Contexto:** Era necesario definir como el backend decide que tipo de analisis ejecutar y como se protege la estabilidad del sistema ante modos experimentales.

**Decision:** Tres modos con compuerta explicita para GPU.

| Modo | Descripcion | Compuerta |
|------|-------------|-----------|
| `precomputed` | Lookup de artefactos existentes | Sin restriccion |
| `lightweight_detector` | Detector ligero incremental sin SAM 3 | Sin restriccion (stride configurable) |
| `sam3_sampling` | SAM 3 cada N frames durante reproduccion | Requiere `--allow-gpu --gpu-profile` |

**Razones:**

- El modo `precomputed` debe estar disponible en cualquier equipo sin GPU.
- El modo `sam3_sampling` puede congelar la UI si se activa por error en un equipo sin GPU suficiente.
- La compuerta `--allow-gpu` hace explicita la decision de activar un modo costoso.
- El perfil `--gpu-profile msi_gpu` permite documentar en evidencia con que hardware se ejecuto el benchmark.

**Consecuencias:**

- El modo GPU nunca se activa por defecto ni por inferencia de entorno.
- Los modos `precomputed` y `lightweight_detector` son suficientes para demos sin laptop MSI.
- El benchmark de SAM 3 online queda fuera del flujo principal y se documenta por separado.

---

## Decision 4: Limitaciones De SAM 3 Online

**Contexto:** SAM 3 es la tecnologia de segmentacion base del pipeline. La pregunta era si podia usarse frame a frame durante reproduccion.

**Decision:** SAM 3 no se usa por cada frame en modo online. Solo se permite con stride/sampling y compuerta GPU explicita.

**Razones:**

- SAM 3 procesa un frame de video de futbol en 200-2000 ms en laptop MSI con RTX 4050 segun el tamano de entrada y el numero de objetos.
- Un video a 30 fps requiere un nuevo frame cada 33 ms; SAM 3 no puede cumplir esa restriccion en tiempo real.
- Intentar SAM 3 sin stride bloquea la UI del navegador o acumula backpressure hasta vaciamiento.
- La calidad de tracking con datos precomputados de Nivel 3 es superior a lo que un stride de SAM 3 puede producir en tiempo real.

**Consecuencias:**

- El modo `sam3_sampling` solo es util para benchmarks documentados, no para demos de reproduccion fluida.
- La inferencia online util se basa en `IncrementalTrackerSession` con detecciones precomputadas como entrada, no en SAM 3 en vivo.
- Si se necesita inferencia online de calidad, la arquitectura correcta es procesar offline el segmento pendiente y luego reproducirlo en modo precomputado.

**Frontera de hardware:**

- Laptop MSI con RTX 4050: unico equipo habilitado para pruebas SAM 3 online.
- Escritorio de desarrollo: modo precomputado, lightweight y revision de artefactos.

---

## Decision 5: Backpressure Y Degradacion Gradual

**Contexto:** Cuando el analisis online se atrasa respecto al video, habia que decidir entre (a) pausar el video para esperar, (b) saltar el analisis del frame, o (c) usar el ultimo overlay disponible.

**Decision:** Degradacion gradual con cuatro estados y politica de fallback explicita.

| Estado | Condicion | Accion |
|--------|-----------|--------|
| `live` | Lag <= 2 frames | Overlay sincronizado, sin cambios |
| `delayed` | Lag 3-7 frames | Usar ultimo overlay, reducir trails |
| `replaying_cache` | Lag > threshold | Usar overlay precomputado, omitir capas costosas |
| `analysis_paused` | Sin analisis por > 30 frames | Detener inferencia, solo precomputado |

**Razones:**

- El video nunca debe pausarse esperando analisis: la experiencia de reproduccion es la prioridad.
- El usuario prefiere ver un overlay ligeramente desactualizado que un video congelado.
- La reduccion gradual de capas (trails primero, luego debug, luego mini-mapa) preserva la informacion mas importante bajo carga.

**Consecuencias:**

- `PlaybackBackpressureEngine` implementa la cola acotada, el monitor y la politica de fallback.
- `skip_inference` y `reduce_layers` son flags binarios que el loop de frames consume en cada tick.
- El numero de frames consecutivos con latencia alta dispara `recommend_precomputed` para que el operador cambie de modo si lo considera necesario.
