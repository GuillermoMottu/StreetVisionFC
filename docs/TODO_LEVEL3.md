# TODO Nivel 3

Nivel 3 esta iniciado de forma controlada desde la Actividad 0. Este TODO convierte el gate posterior al cierre de Nivel 2 en una lista operativa para completar la extension avanzada sin romper la entrega principal.

Punto de partida:

- Nivel 2 cerrado en `experiments/test_017_level2_closure/`.
- Gate Nivel 2 con `8 pass`, `0 fail`.
- Nivel 3 iniciado con decision formal `DEC-012`.
- Recomendacion tecnica pendiente: rectificacion/homografia como mejora de Nivel 3.

Meta de Nivel 3:

Generar una demo destacada con analisis tactico aproximado, visualizaciones avanzadas, highlights, narrativa deportiva, dashboard ligero y reel final, manteniendo reproducibilidad desde GitHub y dejando archivos pesados fuera del repositorio.

## Regla De Trabajo

- [ ] No comprometer el cierre ya logrado de Nivel 1 y Nivel 2.
- [ ] Mantener videos completos, checkpoints, frames masivos, mascaras masivas y renders pesados fuera de Git.
- [ ] Versionar solo evidencia ligera: CSV, JSON, Markdown, PNG seleccionados, manifests y configuraciones.
- [ ] Crear una carpeta de experimento por bloque nuevo.
- [ ] Guardar siempre `config.yaml`, `summary.md` y, cuando aplique, `*_manifest.csv`.
- [ ] Mantener Nivel 3 como demo avanzada, no como SaaS, streaming en tiempo real ni arbitraje completo.
- [ ] Preferir calculos sobre `tracks_level2.csv`, `level2_events.json` y metricas existentes antes de ejecutar inferencia pesada nueva.

## Estado De Desbloqueo

- [x] Nivel 2 documentado con resultados.
- [x] Eventos intermedios funcionando con evidencia.
- [x] Visualizaciones intermedias generadas.
- [x] Pipeline reproducible desde GitHub.
- [x] Gate de cierre Nivel 2 sin fallos.
- [x] Registrar decision formal de inicio de Nivel 3 en `FutBotMX_documentacion_markdown/DECISIONS.md`.
- [x] Elegir clip principal para demo Nivel 3: `video_595`.
- [x] Elegir clips secundarios para validacion multi-clip: `video_667`; diagnostico: `video_480`.
- [x] Definir presupuesto de tiempo para no afectar entrega final.

## Actividad 0 - Gate De Inicio Y Alcance

### Objetivo

Confirmar que Nivel 3 se puede iniciar con alcance controlado y evidencia suficiente de Nivel 2.

### Tarea 0.1 - Formalizar decision de inicio

- [x] Crear decision `DEC-012 - Inicio controlado Nivel 3`.
- [x] Declarar que Nivel 3 se inicia solo como extension avanzada.
- [x] Registrar riesgos: homografia aproximada, identidad de equipos, oclusiones, clips pesados fuera de Git.
- [x] Registrar criterio de salida: demo avanzada reproducible con evidencia ligera.

### Tarea 0.2 - Definir clips de trabajo

- [x] Seleccionar clip principal entre `video_595`, `video_667` o `video_836`: `video_595`.
- [x] Seleccionar al menos un clip secundario para validacion cruzada: `video_667`.
- [x] Mantener `video_480` como diagnostico si el balon sigue siendo inestable.
- [x] Documentar motivos de seleccion: visibilidad del campo, estabilidad de tracks, presencia de eventos.

### Tarea 0.3 - Crear gate de readiness Nivel 3

- [x] Implementar `scripts/check_level3_readiness.py`.
- [x] Validar existencia de `experiments/test_017_level2_closure/summary.md`.
- [x] Validar `LEVEL2_CLOSURE_SUMMARY.md` con Nivel 2 cerrado.
- [x] Validar que existan tracks y eventos de al menos dos clips candidatos.
- [x] Validar que no haya archivos pesados versionados.
- [x] Exportar resultados a `experiments/test_018_level3_readiness/readiness_checks.csv`.
- [x] Crear `experiments/test_018_level3_readiness/summary.md`.

### Criterio de aceptacion

- [x] `scripts/check_level3_readiness.py` termina con `0 fail`.
- [x] `summary.md` declara Nivel 3 desbloqueado para implementacion controlada.

## Actividad 1 - Contrato De Datos Nivel 3

### Objetivo

Definir los formatos que usaran metricas tacticas, eventos avanzados, visualizaciones, dashboard y reel.

### Tarea 1.1 - Auditar datos heredados de Nivel 2

- [x] Revisar columnas de `tracks_level2.csv`.
- [x] Revisar estructura de `level2_events.json`.
- [x] Revisar `level2_metrics.csv` y `level2_metrics.json`.
- [x] Identificar campos faltantes para Nivel 3: equipo, coordenadas rectificadas, zona, confianza, frame inicial/final.
- [x] Documentar limitaciones detectadas en `experiments/test_019_level3_data_contract/summary.md`.

### Tarea 1.2 - Definir esquemas de salida

- [x] Definir `level3_tracks.csv` con coordenadas originales y rectificadas.
- [x] Definir `level3_metrics.csv` para metricas tacticas agregadas.
- [x] Definir `level3_metrics.json` para resumen legible.
- [x] Definir `level3_events.json` para cadenas de pases, highlights e interacciones.
- [x] Definir `level3_highlights.csv` con ranking de jugadas.
- [x] Definir `level3_narrative.md` con narrativa generada por reglas.
- [x] Definir `level3_visualization_manifest.csv` con PNG/GIF/video local asociado.

### Tarea 1.3 - Crear modulos base

- [x] Crear paquete `src/futbotmx/level3/` si el codigo crece mas alla de un script.
- [x] Separar modelos de datos, metricas tacticas, eventos avanzados y visualizaciones.
- [x] Reutilizar lectores existentes de tracks y eventos.
- [x] Agregar pruebas unitarias para validacion de esquemas.

### Criterio de aceptacion

- [x] Los artefactos Nivel 3 tienen nombres, columnas y campos documentados.
- [x] Las pruebas cubren lectura/escritura de los nuevos formatos.

## Actividad 2 - Rectificacion Espacial Y Mini-Mapa

### Objetivo

Convertir posiciones de camara a coordenadas aproximadas de cancha para habilitar Voronoi, control espacial, mini-mapa y grafo tactico.

### Tarea 2.1 - Definir modelo de cancha

- [x] Crear representacion normalizada de cancha con ejes `x_norm`, `y_norm`.
- [x] Definir dimensiones relativas de campo, porterias y zonas tacticas.
- [x] Definir sistema de coordenadas consistente con `zone_axis` de Nivel 2.
- [x] Documentar convencion de origen, direccion y unidades.

### Tarea 2.2 - Calibrar homografia aproximada

- [x] Crear `field_calibration.json` con puntos de referencia por clip.
- [x] Permitir calibracion manual por cuatro esquinas si la deteccion automatica no es confiable.
- [x] Implementar transformacion de puntos de imagen a cancha.
- [x] Implementar fallback sin homografia para clips donde no se vea suficiente campo.
- [x] Registrar confianza de calibracion por clip.

### Tarea 2.3 - Generar tracks rectificados

- [x] Leer `tracks_level2.csv`.
- [x] Calcular centroides rectificados para robots y balon.
- [x] Exportar `level3_tracks.csv`.
- [x] Conservar columnas originales para trazabilidad.
- [x] Marcar filas con transformacion no confiable.

### Tarea 2.4 - Validar visualmente la rectificacion

- [x] Crear mini-mapa base `minimap_base.png`.
- [x] Dibujar trayectorias rectificadas sobre mini-mapa.
- [x] Comparar contra overlay original en frames seleccionados.
- [x] Crear capturas ligeras de validacion.
- [x] Documentar errores visuales y supuestos.

### Artefactos esperados

- [x] `experiments/test_020_level3_spatial_model/config.yaml`.
- [x] `experiments/test_020_level3_spatial_model/field_calibration.json`.
- [x] `experiments/test_020_level3_spatial_model/level3_tracks.csv`.
- [x] `experiments/test_020_level3_spatial_model/minimap_tracks.png`.
- [x] `experiments/test_020_level3_spatial_model/summary.md`.

### Criterio de aceptacion

- [x] Al menos un clip principal tiene tracks rectificados utilizables.
- [x] La transformacion conserva IDs, frames y clases.
- [x] El mini-mapa no contradice visualmente el movimiento observado.

## Actividad 3 - Metricas Tacticas Avanzadas

### Objetivo

Agregar analisis tactico aproximado basado en espacio, proximidad e interacciones entre robots.

### Tarea 3.1 - Calcular control espacial aproximado

- [x] Implementar control por proximidad usando grilla de cancha.
- [x] Asignar cada celda al robot mas cercano.
- [x] Separar control por equipo cuando exista asignacion de equipo.
- [x] Crear fallback por robot individual cuando no exista equipo confiable.
- [x] Exportar porcentaje de control por frame y agregado por clip.

### Tarea 3.2 - Calcular Voronoi tactico

- [x] Generar regiones tipo Voronoi sobre coordenadas rectificadas.
- [x] Recortar regiones a limites de cancha.
- [x] Ignorar robots con tracking no confiable.
- [x] Guardar frames representativos para eventos importantes.
- [x] Comparar resultado contra grilla de control espacial.

### Tarea 3.3 - Medir presion e interaccion

- [x] Calcular distancia robot-balon rectificada.
- [x] Calcular distancia entre robots cercanos.
- [x] Detectar presion sobre poseedor del balon.
- [x] Detectar clusters de robots en disputa.
- [x] Exportar `interaction_metrics.csv`.

### Tarea 3.4 - Construir grafo de interaccion

- [x] Crear nodos por robot y balon.
- [x] Crear aristas por proximidad, disputa, posesion o pase.
- [x] Ponderar aristas por duracion/confianza.
- [x] Exportar `interaction_graph.json`.
- [x] Exportar tabla `interaction_edges.csv`.

### Artefactos esperados

- [x] `experiments/test_021_level3_tactical_metrics/level3_metrics.csv`.
- [x] `experiments/test_021_level3_tactical_metrics/level3_metrics.json`.
- [x] `experiments/test_021_level3_tactical_metrics/interaction_metrics.csv`.
- [x] `experiments/test_021_level3_tactical_metrics/interaction_graph.json`.
- [x] `experiments/test_021_level3_tactical_metrics/summary.md`.
- [x] `experiments/test_021_level3_tactical_metrics/spatial_control.csv`.
- [x] `experiments/test_021_level3_tactical_metrics/voronoi_frames.csv`.
- [x] `experiments/test_021_level3_tactical_metrics/interaction_edges.csv`.

### Criterio de aceptacion

- [x] Las metricas tacticas se calculan sin depender de video pesado.
- [x] Los resultados son comparables entre al menos dos clips.
- [x] Cada metrica indica supuestos y nivel de confianza.

## Actividad 4 - Eventos Avanzados Nivel 3

### Objetivo

Detectar eventos de mayor valor narrativo: cadenas de pases, highlights avanzados, jugadas de presion y grafo de interaccion.

### Tarea 4.1 - Cadenas de pases

- [x] Reutilizar segmentos de posesion de Nivel 2.
- [x] Detectar cambios de posesion entre robots del mismo equipo.
- [x] Agrupar pases consecutivos en cadenas.
- [x] Registrar inicio, fin, robots involucrados, frames y confianza.
- [x] Marcar cadenas dudosas cuando falte equipo o el balon tenga tracking inestable.

### Tarea 4.2 - Highlights avanzados

- [x] Crear score de highlight por velocidad del balon.
- [x] Sumar peso por cambio de posesion.
- [x] Sumar peso por cercania a porteria o zona critica.
- [x] Sumar peso por presion/interaccion entre robots.
- [x] Penalizar eventos con baja confianza de tracking.
- [x] Exportar ranking en `level3_highlights.csv`.

### Tarea 4.3 - Narrativa deportiva

- [x] Crear reglas de texto para jugadas destacadas.
- [x] Generar frases por evento con timestamp/frame.
- [x] Indicar motivo del highlight: pase, recuperacion, presion, tiro aproximado, actividad en zona.
- [x] Evitar afirmar goles o reglas oficiales si no hay evidencia suficiente.
- [x] Exportar `level3_narrative.md`.

### Tarea 4.4 - Overlays de validacion de eventos

- [x] Crear PNG por highlight top.
- [x] Incluir ID de robots, balon, trayectoria corta y etiqueta del evento.
- [x] Incluir confianza del evento.
- [x] Crear `overlay_validation.csv`.

### Artefactos esperados

- [x] `experiments/test_022_level3_advanced_events/level3_events.json`.
- [x] `experiments/test_022_level3_advanced_events/level3_highlights.csv`.
- [x] `experiments/test_022_level3_advanced_events/level3_narrative.md`.
- [x] `experiments/test_022_level3_advanced_events/overlay_validation.csv`.
- [x] `experiments/test_022_level3_advanced_events/summary.md`.
- [x] `experiments/test_022_level3_advanced_events/overlay_highlight_*.png`.

### Criterio de aceptacion

- [x] Hay al menos tres highlights rankeados en el clip principal o se documenta por que no existen.
- [x] Cada evento tiene confianza y explicacion.
- [x] La narrativa no sobrepromete precision no demostrada.

## Actividad 5 - Visualizaciones Avanzadas

### Objetivo

Crear visualizaciones que hagan visible el valor de Nivel 3: Voronoi, grafo, mini-mapa, highlights y tablero tactico.

### Tarea 5.1 - Visualizacion Voronoi

- [x] Crear script `scripts/run_level3_visualizations.py`.
- [x] Renderizar Voronoi sobre mini-mapa.
- [x] Renderizar Voronoi sobre frame original si la calibracion lo permite.
- [x] Exportar imagen por highlight relevante.
- [x] Documentar limitaciones por perspectiva.

### Tarea 5.2 - Visualizacion de grafo de interaccion

- [x] Renderizar nodos de robots y balon.
- [x] Dibujar aristas con grosor segun duracion o frecuencia.
- [x] Diferenciar posesion, disputa y proximidad.
- [x] Exportar `interaction_graph.png`.

### Tarea 5.3 - Mini-mapa animable o secuencial

- [x] Crear mini-mapa con trails de robots y balon.
- [x] Marcar zonas de actividad.
- [x] Marcar evento actual cuando exista.
- [x] Exportar PNG ligeros por frames clave.
- [x] Si se genera GIF, mantenerlo pequeno o dejarlo fuera de Git con manifest.

### Tarea 5.4 - Storyboard de highlights

- [x] Crear una lamina por highlight con mini-mapa, frame original y texto corto.
- [x] Exportar `highlight_storyboard.png`.
- [x] Crear `highlight_storyboard_manifest.csv`.

### Artefactos esperados

- [x] `experiments/test_023_level3_visualizations/config.yaml`.
- [x] `experiments/test_023_level3_visualizations/voronoi_frame_*.png`.
- [x] `experiments/test_023_level3_visualizations/voronoi_original_frame_*.png`.
- [x] `experiments/test_023_level3_visualizations/interaction_graph.png`.
- [x] `experiments/test_023_level3_visualizations/minimap_highlight_*.png`.
- [x] `experiments/test_023_level3_visualizations/highlight_storyboard.png`.
- [x] `experiments/test_023_level3_visualizations/highlight_storyboard_manifest.csv`.
- [x] `experiments/test_023_level3_visualizations/visualization_manifest.csv`.
- [x] `experiments/test_023_level3_visualizations/summary.md`.

### Criterio de aceptacion

- [x] Las visualizaciones son legibles como capturas estaticas.
- [x] Cada imagen esta respaldada por datos CSV/JSON.
- [x] No se versionan renders pesados.

## Actividad 6 - Dashboard Ligero Nivel 3

### Objetivo

Crear un dashboard local o estatico que concentre metricas, eventos, highlights y visualizaciones avanzadas para presentacion.

### Tarea 6.1 - Definir formato del dashboard

- [x] Decidir si sera HTML estatico, Markdown enriquecido o app ligera local.
- [x] Evitar arquitectura SaaS, login, backend complejo o dependencias innecesarias.
- [x] Definir secciones: resumen, metricas, timeline, highlights, visualizaciones, evidencia.

### Tarea 6.2 - Construir resumen visual

- [x] Mostrar score de highlights.
- [x] Mostrar posesion y control espacial.
- [x] Mostrar distancia/velocidad clave.
- [x] Mostrar numero de interacciones y cadenas de pases.
- [x] Mostrar clip principal y clips secundarios analizados.

### Tarea 6.3 - Integrar assets

- [x] Incluir mini-mapa.
- [x] Incluir Voronoi.
- [x] Incluir grafo de interaccion.
- [x] Incluir storyboard de highlights.
- [x] Incluir links relativos a CSV/JSON/Markdown de evidencia.

### Tarea 6.4 - Empaquetar dashboard

- [x] Crear `experiments/test_024_level3_dashboard/`.
- [x] Crear `dashboard_manifest.csv`.
- [x] Crear `summary.md`.
- [x] Documentar comando de generacion.

### Criterio de aceptacion

- [x] El dashboard se puede abrir localmente sin depender de archivos pesados versionados.
- [x] El dashboard explica Nivel 3 con evidencia visual y metrica.

## Actividad 7 - Reel Final Y Demo De Presentacion

### Objetivo

Preparar material final para mostrar el resultado avanzado de FutBotMX de forma clara y convincente.

### Tarea 7.1 - Seleccionar momentos del reel

- [x] Usar `level3_highlights.csv` para elegir momentos.
- [x] Elegir entre tres y cinco segmentos cortos.
- [x] Priorizar jugadas con buen tracking y visualizacion clara.
- [x] Documentar frames/timestamps seleccionados.

### Tarea 7.2 - Crear overlay narrativo

- [x] Mostrar IDs y trails.
- [x] Mostrar evento actual.
- [x] Mostrar mini-mapa o indicador tactico cuando sea legible.
- [x] Mostrar texto narrativo breve por highlight.
- [x] Evitar saturar el frame con informacion.

### Tarea 7.3 - Generar reel local

- [x] Crear script o comando documentado para renderizar reel.
- [x] Mantener MP4 pesado fuera de Git.
- [x] Exportar thumbnails ligeros.
- [x] Exportar `reel_manifest.csv` con rutas locales o descripcion de archivos no versionados.

### Tarea 7.4 - Crear paquete de demo

- [x] Crear `experiments/test_025_level3_reel/summary.md`.
- [x] Incluir capturas ligeras del reel.
- [x] Incluir descripcion de narrativa.
- [x] Incluir comandos para regenerar el reel.

### Criterio de aceptacion

- [x] Existe una demo final local reproducible.
- [x] Existe evidencia ligera versionable suficiente para GitHub.
- [x] El reel no depende de afirmar precision no validada.

## Actividad 8 - Validacion Multi-Clip Nivel 3

### Objetivo

Demostrar que Nivel 3 no funciona solo en un clip aislado y documentar donde falla.

### Tarea 8.1 - Ejecutar pipeline Nivel 3 en clip principal

- [x] Generar tracks rectificados.
- [x] Generar metricas tacticas.
- [x] Generar eventos avanzados.
- [x] Generar visualizaciones.
- [x] Generar dashboard/demo.

### Tarea 8.2 - Ejecutar pipeline Nivel 3 en clip secundario

- [x] Repetir calculos sin reescribir reglas para un solo clip.
- [x] Comparar diferencias de camara, iluminacion, oclusion y estabilidad de balon.
- [x] Registrar fallos o degradaciones.

### Tarea 8.3 - Comparar resultados

- [x] Crear `level3_multiclip_comparison.csv`.
- [x] Comparar numero de highlights.
- [x] Comparar control espacial agregado.
- [x] Comparar numero de interacciones.
- [x] Comparar confiabilidad media.

### Tarea 8.4 - Revision humana

- [x] Revisar overlays de highlights top.
- [x] Marcar `confiable`, `provisional` o `descartado`.
- [x] Documentar ejemplos de falsos positivos.
- [x] Documentar casos donde la homografia no sea suficiente.

### Artefactos esperados

- [x] `experiments/test_026_level3_multiclip/level3_multiclip_comparison.csv`.
- [x] `experiments/test_026_level3_multiclip/summary.md`.
- [x] Subcarpetas por clip con `config.yaml`, `summary.md` y evidencia ligera.

### Criterio de aceptacion

- [x] Al menos dos clips tienen salida Nivel 3 documentada.
- [x] Las limitaciones se reportan explicitamente.

## Actividad 9 - Pruebas, Calidad Y Gate De Cierre

### Objetivo

Cerrar Nivel 3 con un gate reproducible equivalente al cierre tecnico de Nivel 2.

### Tarea 9.1 - Pruebas unitarias

- [x] Agregar pruebas de homografia/transformacion de puntos.
- [x] Agregar pruebas de grilla de control espacial.
- [x] Agregar pruebas de ranking de highlights.
- [x] Agregar pruebas de generacion de narrativa.
- [x] Agregar pruebas de lectura/escritura de esquemas Nivel 3.

### Tarea 9.2 - Pruebas de integracion ligeras

- [x] Crear fixtures pequenos con tracks sinteticos.
- [x] Verificar que el pipeline Nivel 3 produce CSV/JSON esperados.
- [x] Verificar que visualizaciones basicas se generan sin video pesado.
- [x] Verificar que el dashboard referencia assets existentes.

### Tarea 9.3 - Gate de cierre Nivel 3

- [x] Implementar `scripts/check_level3_closure.py`.
- [x] Validar tests unitarios verdes.
- [x] Validar readiness Nivel 3.
- [x] Validar artefactos de spatial model.
- [x] Validar artefactos de metricas tacticas.
- [x] Validar artefactos de eventos avanzados.
- [x] Validar visualizaciones avanzadas.
- [x] Validar dashboard y reel manifest.
- [x] Validar multi-clip.
- [x] Validar ausencia de archivos pesados versionados.
- [x] Exportar `closure_checks.csv`.
- [x] Crear `experiments/test_027_level3_closure/summary.md`.

### Criterio de aceptacion

- [x] `scripts/check_level3_closure.py` termina con `0 fail`.
- [x] La carpeta de cierre declara Nivel 3 completado.

## Actividad 10 - Documentacion Final

### Objetivo

Actualizar la documentacion principal para que la entrega final explique claramente que se completo Nivel 3 y como reproducirlo.

### Tarea 10.1 - Actualizar documentos principales

- [ ] Actualizar `README.md` con estado Nivel 3.
- [ ] Actualizar `FutBotMX_documentacion_markdown/PROJECT_SCOPE.md`.
- [ ] Actualizar `FutBotMX_documentacion_markdown/EVENTS_DEFINITION.md`.
- [ ] Actualizar `FutBotMX_documentacion_markdown/VISUALIZATION_STRATEGY.md`.
- [ ] Actualizar `FutBotMX_documentacion_markdown/TESTING_LOG.md`.
- [ ] Actualizar `FutBotMX_documentacion_markdown/DECISIONS.md`.
- [ ] Actualizar `docs/TASK_LIST_DETAILED.md`.

### Tarea 10.2 - Crear resumen final Nivel 3

- [ ] Crear `experiments/test_027_level3_closure/LEVEL3_CLOSURE_SUMMARY.md`.
- [ ] Incluir checks pass/fail.
- [ ] Incluir lista de artefactos.
- [ ] Incluir limitaciones conocidas.
- [ ] Incluir comandos reproducibles.
- [ ] Declarar archivos pesados fuera de Git.

### Tarea 10.3 - Preparar lectura para evaluacion

- [ ] Crear una seccion clara en README con capturas Nivel 3.
- [ ] Mostrar tabla de metricas principales.
- [ ] Mostrar ejemplo corto de narrativa.
- [ ] Mostrar links relativos a dashboard y evidencia.
- [ ] Explicar que Nivel 3 es analisis avanzado aproximado, no arbitraje oficial.

### Criterio de aceptacion

- [ ] Un evaluador puede entender y reproducir Nivel 3 desde README y docs.
- [ ] La documentacion no contiene estados contradictorios entre Nivel 2 y Nivel 3.

## Orden Recomendado De Ejecucion

1. Completar Actividad 0 para iniciar Nivel 3 con decision formal.
2. Completar Actividad 1 para evitar cambios de formato tardios.
3. Completar Actividad 2 antes de Voronoi/control espacial.
4. Completar Actividades 3 y 4 en paralelo cuando el contrato de datos este estable.
5. Completar Actividades 5, 6 y 7 para construir la demo visible.
6. Completar Actividad 8 para validar que no sea un caso aislado.
7. Completar Actividades 9 y 10 para cierre tecnico y entrega final.

## Criterios De Cierre Nivel 3

- [x] Decision de inicio registrada.
- [x] Readiness Nivel 3 sin fallos.
- [x] Contrato de datos Nivel 3 documentado.
- [x] Tracks rectificados o fallback documentado.
- [x] Metricas tacticas generadas.
- [x] Eventos avanzados generados.
- [x] Highlights rankeados y validados visualmente.
- [x] Voronoi, grafo y mini-mapa generados.
- [x] Dashboard ligero disponible.
- [x] Reel/demo local documentado con manifest.
- [x] Validacion multi-clip completada.
- [x] Tests unitarios verdes.
- [x] Gate de cierre Nivel 3 con `0 fail`.
- [ ] README y documentacion principal actualizados.
- [x] Sin archivos pesados versionados.

## Comandos De Gate Esperados

```bash
env MPLCONFIGDIR=/tmp/matplotlib .venv/bin/python -m unittest discover -s tests -q
.venv/bin/python scripts/check_level3_readiness.py
.venv/bin/python scripts/check_level3_closure.py
```
