# FutBotMX

FutBotMX es un proyecto de visión por computadora aplicado a videos de partidos de fútbol robótico. Usa **SAM 3** como tecnología base para segmentar campo, robots y balón, generar tracking, detectar eventos deportivos y crear visualizaciones útiles para análisis y demostración.

---

## Objetivo

Construir un pipeline reproducible que permita:

- Cargar videos de partidos.
- Segmentar elementos clave con SAM 3.
- Rastrear robots y balón.
- Detectar eventos deportivos.
- Generar visualizaciones.
- Exportar resultados ligeros en JSON, CSV, imágenes y Markdown.
- Preparar una demo alineada con la Copa FutBotMX.

---

# Alcance por niveles

El proyecto conserva 3 niveles de alcance.

## Nivel 1 — MVP obligatorio

Incluye:

- Ingesta de video.
- Segmentación con SAM 3.
- Tracking básico.
- Eventos mínimos.
- Overlay.
- Trails simples.
- Mapa de calor básico.
- Exportación de CSV/JSON.
- Documentación y bitácora.

## Nivel 2 — Extensión intermedia

Incluye:

- Eventos adicionales.
- Métricas de posesión.
- Timeline de eventos.
- Mejoras de tracking.
- Visualizaciones más claras.

Solo se inicia si Nivel 1 queda estable.

## Nivel 3 — Extensión avanzada

Incluye:

- Voronoi.
- Grafos de interacción.
- Highlights.
- Narrativa deportiva.
- Dashboard.
- Reel/demo final más elaborado.

Solo se inicia si Nivel 2 tiene resultados documentados.

---

# Flujo de trabajo con dos equipos

FutBotMX se desarrolla usando dos equipos:

## Escritorio

- Intel Core i7-12700.
- 16 GB RAM.
- NVIDIA GT 1030 2 GB.
- Windows.
- Codex.
- Claude Desktop.

Uso principal:

- Desarrollo de código.
- Documentación.
- Revisión de resultados.
- Ajuste de eventos.
- README.
- Dashboard ligero.
- Coordinación con agentes IA.

No debe usarse como máquina principal para inferencia SAM 3.

## Laptop MSI Thin GF63 12VE

- Intel Core i5-12450H.
- 16 GB RAM.
- NVIDIA RTX 4050 Laptop GPU.
- Ubuntu/Linux.

Uso principal:

- SAM 3.
- Segmentación.
- Tracking.
- Overlays.
- Benchmarks.
- Videos anotados.
- Pruebas pesadas con GPU.

## GitHub

GitHub sincroniza:

- Código.
- Documentación.
- Configuración.
- Scripts.
- Métricas ligeras.
- JSON de eventos.
- CSV de tracking.
- Capturas.
- Reportes markdown.

Los archivos pesados se mantienen fuera del repositorio.

---

# Arquitectura resumida

```text
Video local
   ↓
Ingesta de video
   ↓
Segmentación con SAM 3
   ↓
Normalización de detecciones
   ↓
Tracking
   ↓
Detección de eventos
   ↓
Visualizaciones
   ↓
Exportación de resultados
```

---

# Estructura del repositorio

```text
FutBotMX/
├── README.md
├── requirements-dev.txt
├── requirements-gpu.txt
├── configs/
├── data/
│   ├── raw/
│   ├── sample/
│   └── processed/
├── docs/
├── experiments/
├── outputs/
├── scripts/
├── src/
│   └── futbotmx/
└── tests/
```

---

# Instalación en escritorio

```bash
git clone <repo-url>
cd FutBotMX

python -m venv .venv
.venv\Scripts\activate

python -m pip install --upgrade pip
pip install -r requirements-dev.txt
```

---

# Instalación en laptop MSI

```bash
git clone <repo-url>
cd FutBotMX

python3 -m venv .venv
source .venv/bin/activate

python -m pip install --upgrade pip
pip install -r requirements-gpu.txt
```

Verificar GPU:

```bash
nvidia-smi
python -c "import torch; print(torch.cuda.is_available())"
```

---

# Cómo ejecutar una prueba en laptop MSI

1. Actualizar repositorio:

```bash
git pull origin main
```

2. Ejecutar prueba SAM 3:

```bash
python scripts/run_sam3_test.py --config configs/default.yaml
```

3. Guardar resultados ligeros en:

```text
experiments/test_001_sam3_ball_prompt/
```

4. Subir solo archivos ligeros:

```text
summary.md
metrics.csv
events.json
screenshots/
```

5. No subir:

```text
videos completos
frames masivos
máscaras masivas
checkpoints
outputs pesados
```

---

# Outputs esperados

```text
experiments/test_xxx/summary.md
experiments/test_xxx/config.yaml
experiments/test_xxx/metrics.csv
experiments/test_xxx/events.json
experiments/test_xxx/screenshots/
outputs/tracking/tracks.csv
outputs/events/events.json
outputs/visualizations/heatmap.png
```

Videos anotados completos pueden generarse localmente en la laptop, pero no deben subirse si son pesados.

---

# Estado actual

- [ ] Nivel 1 en desarrollo.
- [ ] SAM 3 pendiente de validación en laptop MSI.
- [ ] Tracking pendiente de prueba real.
- [ ] Eventos pendientes de validación con datos reales.
- [ ] Visualizaciones pendientes de generación.
- [ ] Nivel 2 pendiente.
- [ ] Nivel 3 pendiente.

---

# Documentación técnica

```text
docs/PROJECT_SCOPE.md
docs/EVENTS_DEFINITION.md
docs/TASK_BREAKDOWN.md
docs/DEVELOPMENT_RULES.md
docs/DEPENDENCIES.md
docs/VISUALIZATION_STRATEGY.md
docs/WORKFLOW_GITHUB_DUAL_MACHINE.md
docs/TESTING_LOG.md
docs/DECISIONS.md
docs/ERRORS_AND_FIXES.md
```

---

# Pendiente: reel de Instagram

Agregar:

- Link o archivo final.
- Clips usados.
- Duración.
- Texto narrativo.
- Capturas destacadas.

---

# Pendiente: video demo

Agregar:

- Ruta local o link externo.
- Configuración usada.
- Commit hash.
- Resultados generados.
- Limitaciones.

---

# Créditos

Proyecto desarrollado para **Copa FutBotMX — Capítulo Visión por Computadora**.

Tecnologías consideradas:

- SAM 3.
- PyTorch.
- OpenCV.
- NumPy.
- pandas.
- matplotlib.
- supervision.
- ByteTrack.
- ffmpeg.

---

# Licencia preliminar

Licencia sugerida: MIT.

La licencia final debe validarse antes de publicar, especialmente si se integran modelos, pesos, datasets o código externo.
