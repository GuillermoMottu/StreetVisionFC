# TODO Playback Vivo Y Analisis Online

Este TODO define una extension Post-Nivel 3 para que FutBotMX pueda mostrar analisis sincronizado mientras un video se reproduce en navegador local.

El punto de partida recomendado es un reproductor con overlays precomputados. Despues se puede avanzar hacia streaming simulado y, finalmente, analisis online parcial. Esta extension no modifica el cierre tecnico de Nivel 1, Nivel 2 ni Nivel 3.

## Objetivo General

Crear una experiencia local donde el video se reproduzca con tracks, IDs, balon, eventos, posesion candidata, mini-mapa y highlights sincronizados por frame o timestamp. El sistema debe poder trabajar primero con artefactos precomputados y luego evolucionar hacia procesamiento incremental frame a frame.

## Regla De Trabajo

- [ ] Mantener esta extension como trabajo Post-Nivel 3.
- [ ] No comprometer el cierre ya logrado de Nivel 1, Nivel 2 ni Nivel 3.
- [ ] Mantener videos completos, checkpoints, frames masivos, mascaras masivas y renders pesados fuera de Git.
- [ ] Versionar solo evidencia ligera: codigo, configuracion, Markdown, CSV, JSON, PNG seleccionados y manifests.
- [ ] Usar lenguaje conservador: analisis aproximado, eventos candidatos, posesion candidata y highlights provisionales.
- [ ] Priorizar playback con datos precomputados antes de intentar inferencia online con SAM 3.
- [ ] Documentar claramente la frontera GPU: SAM 3 pesado en laptop MSI, desarrollo y revision ligera en escritorio.

## Fases Recomendadas

1. Playback sincronizado con artefactos precomputados.
2. Canal backend/frontend para emitir resultados durante reproduccion.
3. Motor online de frames con detecciones precomputadas.
4. Tracker incremental y eventos con ventanas moviles.
5. Inferencia online parcial con stride, sampling o detector ligero.

## Actividad 21 - Definir Alcance Del Modo Playback Vivo

### Objetivo

Convertir la idea en una extension experimental local, sin presentarla como producto SaaS, arbitraje oficial ni streaming en tiempo real garantizado.

### Documento de alcance

- [x] Alcance operativo registrado en `docs/LIVE_PLAYBACK_SCOPE.md`.

### Tarea 21.1 - Separar modos de operacion

- [x] Definir `playback_precomputado`: video local + overlays desde CSV/JSON existentes.
- [x] Definir `streaming_simulado`: backend emite resultados ya calculados como si llegaran frame a frame.
- [x] Definir `online_parcial`: backend procesa frames durante reproduccion con detecciones precomputadas o detector ligero.
- [x] Definir `online_sam3`: modo experimental GPU con stride/sampling, no cada frame por defecto.

### Tarea 21.2 - Definir limites tecnicos

- [x] Documentar que SAM 3 es el cuello de botella principal.
- [x] Documentar que la UI debe priorizar reproduccion fluida aunque el overlay llegue tarde.
- [x] Definir presupuesto inicial de latencia por frame.
- [x] Definir FPS objetivo para video y FPS objetivo para analisis.

### Criterio de aceptacion

- [x] Existe una descripcion clara de modos, riesgos y criterios de salida.
- [x] El alcance queda registrado como Post-Nivel 3.

## Actividad 22 - Contrato De Datos Temporal

### Objetivo

Estandarizar los datos que usaran frontend y backend para sincronizar overlays por frame o timestamp.

### Tarea 22.1 - Normalizar tracks

- [x] Definir columnas minimas para `live_tracks.csv`.
- [x] Incluir `clip_id`, `frame`, `timestamp_sec`, `track_id`, `class`, `x`, `y`, `w`, `h`, `center_x`, `center_y`, `team`, `confidence`.
- [x] Permitir columnas opcionales de Nivel 3: `x_norm`, `y_norm`, `zone`, `calibration_confidence`.
- [x] Documentar conversion desde `tracks.csv`, `tracks_level2.csv` o `level3_tracks.csv`.

### Tarea 22.2 - Normalizar eventos

- [x] Definir `live_events.json` con `event_id`, `label`, `start_frame`, `end_frame`, `start_time_sec`, `end_time_sec`, `confidence`, `status`.
- [x] Usar `status` con valores como `candidate`, `provisional`, `confirmed`, `discarded`.
- [x] Incluir referencias a tracks participantes cuando existan.
- [x] Mantener compatibilidad con `events.json`, `level2_events.json` y `level3_events.json`.

### Tarea 22.3 - Normalizar highlights y mini-mapa

- [x] Definir `live_highlights.csv` derivado de `level3_highlights.csv`.
- [x] Definir payload de mini-mapa por frame con coordenadas rectificadas o fallback.
- [x] Incluir confianza de calibracion.
- [x] Crear fixtures pequenos para pruebas de sincronizacion.

### Artefactos esperados

- [x] `docs/LIVE_PLAYBACK_DATA_CONTRACT.md`.
- [x] Fixtures ligeros en `tests/fixtures/live_playback/`.
- [x] Validadores unitarios de tracks, eventos y highlights.

### Criterio de aceptacion

- [x] Frontend y backend pueden leer los mismos datos sin depender de formatos internos dispersos.

## Actividad 23 - Reproductor Con Overlays Precomputados

### Objetivo

Crear la primera demo funcional: reproducir un video local y dibujar encima informacion ya calculada.

### Tarea 23.1 - Crear UI de reproduccion

- [x] Crear vista HTML local con elemento `<video>`.
- [x] Crear canvas superpuesto para dibujar overlays.
- [x] Ajustar canvas al tamano real del video.
- [x] Mantener relacion de aspecto sin deformar coordenadas.

### Tarea 23.2 - Dibujar capas de analisis

- [x] Dibujar cajas, centroides o mascaras ligeras cuando existan.
- [x] Dibujar IDs de robots.
- [x] Dibujar balon con estilo diferenciado.
- [x] Dibujar trails cortos por track.
- [x] Dibujar evento activo.
- [x] Dibujar posesion candidata.
- [x] Dibujar mini-mapa sincronizado.
- [x] Dibujar marcador de highlight cuando corresponda.

### Tarea 23.3 - Controles de capas

- [x] Agregar toggles para tracks, IDs, balon, trails, eventos, posesion, mini-mapa y debug.
- [x] Agregar selector de experimento/clip.
- [x] Agregar indicador de frame actual y timestamp.
- [x] Agregar estado de datos disponibles para el frame actual.

### Artefactos esperados

- [x] `scripts/run_live_playback_app.py`.
- [x] `src/futbotmx/live_playback.py`.
- [x] `experiments/test_039_live_playback/playback.html`.
- [x] `experiments/test_039_live_playback/config.yaml`.
- [x] `experiments/test_039_live_playback/live_playback_manifest.csv`.
- [x] `experiments/test_039_live_playback/summary.md`.

### Criterio de aceptacion

- [x] Un video local reproduce fluido con overlays sincronizados usando tracks y eventos precomputados.

## Actividad 24 - Sincronizador Frame/Timestamp

### Objetivo

Evitar desfases entre video y overlays, especialmente al pausar, hacer seek o cambiar velocidad de reproduccion.

### Tarea 24.1 - Metadatos de video

- [ ] Leer FPS, ancho, alto, duracion y total aproximado de frames.
- [ ] Guardar metadatos en manifest ligero.
- [ ] Definir conversion `currentTime -> frame`.
- [ ] Documentar diferencias entre FPS nominal y frames reales si aparecen.

### Tarea 24.2 - Resolver frame visible

- [ ] Buscar el frame exacto si existe en datos.
- [ ] Usar frame anterior mas cercano si los datos vienen con stride.
- [ ] Interpolar centroides solo cuando el modo lo permita.
- [ ] Marcar visualmente frames sin datos.

### Tarea 24.3 - Manejar controles de reproduccion

- [ ] Soportar play, pause, seek y replay.
- [ ] Recalcular overlay inmediatamente despues de un seek.
- [ ] Limpiar trails cuando el salto temporal sea grande.
- [ ] Mantener sincronizacion al cambiar velocidad.

### Criterio de aceptacion

- [ ] El overlay no queda desfasado despues de pausar, avanzar o regresar en el video.

## Actividad 25 - Backend Local De Playback

### Objetivo

Servir video, artefactos y estado local desde Python sin introducir dependencias innecesarias.

### Tarea 25.1 - Servir artefactos

- [ ] Exponer endpoint local para manifest de experimentos.
- [ ] Exponer endpoint local para tracks.
- [ ] Exponer endpoint local para eventos.
- [ ] Exponer endpoint local para highlights.
- [ ] Exponer endpoint local para calibracion y mini-mapa.

### Tarea 25.2 - Servir video local

- [ ] Permitir seleccionar video local por configuracion.
- [ ] Proteger rutas para evitar leer fuera de ubicaciones permitidas.
- [ ] Soportar videos fuera de Git.
- [ ] Documentar cuando el video no este disponible en otro equipo.

### Tarea 25.3 - Integrar con app local existente

- [ ] Reusar patrones de `src/futbotmx/local_app.py` cuando aplique.
- [ ] Mantener backend con libreria estandar de Python si es suficiente.
- [ ] Evitar login, servidor remoto o arquitectura SaaS.

### Criterio de aceptacion

- [ ] La app local abre el reproductor y carga datos desde endpoints locales reproducibles.

## Actividad 26 - Canal Backend/Frontend

### Objetivo

Preparar un canal continuo para emitir resultados durante reproduccion.

### Tarea 26.1 - Definir mensajes

- [ ] Definir mensaje `session_status`.
- [ ] Definir mensaje `frame_result`.
- [ ] Definir mensaje `event_update`.
- [ ] Definir mensaje `latency_metrics`.
- [ ] Definir mensaje `warning`.

### Tarea 26.2 - Implementar transporte

- [ ] Evaluar SSE para flujo unidireccional simple.
- [ ] Evaluar WebSocket si se requieren comandos bidireccionales.
- [ ] Implementar primero la opcion mas simple que cubra playback local.
- [ ] Agregar reconexion basica del frontend.

### Tarea 26.3 - Registrar sesion

- [ ] Guardar log ligero de mensajes emitidos.
- [ ] Guardar metricas de latencia.
- [ ] Guardar resumen de errores o warnings.

### Criterio de aceptacion

- [ ] El frontend puede recibir resultados frame a frame sin recargar la pagina.

## Actividad 27 - Motor Online De Frames

### Objetivo

Crear un loop vivo que procese o recupere datos por frame mientras el video avanza.

### Tarea 27.1 - Loop base

- [ ] Leer frame actual o frame solicitado.
- [ ] Recuperar detecciones precomputadas si existen.
- [ ] Ejecutar inferencia si el modo online esta habilitado.
- [ ] Actualizar tracker.
- [ ] Actualizar eventos.
- [ ] Emitir overlay.

### Tarea 27.2 - Control de ejecucion

- [ ] Soportar pausa y resume.
- [ ] Soportar seek con reinicio de estado cuando sea necesario.
- [ ] Soportar stop limpio.
- [ ] Soportar salto de frames si el procesamiento se atrasa.

### Tarea 27.3 - Medicion de rendimiento

- [ ] Medir tiempo de lectura de frame.
- [ ] Medir tiempo de deteccion.
- [ ] Medir tiempo de tracking.
- [ ] Medir tiempo de eventos.
- [ ] Medir tiempo total hasta overlay.

### Criterio de aceptacion

- [ ] Existe un loop que emite resultados parciales sin esperar a generar CSV final.

## Actividad 28 - Modos De Inferencia

### Objetivo

Resolver el cuello de botella de SAM 3 mediante modos configurables.

### Tarea 28.1 - Modo precomputado

- [ ] Cargar detecciones SAM 3 ya generadas.
- [ ] Sincronizar detecciones por frame.
- [ ] Permitir stride y frame mas cercano.
- [ ] Marcar el modo como recomendado para demo fluida.

### Tarea 28.2 - Modo SAM 3 con sampling

- [ ] Ejecutar SAM 3 solo cada N frames.
- [ ] Reusar o interpolar resultados entre frames.
- [ ] Ejecutar solo en laptop MSI con GPU cuando aplique.
- [ ] Registrar latencia y memoria GPU si esta disponible.

### Tarea 28.3 - Modo detector ligero

- [ ] Evaluar detector mas rapido para robots y balon.
- [ ] Usar SAM 3 offline para resultados de alta calidad.
- [ ] Documentar degradacion de calidad.
- [ ] Mantener compatibilidad con tracker incremental.

### Criterio de aceptacion

- [ ] La app puede elegir modo por configuracion y documenta sus limitaciones.

## Actividad 29 - Tracker Incremental

### Objetivo

Usar ByteTrack/tracking como proceso vivo que mantiene estado en memoria.

### Tarea 29.1 - Wrapper de tracker vivo

- [ ] Crear inicializador de tracker por sesion.
- [ ] Recibir detecciones frame a frame.
- [ ] Emitir tracks activos por frame.
- [ ] Mantener tracks perdidos durante una ventana configurable.

### Tarea 29.2 - Estado y reset

- [ ] Reiniciar tracker cuando se hace seek hacia atras.
- [ ] Permitir reconstruir estado desde frame inicial hasta frame actual si es necesario.
- [ ] Exportar snapshots parciales para depuracion.
- [ ] Comparar contra tracks batch cuando existan.

### Tarea 29.3 - Salida incremental

- [ ] Emitir `live_tracks.jsonl`.
- [ ] Exportar CSV parcial al terminar sesion.
- [ ] Incluir confianza y estado del track.

### Criterio de aceptacion

- [ ] El tracker produce IDs continuos sin esperar al archivo `tracks.csv` final.

## Actividad 30 - Detector De Eventos En Streaming

### Objetivo

Adaptar reglas de eventos para operar con ventanas temporales moviles.

### Tarea 30.1 - Buffers temporales

- [ ] Mantener ultimos N frames de tracks.
- [ ] Mantener historial reciente del balon.
- [ ] Mantener historial de posesion candidata.
- [ ] Mantener historial de proximidades robot-balon y robot-robot.

### Tarea 30.2 - Eventos candidatos

- [ ] Detectar posesion candidata.
- [ ] Detectar tiro aproximado.
- [ ] Detectar pase simple o interaccion.
- [ ] Detectar colision o disputa.
- [ ] Detectar highlight provisional por velocidad, zona o cambio de posesion.

### Tarea 30.3 - Ciclo de vida del evento

- [ ] Crear evento candidato.
- [ ] Actualizar evento si llegan nuevos frames compatibles.
- [ ] Confirmar evento si cumple duracion/confianza minima.
- [ ] Descartar evento si se contradice con frames nuevos.
- [ ] Exportar `stream_events.jsonl`.

### Criterio de aceptacion

- [ ] Los eventos aparecen durante la reproduccion con estado provisional y se actualizan sin esperar el analisis batch.

## Actividad 31 - Mini-Mapa Y Metricas Vivas

### Objetivo

Mostrar lectura tactica aproximada durante playback.

### Tarea 31.1 - Mini-mapa sincronizado

- [ ] Reusar calibracion manual cuando exista.
- [ ] Reusar homografia aproximada o fallback.
- [ ] Dibujar robots y balon por frame.
- [ ] Dibujar trails cortos en coordenadas de cancha.

### Tarea 31.2 - Metricas vivas

- [ ] Actualizar posesion candidata por equipo cuando exista asignacion.
- [ ] Actualizar zona de actividad.
- [ ] Actualizar velocidad aproximada del balon.
- [ ] Mostrar confianza de calibracion y tracking.

### Criterio de aceptacion

- [ ] El mini-mapa se actualiza junto con el video y oculta datos no confiables cuando falte calibracion.

## Actividad 32 - Backpressure Y Degradacion

### Objetivo

Evitar que el video o la UI se congelen cuando el analisis se atrasa.

### Tarea 32.1 - Cola de frames

- [ ] Definir tamano maximo de cola.
- [ ] Descartar frames antiguos si ya no sirven para la vista actual.
- [ ] Priorizar frame actual sobre frames atrasados.
- [ ] Separar reloj de video y reloj de analisis.

### Tarea 32.2 - Estados de degradacion

- [ ] Mostrar `live` cuando el overlay esta sincronizado.
- [ ] Mostrar `delayed` cuando el overlay llega tarde.
- [ ] Mostrar `replaying_cache` cuando se usan datos precomputados.
- [ ] Mostrar `analysis_paused` cuando el motor se detiene.

### Tarea 32.3 - Politica de fallback

- [ ] Usar ultimo overlay disponible si falta el frame actual.
- [ ] Saltar inferencia pesada si se acumula latencia.
- [ ] Reducir capas visuales si la UI baja rendimiento.
- [ ] Cambiar a modo precomputado si online no cumple presupuesto.

### Criterio de aceptacion

- [ ] La reproduccion del video sigue fluida aunque el analisis llegue con retraso.

## Actividad 33 - Validacion Tecnica

### Objetivo

Medir si la experiencia funciona realmente durante reproduccion.

### Tarea 33.1 - Clips de prueba

- [ ] Usar `video_595` como clip principal.
- [ ] Usar `video_667` como clip secundario.
- [ ] Mantener `video_480` como diagnostico de balon si aplica.
- [ ] Crear configuraciones ligeras por clip.

### Tarea 33.2 - Metricas de runtime

- [ ] Medir FPS de video.
- [ ] Medir FPS de analisis.
- [ ] Medir latencia media.
- [ ] Medir latencia p95.
- [ ] Medir frames saltados.
- [ ] Medir eventos emitidos y actualizados.

### Tarea 33.3 - Comparacion contra batch

- [ ] Comparar tracks streaming contra `tracks.csv` o `level3_tracks.csv`.
- [ ] Comparar eventos streaming contra `events.json` o `level3_events.json`.
- [ ] Clasificar diferencias como aceptables, degradadas o fallidas.
- [ ] Documentar causas de errores.

### Artefactos esperados

- [ ] `experiments/test_040_live_playback_validation/config.yaml`.
- [ ] `experiments/test_040_live_playback_validation/runtime_metrics.csv`.
- [ ] `experiments/test_040_live_playback_validation/event_comparison.csv`.
- [ ] `experiments/test_040_live_playback_validation/summary.md`.
- [ ] `experiments/test_040_live_playback_validation/live_validation_manifest.csv`.

### Criterio de aceptacion

- [ ] Existe evidencia ligera de latencia, sincronizacion y degradaciones por clip.

## Actividad 34 - Panel De Depuracion

### Objetivo

Facilitar el ajuste de sincronizacion, reglas de eventos y rendimiento.

### Tarea 34.1 - Indicadores visibles

- [ ] Mostrar frame actual.
- [ ] Mostrar timestamp actual.
- [ ] Mostrar modo de inferencia.
- [ ] Mostrar estado del canal.
- [ ] Mostrar latencia actual.
- [ ] Mostrar tamano de cola.
- [ ] Mostrar numero de tracks activos.
- [ ] Mostrar evento activo.

### Tarea 34.2 - Herramientas de revision

- [ ] Permitir descargar logs de sesion.
- [ ] Permitir descargar `live_tracks.jsonl`.
- [ ] Permitir descargar `stream_events.jsonl`.
- [ ] Permitir activar/desactivar overlay debug.

### Criterio de aceptacion

- [ ] Una falla de sincronizacion o latencia puede diagnosticarse desde el panel local.

## Actividad 35 - Documentacion Y Cierre Experimental

### Objetivo

Dejar la extension reproducible, acotada y documentada.

### Tarea 35.1 - Documentar uso

- [ ] Agregar comandos para arrancar app local.
- [ ] Agregar estructura esperada de artefactos.
- [ ] Agregar ejemplos con datos precomputados.
- [ ] Agregar notas de hardware y rendimiento.

### Tarea 35.2 - Documentar decisiones

- [ ] Registrar decision tecnica de usar playback precomputado como primer paso.
- [ ] Registrar decision sobre SSE o WebSocket.
- [ ] Registrar decision sobre modos de inferencia.
- [ ] Registrar limitaciones de SAM 3 online.

### Tarea 35.3 - Cierre

- [ ] Crear resumen experimental.
- [ ] Crear manifest de artefactos ligeros.
- [ ] Registrar pruebas ejecutadas.
- [ ] Registrar riesgos pendientes.

### Criterio de aceptacion

- [ ] La extension tiene instrucciones claras y evidencia ligera sin agregar archivos pesados a Git.

## Criterio De Exito Inicial

La primera version se considera exitosa cuando un video local reproduce fluido y muestra tracks, balon, IDs, eventos, posesion candidata, highlights y mini-mapa sincronizados usando artefactos existentes como `tracks.csv`, `events.json` y `level3_highlights.csv`.

## Prioridad Recomendada

1. Implementar `Actividad 23 - Reproductor Con Overlays Precomputados`.
2. Implementar `Actividad 24 - Sincronizador Frame/Timestamp`.
3. Implementar `Actividad 25 - Backend Local De Playback`.
4. Implementar `Actividad 26 - Canal Backend/Frontend`.
5. Implementar `Actividad 29 - Tracker Incremental`.
6. Implementar `Actividad 30 - Detector De Eventos En Streaming`.
7. Evaluar `Actividad 28 - Modos De Inferencia` solo despues de tener playback y streaming simulado funcionando.
