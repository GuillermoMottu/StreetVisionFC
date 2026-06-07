# Backlog Post-Nivel 3

Este backlog continua despues del cierre tecnico de Nivel 3. El objetivo es mejorar la operacion local, revision humana, empaquetado y validacion sin cambiar el alcance del proyecto: demo avanzada reproducible, sin SaaS, sin streaming en tiempo real y sin subir archivos pesados a Git.

## Regla De Trabajo

- [ ] No comprometer el cierre de Nivel 1, Nivel 2 ni Nivel 3.
- [ ] Mantener videos completos, checkpoints, frames masivos, mascaras masivas y renders pesados fuera de Git.
- [ ] Versionar solo evidencia ligera: codigo, configuracion, Markdown, CSV, JSON, PNG seleccionados y manifests.
- [ ] Crear carpeta de experimento por bloque nuevo cuando se generen artefactos.
- [ ] Guardar `config.yaml`, `summary.md` y manifest cuando aplique.
- [ ] Mantener lenguaje conservador: analisis aproximado, no arbitraje oficial.

## Estado General

- [x] Actividad 11 desarrollada como interfaz local con backend estandar de Python.
- [x] Actividad 12 desarrollada con editor local de puntos y validacion manual reproducible.
- [x] Actividad 13 desarrollada con asignacion aproximada de equipos, tracks enriquecidos, metricas y eventos regenerados.
- [x] Actividad 14 desarrollada con orquestador completo local, frontera GPU documentada y evidencia ligera reproducible.
- [x] Actividad 15 desarrollada con panel local de revision, `human_review.csv` validable e integracion en dashboard/reel.
- [ ] Actividades 16 a 20 pendientes.

## Actividad 11 - Interfaz Local De Ejecucion

### Objetivo

Permitir usar FutBotMX desde navegador local sin ejecutar scripts manualmente.

### Decision tecnica

- [x] Usar `HTML + backend local` con libreria estandar de Python.
- [x] Evitar Streamlit, Gradio, Flask u otra dependencia nueva.
- [x] Mantener la app como herramienta local, sin login, SaaS ni servidor remoto.

### Tarea 11.1 - Crear app local

- [x] Crear `scripts/run_local_app.py`.
- [x] Crear modulo testeable `src/futbotmx/local_app.py`.
- [x] Mostrar pantalla inicial con selector de video.
- [x] Mostrar `clip_id`.
- [x] Mostrar rango de frames.

### Tarea 11.2 - Integrar controles

- [x] Agregar selector de ROI: preset del clip, full frame o custom.
- [x] Agregar parametros de frame inicial/final/stride.
- [x] Agregar boton `Ejecutar analisis`.
- [x] Permitir regenerar dashboard y reel demo como artefactos ligeros.

### Tarea 11.3 - Mostrar resultados

- [x] Enlazar dashboard generado.
- [x] Enlazar reel/demo generado.
- [x] Mostrar checks de cierre Nivel 3.
- [x] Mostrar tabla de artefactos y estado de existencia.

### Artefactos

- [x] `scripts/run_local_app.py`.
- [x] `src/futbotmx/local_app.py`.
- [x] `tests/test_local_app.py`.
- [x] `experiments/test_028_local_app/config.yaml`.
- [x] `experiments/test_028_local_app/local_app_manifest.csv`.
- [x] `experiments/test_028_local_app/summary.md`.

### Criterio de aceptacion

- [x] La app arranca localmente con `.venv/bin/python scripts/run_local_app.py`.
- [x] La pagina inicial muestra selector de video, clip ID, frames, ROI y stride.
- [x] El boton de analisis puede regenerar dashboard/reel sin inferencia pesada.
- [x] Las pruebas unitarias cubren lectura de clips, formulario, render base y proteccion de rutas.

## Actividad 12 - Calibracion Manual De Cancha

### Objetivo

Mejorar homografia, mini-mapa, Voronoi y control espacial.

### Tarea 12.1 - Editor de puntos

- [x] Mostrar frame/overlay ligero.
- [x] Permitir seleccionar 4 esquinas del campo.
- [x] Guardar puntos en `field_calibration.json`.

### Tarea 12.2 - Validar calibracion

- [x] Proyectar tracks sobre mini-mapa.
- [x] Calcular confianza de calibracion.
- [x] Comparar homografia automatica vs manual.

### Tarea 12.3 - Integrar al pipeline

- [x] Permitir `--calibration-json`.
- [x] Registrar si se uso calibracion manual.
- [x] Actualizar resumen y manifest.

### Artefactos

- [x] `scripts/run_field_calibration_editor.py`.
- [x] `src/futbotmx/level3/manual_calibration.py`.
- [x] `experiments/test_029_manual_calibration/calibration_editor.html`.
- [x] `experiments/test_029_manual_calibration/field_calibration.json`.
- [x] `experiments/test_029_manual_calibration/calibration_editor_manifest.csv`.
- [x] `experiments/test_030_manual_spatial_model/calibration_comparison.csv`.
- [x] `experiments/test_030_manual_spatial_model/spatial_manifest.csv`.
- [x] `experiments/test_030_manual_spatial_model/minimap_tracks.png`.

### Criterio de aceptacion

- [x] Un clip puede usar calibracion manual reproducible.
- [x] El resumen diferencia calibracion automatica, manual y fallback.

## Actividad 13 - Asignacion De Equipos

### Objetivo

Pasar de robots neutrales a equipos aproximados para mejorar posesion, pases y narrativa.

### Tarea 13.1 - Definir estrategia

- [x] Evaluar asignacion manual por ID.
- [x] Evaluar color dominante del robot.
- [x] Evaluar lado/zona inicial como fallback.

### Tarea 13.2 - Crear `team_assignment.csv`

- [x] Incluir `clip_id`, `track_id`, `team`, `confidence`, `source`.
- [x] Permitir edicion humana.
- [x] Validar IDs existentes en tracks.

### Tarea 13.3 - Usar equipos en Nivel 3

- [x] Recalcular control por equipo.
- [x] Mejorar cadenas de pases.
- [x] Ajustar narrativa para no marcar todo como dudoso.

### Artefactos

- [x] `scripts/run_team_assignment.py`.
- [x] `src/futbotmx/level3/team_assignment.py`.
- [x] `experiments/test_031_team_assignment/team_assignment.csv`.
- [x] `experiments/test_031_team_assignment/strategy_evaluation.csv`.
- [x] `experiments/test_031_team_assignment/team_assignment_validation.csv`.
- [x] `experiments/test_031_team_assignment/level3_tracks_with_teams.csv`.
- [x] `experiments/test_032_level3_team_metrics/level3_metrics.csv`.
- [x] `experiments/test_032_level3_team_metrics/spatial_control.csv`.
- [x] `experiments/test_033_level3_team_events/level3_events.json`.
- [x] `experiments/test_033_level3_team_events/level3_narrative.md`.

### Criterio de aceptacion

- [x] Las metricas por equipo son opcionales y trazables.
- [x] Si no hay equipo confiable, el pipeline conserva fallback neutral.

## Actividad 14 - Pipeline Completo Para Video Nuevo

### Objetivo

Ejecutar todo el analisis con un solo comando.

### Tarea 14.1 - Crear script unificado

- [x] Crear `scripts/run_full_analysis.py`.
- [x] Recibir `--video`, `--clip-id`, `--start-frame`, `--end-frame`.
- [x] Crear carpeta de experimento automaticamente.

### Tarea 14.2 - Encadenar etapas

- [x] Ingesta de video.
- [x] SAM 3/detecciones.
- [x] Tracking.
- [x] Eventos Nivel 1/2.
- [x] Nivel 3 completo.

### Tarea 14.3 - Exportar resultado final

- [x] Generar dashboard.
- [x] Generar reel local.
- [x] Generar resumen reproducible.

### Artefactos

- [x] `scripts/run_full_analysis.py`.
- [x] `src/futbotmx/full_analysis.py`.
- [x] `tests/test_full_analysis.py`.
- [x] `experiments/test_034_full_analysis/config.yaml`.
- [x] `experiments/test_034_full_analysis/summary.md`.
- [x] `experiments/test_034_full_analysis/stage_plan.csv`.
- [x] `experiments/test_034_full_analysis/runtime_metrics.csv`.
- [x] `experiments/test_034_full_analysis/full_analysis_manifest.csv`.
- [x] `experiments/test_034_full_analysis/dashboard/dashboard.html`.
- [x] `experiments/test_034_full_analysis/reel/reel_demo.html`.

### Criterio de aceptacion

- [x] El comando documenta que etapas son ligeras y cuales requieren laptop/GPU.
- [x] Cada salida queda con configuracion, summary y manifest.

## Actividad 15 - Revision Humana De Highlights

### Objetivo

Fortalecer la evidencia visual y reducir falsos positivos.

### Tarea 15.1 - Crear panel de revision

- [x] Mostrar overlay del highlight.
- [x] Mostrar mini-mapa y datos del evento.
- [x] Permitir marcar `confiable`, `provisional` o `descartado`.

### Tarea 15.2 - Guardar revision

- [x] Exportar `human_review.csv`.
- [x] Incluir notas libres.
- [x] Incluir usuario/fecha si aplica.

### Tarea 15.3 - Integrar revision

- [x] Usar revision en dashboard.
- [x] Usar revision en reel.
- [x] Incluir resumen en cierre.

### Artefactos

- [x] `scripts/run_highlight_review_panel.py`.
- [x] `src/futbotmx/level3/highlight_review.py`.
- [x] `tests/test_highlight_review.py`.
- [x] `experiments/test_035_human_review/human_review_panel.html`.
- [x] `experiments/test_035_human_review/human_review.csv`.
- [x] `experiments/test_035_human_review/human_review_validation.csv`.
- [x] `experiments/test_035_human_review/human_review_manifest.csv`.
- [x] `experiments/test_035_human_review/dashboard/dashboard.html`.
- [x] `experiments/test_035_human_review/reel/reel_demo.html`.

### Criterio de aceptacion

- [x] Los highlights revisados afectan dashboard/reel sin borrar evidencia original.
- [x] El archivo de revision es editable y validable.

## Actividad 16 - Resumen Ejecutivo Para Evaluadores

### Objetivo

Crear una entrada clara y rapida para jueces o evaluadores.

### Tarea 16.1 - Crear reporte HTML

- [ ] Crear `experiments/final_demo_report/`.
- [ ] Incluir objetivo, resultado y limitaciones.
- [ ] Incluir links a dashboard, reel y cierre.

### Tarea 16.2 - Incluir evidencia clave

- [ ] Agregar 3 capturas Nivel 3.
- [ ] Agregar tabla multi-clip.
- [ ] Agregar narrativa ejemplo.

### Tarea 16.3 - Empaquetar lectura

- [ ] Crear `FINAL_DEMO_REPORT.html`.
- [ ] Crear `summary.md`.
- [ ] Crear manifest de assets.

### Criterio de aceptacion

- [ ] El reporte se abre localmente y se entiende sin recorrer todo el repositorio.
- [ ] Los links relativos apuntan a artefactos versionados.

## Actividad 17 - Optimizacion Y Cache

### Objetivo

Reducir tiempos al analizar mas clips o repetir pruebas.

### Tarea 17.1 - Definir cache

- [ ] Cachear detecciones SAM 3.
- [ ] Cachear tracks.
- [ ] Cachear artefactos Nivel 3 por hash de entrada.

### Tarea 17.2 - Evitar recomputacion

- [ ] Detectar si el video/rango ya fue procesado.
- [ ] Reusar CSV/JSON existentes.
- [ ] Forzar recomputacion con `--force`.

### Tarea 17.3 - Medir rendimiento

- [ ] Registrar duracion por etapa.
- [ ] Exportar `runtime_metrics.csv`.
- [ ] Documentar cuellos de botella.

### Criterio de aceptacion

- [ ] El pipeline explica cuando reutiliza cache.
- [ ] `--force` invalida cache de forma controlada.

## Actividad 18 - Validacion Con Mas Clips

### Objetivo

Aumentar robustez comparando mas condiciones de camara, luz y oclusion.

### Tarea 18.1 - Seleccionar clips

- [ ] Elegir 3-5 videos nuevos.
- [ ] Clasificar por visibilidad, balon, robots y campo.
- [ ] Documentar motivos de seleccion.

### Tarea 18.2 - Ejecutar pipeline

- [ ] Procesar cada clip con mismas reglas.
- [ ] Exportar subcarpetas por clip.
- [ ] Generar comparacion agregada.

### Tarea 18.3 - Documentar fallos

- [ ] Identificar casos con mala homografia.
- [ ] Identificar perdida de balon.
- [ ] Identificar falsos highlights.

### Criterio de aceptacion

- [ ] La comparacion separa exito, degradacion y fallo conocido.
- [ ] No se versionan videos ni renders pesados.

## Actividad 19 - Overlay De Video Corto

### Objetivo

Crear evidencia visual mas directa sin subir archivos pesados.

### Tarea 19.1 - Generar clip corto local

- [ ] Seleccionar 1-3 highlights.
- [ ] Renderizar overlay con IDs, trails y evento.
- [ ] Guardar MP4 local fuera de Git.

### Tarea 19.2 - Crear evidencia ligera

- [ ] Exportar thumbnails.
- [ ] Exportar contact sheet.
- [ ] Crear `video_overlay_manifest.csv`.

### Tarea 19.3 - Documentar reproduccion

- [ ] Crear script `render_overlay_clip.sh`.
- [ ] Documentar dependencias.
- [ ] Enlazar desde README/reporte.

### Criterio de aceptacion

- [ ] El MP4 queda fuera de Git.
- [ ] La evidencia versionada permite entender que se renderizo.

## Actividad 20 - Exportacion A Reporte PDF/HTML

### Objetivo

Convertir la entrega en un reporte presentable y autocontenido.

### Tarea 20.1 - Definir plantilla

- [ ] Crear estructura HTML imprimible.
- [ ] Incluir portada, resumen, metricas y evidencias.
- [ ] Mantener links relativos a artefactos.

### Tarea 20.2 - Generar reporte

- [ ] Crear `scripts/build_final_report.py`.
- [ ] Exportar `final_report.html`.
- [ ] Opcionalmente exportar PDF local fuera de Git.

### Tarea 20.3 - Validar reporte

- [ ] Verificar que todos los links existen.
- [ ] Verificar que no duplica archivos pesados.
- [ ] Agregar manifest y summary.

### Criterio de aceptacion

- [ ] El HTML imprimible queda versionado.
- [ ] El PDF, si se genera, queda documentado como salida local no versionada.
