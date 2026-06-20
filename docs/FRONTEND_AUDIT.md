# Auditoria frontend

Fecha: 2026-06-18

## Estado corregido en esta ronda

- `src/futbotmx/live_playback.py`
  - El formulario para analizar otro video ya no ocupa siempre la primera pantalla; ahora vive en un panel colapsable.
  - El minimapa tiene control de capa propio (`layerMinimap`) y el render JS respeta ese estado.
  - El canvas del overlay se limita al escenario de video; el minimapa deja de heredar posicionamiento absoluto global.
  - Las tarjetas de estadisticas usan clases de tono en lugar de estilos inline.
  - El workbench usa dos columnas mas estables, panel lateral enmarcado y reglas responsive especificas.

- `src/futbotmx/local_app.py`
  - Se eliminaron estilos inline del panel de acciones.
  - `Ejecutar analisis` queda como accion primaria y `Pipeline Completo` como accion secundaria.
  - La pagina de resultado del pipeline comparte la misma base visual que el launcher local.
  - El layout agrega un estado intermedio para pantallas menores a 1100 px.

- `src/futbotmx/level3/manual_calibration.py`
  - `Guardar` queda como accion primaria.
  - `Descargar JSON` queda como accion secundaria.
  - `Reset puntos` queda separado como accion riesgosa.
  - El panel de canvas recibe mas espacio estable en escritorio.

## Estado corregido en segunda ronda

- `src/futbotmx/ui/`
  - Se agrego una capa compartida `futbotmx-ui-v1` con tokens, layout y componentes.
  - Los HTML siguen siendo autocontenidos, pero ahora inyectan una misma fuente visual.
  - `pyproject.toml` incluye los CSS como package data.

- Flujos declarados
  - Launcher local: `data-product-flow="launcher"`.
  - Live playback: `data-product-flow="playback"`.
  - Revision/calibracion: `data-product-flow="review"`.
  - Dashboard, reel y reportes: `data-product-flow="report"`.

- Reportes y herramientas migradas
  - `live_playback.py`
  - `local_app.py`
  - `level3/manual_calibration.py`
  - `level3/dashboard.py`
  - `level3/highlight_review.py`
  - `level3/reel.py`
  - `level3/final_report.py`
  - `level3/executive_report.py`

- Validacion agregada
  - `tests/test_frontend_ui.py` valida shell comun, breakpoints compartidos, flujos declarados y uso limitado de estilos inline.
- Tests de render existentes verifican `data-ui-shell="futbotmx-ui-v1"` en las superficies principales.

## Estado corregido en tercera ronda

- `src/futbotmx/local_app.py`
  - El launcher local ahora es el frontend unificado del proyecto en `http://127.0.0.1:8765/`.
  - Integra tarjetas para pipeline, dashboards generados, live playback, dashboard/reel canonicos, dashboard/reel revisados, revision humana, calibracion, reporte final, reporte ejecutivo, full analysis y checks.
  - Agrega una vista previa embebida priorizando la evidencia mas completa disponible: full analysis, paquete revisado, salida generada local y demos canonicos.
  - Agrega `/files/...` para servir cualquier artefacto del repositorio conservando rutas relativas, lo que permite abrir HTML con assets locales desde el mismo hub.
  - Descubre automaticamente todos los `.html` bajo `experiments/` y los muestra en el catalogo `HTML generados`.

- `tests/test_local_app.py`
  - Valida que el hub renderice el frontend unificado, superficies full analysis/revisadas y catalogo HTML.
  - Valida que el inventario automatico detecte HTML de experimento y no mezcle archivos no HTML.

## Estado corregido en cuarta ronda

- `src/futbotmx/live_playback.py`
  - El playback puede renderizarse con prefijo de ruta (`/playback`) sin perder compatibilidad standalone.
  - Sus endpoints de video, SSE, descargas, explorador, analisis y artefactos se reescriben como `/playback/...` cuando vive dentro del hub.
  - El manifest de backend y `FUTBOT_PLAYBACK_DATA` exponen endpoints montados, evitando colisiones con la raiz del launcher.

- `src/futbotmx/local_app.py`
  - El servidor `8765` monta el backend completo de live playback en `/playback/`.
  - El hub abre playback integrado en lugar de depender de `http://127.0.0.1:8766`.
  - La pagina posterior al pipeline apunta al playback integrado del mismo servidor.

- Validacion agregada
  - `tests/test_live_playback.py` valida HTML, payload y manifest con prefijo `/playback`.
  - `tests/test_local_app.py` valida que el hub enlace `/playback/` y no publique `127.0.0.1:8766`.

## Estado corregido en quinta ronda

- Sistema visual deportivo
  - La paleta compartida usa como base azul copa, azul celeste, rojo/magenta, verde cancha y blanco calido inspirados en la referencia visual del Mundial 2026.
  - La capa `src/futbotmx/ui/` agrega fondos tipo cancha, cabeceras tipo marcador, tarjetas de metricas con acentos por flujo y botones con lenguaje de sitio deportivo.

- Frontend unificado
  - El hub se presenta como `FutBotMX Match Center`, con modulos para pipeline, playback, revision, reportes y evidencia.
  - Las tarjetas de superficies ahora diferencian playback, revision, reportes, manifests y checks con color semantico.
  - La vista integrada y las tablas de artefactos reciben contraste de cabina de analisis, sin sacrificar densidad operativa.

- Playback y reportes
  - `live_playback.py` adopta look de replay deportivo: cabecera azul, acento rojo, tarjetas tipo marcador, panel lateral de broadcast y escenario de video mas contrastado.
  - Dashboard, reel, revision humana, calibracion, reporte final y reporte ejecutivo migran sus variables locales a la misma paleta y cabeceras deportivas.

## Estado corregido en sexta ronda

- Nueva identidad verde/lima
  - La paleta se reemplaza por una base inspirada en la referencia adjunta: verde profundo, verde brillante, lima, blanco y dorado de trofeo/balon.
  - Se eliminaron los restos de azul/rojo de la identidad anterior en `src/futbotmx` y en los HTML generados bajo `experiments/`.

- Optimizacion del frontend unificado
  - El hub ahora usa una cabecera tipo marcador con bloques verdes/lima, paneles mas densos y acciones principales mas claras.
  - Los formularios, estados, tablas, botones, descarga de artefactos y explorador de archivos se normalizaron al mismo sistema visual.
  - Playback adopta una cabina de replay mas compacta: marca `26`, header verde profundo, stats tipo marcador, panel lateral limpio y overlays con colores de la nueva paleta.

- Artefactos regenerados
  - Se regeneraron overlays, visualizaciones tacticas, dashboards, reels, revision humana, calibracion, reportes y playback para evitar pantallas con CSS antiguo.

## Problemas estructurales resueltos

- Hay varias superficies HTML independientes generadas desde Python con CSS/JS embebido:
  - `live_playback.py`
  - `local_app.py`
  - `level3/dashboard.py`
  - `level3/highlight_review.py`
  - `level3/manual_calibration.py`
  - `level3/reel.py`
  - `level3/final_report.py`
  - `level3/executive_report.py`

  Estado: resuelto parcialmente con fuente UI compartida inyectada. Los HTML siguen autocontenidos por compatibilidad con artefactos locales.

- La identidad visual sigue dividida entre:
  - Playback operativo con acentos Copa FutBotMX.
  - Reportes Nivel 3 con estetica papel/verde.
  - Herramientas locales con variaciones propias.

  Estado: resuelto parcialmente con tokens/componentes comunes. Playback conserva acentos propios por ser una herramienta operativa sobre video.

- El flujo de producto aun mezcla tres tareas:
  - Launcher / pipeline.
  - Playback operativo.
  - Reportes y revision humana.

  Estado: resuelto con `data-product-flow`, un hub unico que cataloga todas las superficies HTML detectadas y el playback dinamico montado bajo `/playback/` en el mismo servidor `8765`.

## Pendiente residual

No se agregaron screenshots automatizados con navegador porque el entorno actual no incluye Playwright/Selenium. La suite actual cubre estructura, shell, breakpoints CSS, flujos declarados y reglas anti inline-style. Si se instala Playwright despues, la siguiente mejora natural es agregar capturas en 1366x768, 1024x768 y 390x844 para detectar solapamientos visuales reales.

La meta de esta fase queda cumplida: extraer tokens, botones, paneles, tablas, grids y shells para que todas las pantallas principales pertenezcan al mismo sistema visual.
