# Alcance Playback Vivo Y Analisis Online

Este documento cierra la Actividad 21 de `docs/TODO_LIVE_PLAYBACK.md`. Define el alcance inicial para mostrar analisis sincronizado mientras un video local se reproduce, sin cambiar el cierre tecnico de Nivel 1, Nivel 2 ni Nivel 3.

## Contexto

FutBotMX ya cuenta con pipeline batch, tracking, eventos, visualizaciones Nivel 3, dashboard, reel local y reporte final. El siguiente paso propuesto es mejorar la experiencia de revision: ver el video en navegador local con overlays sincronizados por frame o timestamp.

Este trabajo es Post-Nivel 3. No se declara como streaming en tiempo real garantizado, arbitraje oficial, SaaS ni sistema comercial. La primera meta debe ser reproducible y ligera: playback con artefactos precomputados.

## Modos De Operacion

| Modo | Objetivo | Entrada principal | Procesamiento | Hardware recomendado | Uso esperado |
|---|---|---|---|---|---|
| `playback_precomputado` | Reproducir video local con overlays sincronizados. | Video local, `tracks.csv`, `events.json`, highlights y calibracion. | Lookup por frame/timestamp y render en canvas. | Escritorio o laptop. | Primer demo estable. |
| `streaming_simulado` | Emitir resultados durante playback como flujo local. | Artefactos ya calculados. | Backend envia mensajes por frame o timestamp. | Escritorio o laptop. | Probar canal backend/frontend sin inferencia pesada. |
| `online_parcial` | Procesar frames durante reproduccion con costo controlado. | Frames del video, detecciones precomputadas o detector ligero. | Loop vivo: frame, detecciones, tracker, eventos, overlay. | Laptop para pruebas con GPU; escritorio solo modo ligero. | Demo experimental con latencia medida. |
| `online_sam3` | Evaluar SAM 3 durante playback con sampling. | Frames del video y checkpoint local. | SAM 3 cada N frames, no cada frame por defecto. | Laptop MSI con RTX 4050. | Benchmark experimental, no primera meta. |

## Modo Recomendado Para Iniciar

El modo inicial debe ser `playback_precomputado`.

Razones:

- Reutiliza evidencia existente: tracks, eventos, highlights, mini-mapa y calibracion.
- No requiere inferencia SAM 3 nueva.
- Permite validar la parte mas visible para evaluadores: reproduccion con overlays sincronizados.
- Reduce riesgo de latencia y bloqueo de UI.
- Deja preparada la arquitectura visual para recibir datos por canal continuo despues.

## Limites Tecnicos

### SAM 3

- SAM 3 sigue siendo la tecnologia base para segmentacion de alta calidad.
- SAM 3 es el cuello de botella principal si se intenta inferencia durante reproduccion.
- El modo `online_sam3` no debe prometer analisis por cada frame.
- La estrategia aceptada para SAM 3 online es stride, sampling o precomputo.
- La laptop MSI es la maquina para pruebas SAM 3; el escritorio queda para desarrollo, playback, revision y documentacion.

### UI Y Video

- El reloj principal debe ser el video, no el analizador.
- La UI debe priorizar playback fluido sobre overlay perfecto.
- Si el analisis se atrasa, el frontend puede usar el ultimo overlay disponible, saltar frames o mostrar estado `delayed`.
- El overlay debe poder apagarse por capas para depuracion y rendimiento.
- El seek puede requerir limpiar trails y reiniciar estado incremental.

### Datos

- Los videos completos permanecen fuera de Git.
- El repositorio solo debe versionar datos ligeros: CSV, JSON, Markdown, PNG seleccionados, manifests y configuraciones.
- El modo precomputado debe aceptar formatos existentes antes de exigir un formato nuevo.
- La normalizacion formal de datos corresponde a la Actividad 22.

### Eventos

- Los eventos durante playback deben mostrarse como candidatos o provisionales salvo revision posterior.
- La deteccion streaming debe operar con ventanas moviles y puede corregir o descartar eventos.
- No se deben presentar decisiones como goles, faltas o arbitraje oficial.

## Presupuesto Inicial De Rendimiento

Estos valores son metas de arranque, no garantias:

| Modo | FPS objetivo de video | FPS objetivo de overlay/analisis | Latencia objetivo | Degradacion aceptada |
|---|---:|---:|---:|---|
| `playback_precomputado` | FPS nativo del video | 24-60 redraws/s segun navegador | Menos de 100 ms para lookup y dibujo local | Usar frame mas cercano si hay stride. |
| `streaming_simulado` | FPS nativo del video | 10-30 mensajes/s | Menos de 250 ms en canal local | Saltar mensajes antiguos. |
| `online_parcial` | FPS nativo del video | 5-15 frames procesados/s | Menos de 500 ms para overlay util | Backpressure, frame skip y ultimo resultado disponible. |
| `online_sam3` | FPS nativo del video | Medido por benchmark | Sin garantia inicial | Sampling agresivo o fallback precomputado. |

## Riesgos Principales

- Desfase entre `currentTime` del video y frames de artefactos.
- FPS nominal distinto al FPS real del archivo.
- Tracks con stride o frames faltantes.
- Cambios de ID al reconstruir tracking despues de seek.
- Eventos que cambian al pasar de batch completo a ventana movil.
- Carga del navegador al dibujar demasiadas capas.
- Rutas de videos locales no disponibles en otra maquina.
- Inferencia SAM 3 demasiado lenta para playback online continuo.

## No Objetivos

- No construir SaaS, login, multiusuario ni servidor remoto.
- No subir videos completos, checkpoints, frames masivos ni renders pesados a Git.
- No garantizar analisis en tiempo real con SAM 3 cada frame.
- No reemplazar el pipeline batch de alta calidad.
- No declarar arbitraje oficial ni decisiones reglamentarias exactas.

## Criterios De Salida De Actividad 21

- Los cuatro modos de operacion quedan definidos.
- Los limites tecnicos de SAM 3, UI, datos y eventos quedan documentados.
- Existe presupuesto inicial de FPS y latencia.
- El alcance queda declarado como Post-Nivel 3.
- La siguiente actividad recomendada es `Actividad 22 - Contrato De Datos Temporal`, seguida por `Actividad 23 - Reproductor Con Overlays Precomputados`.

## Decision Operativa

La ruta aprobada para continuar es:

1. Cerrar contrato de datos temporal.
2. Implementar playback precomputado.
3. Agregar sincronizador frame/timestamp.
4. Agregar backend local y canal continuo.
5. Evaluar online parcial.
6. Evaluar SAM 3 online solo con benchmark documentado en laptop MSI.
