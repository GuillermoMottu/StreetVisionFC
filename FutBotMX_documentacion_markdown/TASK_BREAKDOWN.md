# FutBotMX — Task Breakdown

## 1. Propósito

Este documento organiza el desarrollo de FutBotMX en fases, tareas, responsabilidades por equipo y resultados esperados en GitHub.

El desarrollo se realizará con dos estaciones:

- **Escritorio:** desarrollo, documentación, Codex, Claude Desktop, revisión de resultados.
- **Laptop MSI:** inferencia pesada con GPU, SAM 3, tracking, overlays y benchmarks.

---

# 2. Reglas generales por fase

| Tipo de tarea | Equipo recomendado |
|---|---|
| Documentación | Escritorio |
| Código base | Escritorio |
| Configuración | Escritorio |
| Pruebas ligeras | Escritorio |
| SAM 3 | Laptop MSI |
| Segmentación | Laptop MSI |
| Tracking pesado | Laptop MSI |
| Video anotado | Laptop MSI |
| Análisis de CSV/JSON | Escritorio |
| Ajuste de reglas de eventos | Escritorio |
| Validación final visual | Ambos |

---

# Fase 0: Preparación del entorno

## Tarea 0.1 - Crear estructura base del repositorio

**Equipo recomendado:** Escritorio  
**Motivo:** Es una tarea de organización, documentación y estructura.  
**Entrada desde GitHub:** Ninguna, repositorio inicial.  
**Salida hacia GitHub:** Estructura de carpetas, `.gitignore`, README inicial.  
**No subir:** Entornos virtuales, videos, checkpoints.

### Resultado mínimo viable

Repositorio con carpetas base:

```text
src/
scripts/
configs/
docs/
experiments/
outputs/
data/
tests/
```

### Resultado óptimo

Estructura completa con `.gitkeep`, documentación base y reglas de desarrollo.

---

## Tarea 0.2 - Configurar entorno de escritorio

**Equipo recomendado:** Escritorio  
**Motivo:** Será la estación principal de desarrollo.  
**Entrada desde GitHub:** Repositorio clonado.  
**Salida hacia GitHub:** Notas de instalación si hubo ajustes.  
**No subir:** `.venv/`.

### Resultado esperado en GitHub

- `DEPENDENCIES.md` actualizado.
- `ERRORS_AND_FIXES.md` si hubo errores.
- Commit con configuración de entorno documentada.

---

## Tarea 0.3 - Configurar entorno de laptop MSI

**Equipo recomendado:** Laptop MSI  
**Motivo:** Requiere validar GPU, CUDA, PyTorch y SAM 3.  
**Entrada desde GitHub:** Repositorio actualizado desde escritorio.  
**Salida hacia GitHub:** Resultado ligero de validación.  
**No subir:** Drivers, CUDA, checkpoints, modelos.

### Resultado esperado en GitHub

```text
experiments/test_000_environment_check/
├── summary.md
├── metrics.csv
└── errors.md
```

---

# Fase 1: Ingesta de video

## Tarea 1.1 - Implementar carga de video

**Equipo recomendado:** Escritorio  
**Motivo:** Código ligero con OpenCV.  
**Entrada desde GitHub:** Estructura base.  
**Salida hacia GitHub:** Script de carga de video y pruebas ligeras.  
**No subir:** Videos completos.

### Resultado MVP

Script que lee:

- FPS.
- Resolución.
- Número de frames.
- Duración.

### Resultado esperado en GitHub

```text
scripts/extract_frames.py
src/futbotmx/video_io/
tests/test_video_io.py
```

---

## Tarea 1.2 - Probar carga con clip local

**Equipo recomendado:** Ambos  
**Motivo:** El escritorio valida código; laptop puede probar clips más grandes.  
**Momento de cambio de equipo:** Cuando el script esté terminado en escritorio, hacer push y probar en laptop.

### Entrada desde GitHub

- Script de video.
- Configuración YAML.

### Salida hacia GitHub

- `summary.md`.
- Capturas ligeras si aplica.
- Errores documentados.

### No subir

- Video completo.
- Frames masivos.

---

# Fase 2: Segmentación con SAM 3

## Tarea 2.1 - Integrar wrapper de SAM 3

**Equipo recomendado:** Escritorio para diseño inicial, Laptop MSI para prueba real.  
**Motivo:** La interfaz puede codificarse en escritorio, pero la inferencia debe validarse en laptop.  
**Momento de cambio de equipo:** Cuando el wrapper esté listo y versionado en GitHub.

### Entrada desde GitHub

```text
src/futbotmx/segmentation/sam3_segmenter.py
configs/segmentation.yaml
scripts/run_sam3_test.py
```

### Salida hacia GitHub

```text
experiments/test_001_sam3_ball_prompt/
├── summary.md
├── config.yaml
├── metrics.csv
├── errors.md
└── screenshots/
```

### No subir

- Checkpoints.
- Máscaras masivas.
- Videos completos.
- Frames extraídos masivamente.

---

## Tarea 2.2 - Segmentar balón

**Equipo recomendado:** Laptop MSI  
**Motivo:** Requiere inferencia SAM 3.  
**Entrada desde GitHub:** Script de prueba SAM 3 y configuración.  
**Salida hacia GitHub:** Capturas ligeras, resumen y métricas.

### Resultado MVP

El balón se detecta en frames seleccionados.

### Resultado óptimo

El balón se detecta con consistencia suficiente para tracking.

---

## Tarea 2.3 - Segmentar robots

**Equipo recomendado:** Laptop MSI  
**Motivo:** Inferencia visual con GPU.  
**Entrada desde GitHub:** Código actualizado y configuración.  
**Salida hacia GitHub:** Capturas ligeras y resumen de detección.

### Resultado MVP

Robots detectados como objetos segmentados.

### Resultado óptimo

Separación aproximada entre aliados y rivales.

---

## Tarea 2.4 - Segmentar campo

**Equipo recomendado:** Laptop MSI  
**Motivo:** Segmentación visual y posible uso de máscaras grandes.  
**Entrada desde GitHub:** Configuración y script.  
**Salida hacia GitHub:** Captura ligera de campo segmentado.

---

# Fase 3: Tracking

## Tarea 3.1 - Implementar tracking base

**Equipo recomendado:** Escritorio para código, Laptop MSI para ejecución completa.  
**Motivo:** La lógica se desarrolla en escritorio; el tracking real depende de detecciones generadas en laptop.  
**Momento de cambio de equipo:** Después de implementar el tracker y subirlo a GitHub.

### Entrada desde GitHub

- Detecciones normalizadas.
- Código de tracking.
- Configuración.

### Salida hacia GitHub

```text
experiments/test_003_tracking/
├── summary.md
├── tracks.csv
├── metrics.csv
└── screenshots/
```

### No subir

- Videos anotados pesados.
- Máscaras completas.

---

## Tarea 3.2 - Exportar trayectorias

**Equipo recomendado:** Laptop MSI genera datos; Escritorio revisa.  
**Motivo:** La laptop produce tracks desde inferencia; el escritorio analiza CSV.

### Resultado esperado en GitHub

```text
experiments/test_003_tracking/tracks.csv
```

---

# Fase 4: Detección de eventos

## Tarea 4.1 - Desarrollar lógica de posesión

**Equipo recomendado:** Escritorio  
**Motivo:** Puede desarrollarse usando `tracks.csv` generado por laptop.  
**Entrada desde GitHub:** Tracks exportados.  
**Salida hacia GitHub:** Código de eventos y JSON ligero.

### Resultado esperado

```text
src/futbotmx/events/possession.py
experiments/test_004_events/events.json
```

---

## Tarea 4.2 - Detectar pase, tiro y colisión

**Equipo recomendado:** Escritorio para reglas; Laptop MSI para validación visual.  
**Momento de cambio de equipo:** Después de ajustar reglas en escritorio, probar overlays en laptop.

### Salida hacia GitHub

- `events.json`.
- `summary.md`.
- Capturas con eventos anotados.

---

# Fase 5: Visualizaciones

## Tarea 5.1 - Overlay de segmentación/tracking

**Equipo recomendado:** Laptop MSI  
**Motivo:** Renderizado sobre video y uso de resultados pesados.  
**Entrada desde GitHub:** Código, config, tracks, events.  
**Salida hacia GitHub:** Capturas ligeras y resumen.

### No subir

- Video completo anotado si es pesado.

---

## Tarea 5.2 - Mapa de calor y posesión temporal

**Equipo recomendado:** Escritorio  
**Motivo:** Puede generarse con CSV/JSON ligeros.  
**Entrada desde GitHub:** Tracks y events.  
**Salida hacia GitHub:** PNG ligeros y resumen.

---

# Fase 6: Exportación de resultados

## Tarea 6.1 - Exportar JSON/CSV

**Equipo recomendado:** Ambos  
**Motivo:** La laptop genera datos base; el escritorio valida estructura.  
**Salida hacia GitHub:** Archivos ligeros versionables.

---

## Tarea 6.2 - Exportar video anotado

**Equipo recomendado:** Laptop MSI  
**Motivo:** Puede ser pesado y requiere procesamiento de video.  
**Salida hacia GitHub:** Solo capturas, thumbnails o GIF pequeño si pesa poco.  
**No subir:** Video completo si es grande.

---

# Fase 7: Documentación y demo

## Tarea 7.1 - Actualizar README y documentación

**Equipo recomendado:** Escritorio  
**Motivo:** Trabajo principal con Codex y Claude Desktop.  
**Entrada desde GitHub:** Resultados ligeros de laptop.  
**Salida hacia GitHub:** README, docs y bitácoras actualizadas.

---

## Tarea 7.2 - Preparar demo final

**Equipo recomendado:** Ambos  
**Motivo:** Laptop genera videos; escritorio prepara narrativa, README, reel y entrega.

### Resultado esperado en GitHub

- Capturas.
- Resumen.
- Métricas.
- Documentación.
- Referencia local o externa al video pesado si aplica.

---

# 8. Puntos de cambio entre equipos

## Cambio 1: Escritorio → Laptop MSI

Ocurre cuando:

- Se termina un script.
- Se modifica una configuración.
- Se prepara una prueba SAM 3.
- Se necesita ejecutar inferencia.
- Se requiere generar máscaras, tracking u overlays.

### Proceso

1. Desarrollar en escritorio.
2. Verificar `git status`.
3. Hacer commit.
4. Hacer push a GitHub.
5. Hacer pull en laptop.
6. Ejecutar prueba pesada.
7. Guardar outputs pesados localmente.
8. Subir a GitHub solo resultados ligeros.

## Cambio 2: Laptop MSI → Escritorio

Ocurre cuando:

- La laptop termina una prueba.
- Se generan métricas.
- Se generan JSON de eventos.
- Se obtienen capturas o thumbnails.
- Se documentan errores o resultados.

### Proceso

1. Crear resumen de prueba.
2. Guardar configuración usada.
3. Registrar commit hash.
4. Subir resultados ligeros a GitHub.
5. Hacer pull en escritorio.
6. Revisar con Codex/Claude Desktop.
7. Ajustar código o documentación.
8. Preparar siguiente iteración.

---

# 9. Regla de avance por niveles

## Para iniciar Nivel 2

Debe existir:

- Prueba funcional de Nivel 1.
- SAM 3 validado.
- Tracking básico exportado.
- `events.json` mínimo.
- Evidencia en `experiments/`.
- Bitácora actualizada.

## Para iniciar Nivel 3

Debe existir:

- Nivel 2 documentado.
- Visualizaciones intermedias funcionales.
- Eventos adicionales validados.
- Pipeline reproducible.
- Tiempo suficiente para no comprometer entrega.
