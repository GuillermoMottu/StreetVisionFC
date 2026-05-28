# FutBotMX — Workflow GitHub Dual Machine

## 1. Objetivo

Este documento define el flujo de trabajo con GitHub entre los dos equipos usados en FutBotMX:

- **Escritorio:** desarrollo, documentación, revisión y coordinación con agentes IA.
- **Laptop MSI:** inferencia pesada, SAM 3, tracking, overlays y benchmarks.

GitHub será el centro de integración entre ambos equipos.

---

# 2. Responsabilidades por equipo

| Equipo | Hardware | Rol | Qué tareas realiza | Qué tareas no debe realizar |
|---|---|---|---|---|
| Escritorio | i7-12700, 16 GB RAM, GT 1030 2 GB, Windows | Desarrollo principal | Código ligero, documentación, eventos, revisión CSV/JSON, README, Codex, Claude Desktop | Inferencia pesada SAM 3, videos anotados pesados, generación masiva de máscaras |
| Laptop MSI | i5-12450H, 16 GB RAM, RTX 4050, Ubuntu | Inferencia y pruebas pesadas | SAM 3, segmentación, tracking, benchmarks, overlays, videos anotados | Documentación extensa como tarea principal, edición final de entregables salvo resultados técnicos |

---

# 3. Flujo de trabajo estándar

## Paso 1 — Desarrollo en escritorio

Se implementa o modifica:

- Código fuente.
- Scripts.
- Configuración.
- Documentación.
- Lógica de eventos.
- Tests ligeros.

## Paso 2 — Commit y push a GitHub

```bash
git status
git add .
git commit -m "feat: add SAM3 test script"
git push origin main
```

## Paso 3 — Pull en laptop MSI

```bash
git pull origin main
```

## Paso 4 — Ejecución de pruebas pesadas

Ejemplo:

```bash
python scripts/run_sam3_test.py --config configs/default.yaml
```

## Paso 5 — Exportación de resultados ligeros

Guardar resultados en:

```text
experiments/test_xxx/
```

## Paso 6 — Commit y push desde laptop

```bash
git add experiments/test_001/
git commit -m "exp: add SAM3 test 001 results"
git push origin main
```

## Paso 7 — Pull en escritorio

```bash
git pull origin main
```

## Paso 8 — Revisión con Codex/Claude Desktop

Revisar:

- `summary.md`.
- `metrics.csv`.
- `events.json`.
- Capturas.
- Errores.
- Configuración usada.

## Paso 9 — Ajustes y nueva iteración

El escritorio ajusta código, documentación o parámetros y repite el flujo.

---

# 4. Qué se sube a GitHub

Sí subir:

- Código fuente.
- Documentación.
- Configuraciones YAML.
- Scripts.
- Bitácoras.
- Métricas CSV.
- JSON de eventos.
- CSV de tracking si es ligero.
- Capturas ligeras.
- Thumbnails.
- Reportes markdown.
- Logs resumidos.
- Archivos de prueba pequeños.

---

# 5. Qué no se sube a GitHub

No subir:

- Modelos.
- Checkpoints.
- Videos pesados.
- Datasets completos.
- Frames masivos.
- Máscaras masivas.
- Archivos temporales.
- Cachés.
- Entornos virtuales.
- Outputs demasiado grandes.
- Archivos `.npy` pesados.

---

# 6. Convención de carpetas para resultados ligeros

```text
experiments/
├── test_001_sam3_ball_prompt/
│   ├── summary.md
│   ├── config.yaml
│   ├── metrics.csv
│   ├── events.json
│   ├── errors.md
│   └── screenshots/
│       ├── frame_001.png
│       └── frame_002.png
```

Cada prueba debe tener su propia carpeta.

---

# 7. Convención de nombres para pruebas

Usar formato:

```text
test_<número>_<objetivo>
```

Ejemplos:

```text
test_001_sam3_ball_prompt
test_002_robot_segmentation
test_003_tracking_native_sam3
test_004_event_detection_shot_goal
test_005_overlay_generation
test_006_heatmap_possession
```

---

# 8. Comandos Git recomendados

## Comandos generales

```bash
git status
git pull origin main
git add .
git commit -m "docs: update dual-machine workflow"
git push origin main
```

## Flujo típico en escritorio

```bash
git pull origin main
# editar código/documentación
git status
git add .
git commit -m "feat: update event detection rules"
git push origin main
```

## Flujo típico en laptop

```bash
git pull origin main
python scripts/run_sam3_test.py --config configs/default.yaml
git add experiments/test_001_sam3_ball_prompt/
git commit -m "exp: add SAM3 test 001 results"
git push origin main
```

---

# 9. Reglas de sincronización

1. Antes de empezar trabajo en cualquier equipo, ejecutar:

```bash
git pull origin main
```

2. No trabajar en ambos equipos sobre el mismo archivo al mismo tiempo sin coordinación.
3. Toda prueba pesada debe registrar el commit usado.
4. Todo resultado ligero debe ir en `experiments/`.
5. Todo error relevante debe documentarse.
6. No subir archivos pesados.
7. No declarar una prueba como exitosa sin evidencia.

---

# 10. Registro mínimo por prueba

Cada prueba debe incluir:

```text
summary.md
config.yaml
metrics.csv, si aplica
events.json, si aplica
errors.md, si hubo errores
screenshots/, si aplica
```

El archivo `summary.md` debe indicar:

- Fecha.
- Equipo usado.
- Commit hash.
- Objetivo.
- Configuración.
- Resultado.
- Limitaciones.
- Siguiente acción.
