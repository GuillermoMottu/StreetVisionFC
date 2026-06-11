# PLAN MAESTRO DE CORRECCIÓN AJUSTADO v2 — FutBotMX Categoría Profesional

> Documento unificado y ajustado a partir del Plan Maestro de corrección de FutBotMX.
> Incorpora: trabajo obligatorio en rama separada, baseline previo, entorno MSI validado con RTX 4050,
> validación real de la API de SAM 3 antes de implementar masks, fallback formal para portería,
> gates separados de entrega mínima y entrega profesional, y registro temprano del entorno/dependencias.
>
> **Novedades de la v2:** tabla de equivalencia con las fases del prompt de ejecución y regla de
> precedencia; protocolo de continuidad entre sesiones (cierres de fase versionados + PHASE_STATUS.md);
> tareas con humano en el loop marcadas explícitamente; higiene de `.gitignore` para archivos locales;
> mecanismo definido de carga de variables de entorno; verificación de herramientas (ffmpeg/ffprobe)
> en el baseline; criterios de grep refinados para evitar falsos positivos.
>
> Fecha de referencia: 2026-06-10.

---

## 0. Equivalencia con las fases del prompt de ejecución

El prompt de ejecución (`PROMPT_EJECUCION_FUTBOTMX_V2.md`) organiza el trabajo en **Fases 0-7**; este plan usa **Bloques -1 a 6**. La equivalencia es:

| Bloque (este plan) | Fase (prompt) | Contenido |
|---|---|---|
| Bloque -1 | Fase 0 | Rama, baseline y respaldo |
| Bloque 0 | Fase 1 | Reproducibilidad rápida |
| Bloque 1 (S0-S4) | Fase 2 | Segmentación: inspección SAM 3, masks y portería |
| Bloque 2 | Fase 3 | Overlays, visualización y video demo |
| Bloque 3 | Fase 4 | Team assignment |
| Bloque 5 | Fase 5 | Métricas, benchmark y dependencias |
| Bloque 4 | Fase 6 | Documentación para evaluación |
| Bloque 6 | Fase 7 | Limpieza de arquitectura y CI |

**Regla de precedencia:** en caso de conflicto de orden o contenido entre este plan y el prompt de ejecución, **manda el prompt**. En particular, el prompt ejecuta métricas (Fase 5) antes de documentación (Fase 6) para que `RESULTS_SUMMARY.md` y `EVALUATOR_GUIDE.md` se escriban con las métricas finales ya disponibles; este plan los considera paralelizables y acepta ese orden.

---

## 1. Diagnóstico consolidado

Ambas auditorías coinciden en el mismo veredicto: **corregir antes de entregar**. El proyecto tiene infraestructura técnica genuinamente alta — SAM 3 real en GPU, ByteTrack estable, análisis táctico con Voronoi/grafos, tests y experimentos documentados — pero presenta brechas que un evaluador técnico puede detectar de inmediato.

Probabilidad estimada de cumplir Categoría Profesional en el estado actual: **60-75%**.
Probabilidad estimada con correcciones críticas aplicadas: **85-90%**.

### Brechas críticas

| # | Brecha | Evidencia | Por qué es crítica |
|---|---|---|---|
| C1 | SAM 3 no extrae ni visualiza máscaras pixel-level | `_detections_from_output` solo toma `boxes` y `scores`; `mask_path` siempre `null`; `overlay.py` solo dibuja rectángulos | SAM es un modelo de segmentación. Sin masks visibles, el criterio central de la competencia no se demuestra correctamente |
| C2 | No existe video demo de ≤2 minutos | Único MP4 versionado dura ~1 segundo; el reel es HTML estático | Es un entregable obligatorio, no una mejora |
| C3 | Equipos en `neutral` en todos los tracks | `tracks_bytetrack.csv` columna `team = neutral`; `team_assignment.py` existe pero no está conectado | Sin aliado/rival, pases, intercepciones y posesión por equipo carecen de validez semántica |
| C4 | Pipeline no reproducible externamente | Rutas absolutas en `configs/default.yaml`; dependencias sin versiones; sin `LICENSE`; `data/sample/` vacío | La reproducibilidad es criterio explícito de una entrega profesional |

### Brechas altas

- Portería no incluida como clase de segmentación.
- Sin métricas supervisadas mínimas: IoU, Dice, precision, recall o F1 contra ground truth pequeño.
- Benchmark incompleto: sin FPS, ms/frame ni VRAM durante inferencia.
- Sin `LICENSE` ni `THIRD_PARTY_NOTICES.md`.
- `requirements-gpu.txt` sin pinning y con dependencias faltantes como `einops`, `pycocotools` y `psutil`.
- Arquitectura `Level 1 / Level 2 / Level 3` expuesta como estructura final.
- Documentación activa con flujo dual escritorio/laptop, cuando la dirección actual es MSI como entorno único.

---

## 2. Directrices estructurales obligatorias

### 2.1 Trabajar siempre en una rama distinta

Todas las correcciones deben realizarse en una rama separada. **No se debe trabajar directamente sobre `main`, `master` o la rama estable actual.**

Rama recomendada:

```bash
git checkout main
git pull
git checkout -b fix/master-audit-corrections
```

Reglas para la rama:

- Cada bloque debe cerrarse con commits pequeños y descriptivos.
- Antes de iniciar un bloque nuevo, ejecutar pruebas mínimas o validaciones del bloque anterior.
- No hacer refactors masivos junto con cambios funcionales críticos.
- No renombrar módulos `level*` hasta que el pipeline, demo y tests estén validados.
- Si un cambio rompe el pipeline, debe revertirse o aislarse antes de continuar.

Formato sugerido de commits:

```text
fix(config): remove absolute video paths
chore(config): ignore local env and path files
feat(segmentation): export sam3 masks
feat(visualization): add mask overlays
feat(demo): generate final evaluation video
docs(evaluation): add evaluator guide
chore(closure): add phase X closure report
```

### 2.2 Continuidad entre sesiones (nuevo)

El desarrollo se ejecuta con agentes en sesiones que pueden compactarse o reiniciarse. Para no perder estado:

1. **Cada cierre de bloque/fase se guarda y commitea** en:

```text
experiments/current_evaluation/closures/FASE_X_cierre.md
```

2. **Existe un archivo de estado vivo**:

```text
experiments/current_evaluation/PHASE_STATUS.md
```

con: fase actual, fases aprobadas por el usuario (citando la frase de aprobación), fase pendiente de aprobación, tareas incompletas y bloqueos.

3. **Protocolo de reanudación**: toda sesión nueva debe leer `PHASE_STATUS.md`, el último cierre y `git log --oneline -10` antes de tocar código. No se repite trabajo ya commiteado ni se asume aprobación no registrada.

### 2.3 Tareas con humano en el loop (nuevo)

Tres tareas requieren intervención humana directa y **el agente no debe ejecutarlas por su cuenta** (hacerlo equivaldría a inventar evidencia):

| Tarea | Bloque | Rol del agente | Rol del usuario |
|---|---|---|---|
| Anotación del mini ground truth (20-50 frames) | Bloque 5 | Exportar frames, definir formato (CSV/JSON/COCO), crear plantilla e instrucciones, implementar el cálculo de métricas | Anotar o validar las anotaciones |
| CSV manual de equipos (si la clasificación visual falla) | Bloque 3 | Generar CSV con `track_id` + contactsheet de crops/frames de referencia | Asignar/validar el equipo de cada track |
| Revisión visual del demo final | Bloque 2 | Generar el MP4, validar duración y contenido técnico | Confirmar visualmente que el demo es correcto y presentable |

### 2.4 Proyecto integrado, sin niveles en la narrativa pública

La narrativa pública del proyecto debe organizarse por módulos funcionales:

```text
ingesta → segmentación SAM 3 → exportación de masks → clasificación clase/equipo → tracking → eventos → métricas → análisis táctico → visualización → dashboard → demo
```

Los artefactos `level1`, `level2` y `level3` pueden mantenerse como evidencia histórica, pero no deben presentarse como arquitectura principal.

Regla de seguridad:

- Primero hacer el proyecto demostrable y reproducible.
- Después limpiar nombres y estructura interna.
- Nunca eliminar evidencia histórica; archivar bajo `experiments/archived/` o `docs/archived/`.

### 2.5 Laptop MSI Ubuntu con RTX 4050 como entorno único

El entorno principal ya fue verificado como:

```text
Laptop MSI Ubuntu con GPU NVIDIA RTX 4050
```

Toda la documentación activa debe describir un solo flujo de instalación, ejecución, inferencia y evaluación desde esta laptop.

Documentos como los siguientes deben moverse a legado o dejar de referenciarse desde la documentación activa:

- `docs/SETUP_DESKTOP_WINDOWS.md`
- `FutBotMX_documentacion_markdown/WORKFLOW_GITHUB_DUAL_MACHINE.md`
- cualquier guía que presente escritorio/laptop como flujo operativo principal

Además, debe generarse un reporte real del entorno:

```text
experiments/current_evaluation/environment_report.md
```

Este reporte debe incluir:

- GPU: NVIDIA RTX 4050.
- Driver NVIDIA.
- CUDA disponible.
- Versión de PyTorch.
- Versión de Python.
- VRAM total detectada.
- Sistema operativo.
- Resultado de `torch.cuda.is_available()`.
- **Versiones de `ffmpeg` y `ffprobe`** (requeridas por el Bloque 2 / Fase 3; si faltan, registrar bloqueo desde el baseline).

### 2.6 Segmentación de cuatro clases

La segmentación mínima debe cubrir:

1. Campo.
2. Robots.
3. Balón.
4. Portería.

La portería debe agregarse con evidencia, no por intuición. Prompts candidatos:

```text
goal
soccer goal
goalpost
small soccer goal
robot soccer goal
```

Si SAM 3 no detecta la portería de forma confiable, se permite usar un fallback geométrico basado en el modelo de campo, pero debe documentarse explícitamente como fallback, no como segmentación real.

### 2.7 Mecanismo de configuración portable (nuevo — definición única)

Para evitar implementaciones improvisadas, el mecanismo de variables de entorno queda definido así:

- `configs/default.yaml` referencia rutas con sintaxis `${VAR}` (p. ej. `${FUTBOTMX_VIDEO_836}`, `${SAM3_CHECKPOINT_PATH}`).
- `src/futbotmx/config.py` expande `${VAR}` en los valores string del YAML mediante `os.path.expandvars` (o expansión recursiva equivalente) al cargar la configuración.
- Soporte opcional de `.env` en la raíz: si `python-dotenv` está instalado, `load_config()` carga `.env` con `load_dotenv()` antes de expandir; si no, las variables se exportan en shell y así se documenta.
- Si una variable referenciada no está definida, `load_config()` falla con un mensaje claro que indica qué variable falta y remite a `configs/local_paths.example.yaml` — nunca con un error críptico de ruta inexistente.
- **Higiene de Git:** `.env` y `configs/local_paths.yaml` (el real, con rutas personales) se añaden a `.gitignore` en el mismo bloque en que se crean las plantillas. Solo se versionan `.env.example` y `configs/local_paths.example.yaml`.

---

## 3. Resolución final del orden de ejecución

Codex prioriza reproducibilidad. Claude Code prioriza segmentación. El orden final combina ambos enfoques:

1. Crear rama separada y baseline (incl. verificación de herramientas).
2. Aplicar quick wins de reproducibilidad (incl. `.gitignore`).
3. Iniciar camino crítico de segmentación: inspección de API → portería → masks → overlay.
4. Generar demo visual (con confirmación visual del usuario).
5. Conectar team assignment (con validación humana si hay CSV manual).
6. Elevar rigor profesional con métricas y benchmark (con anotación humana del ground truth).
7. Documentar para evaluador (con métricas reales ya disponibles).
8. Refactorizar arquitectura solo al final.

Camino crítico ajustado:

```text
B-1 → F0 → S0 → S1 → S2 → S3 → S4 → D1
```

Donde:

- `B-1` = baseline y rama de trabajo.
- `F0` = reproducibilidad rápida.
- `S0` = inspección real de API SAM 3.
- `S1` = comparación de prompts de portería.
- `S2` = extracción de masks.
- `S3` = overlay de masks.
- `S4` = portería en schema/eventos/fallback.
- `D1` = video demo final.

---

## 4. Plan por bloques ajustado

---

## Bloque -1 — Rama, baseline y respaldo

**Prioridad:** obligatoria.
**Momento:** antes de modificar cualquier archivo.
**Objetivo:** proteger el estado actual, evitar regresiones difíciles de rastrear y verificar herramientas.

| ID | Tarea | Archivos / comandos | Resultado mínimo viable | Validación |
|---|---|---|---|---|
| B-1.1 | Crear rama separada de trabajo | `git checkout -b fix/master-audit-corrections` | Rama creada fuera de `main/master` | `git branch --show-current` devuelve `fix/master-audit-corrections` |
| B-1.2 | Ejecutar tests actuales | `python -m unittest discover -s tests` | Resultado registrado, aunque existan fallos | Guardar salida en `experiments/current_evaluation/baseline_tests.log` |
| B-1.3 | Ejecutar scripts principales actuales si funcionan | Scripts actuales de pipeline, tracking, dashboard o demo | Saber qué funciona antes de modificar | Guardar outputs o logs como baseline |
| B-1.4 | Crear reporte real del entorno MSI | Nuevo script o comandos documentados | `environment_report.md` creado | Debe confirmar RTX 4050, CUDA, PyTorch y Python |
| B-1.5 | **Verificar herramientas externas** (nuevo) | `ffmpeg -version`, `ffprobe -version`, `nvidia-smi` | Versiones registradas en `environment_report.md` | Si falta `ffmpeg`/`ffprobe`, registrar bloqueo del Bloque 2 desde ya |
| B-1.6 | Crear snapshot de referencia | `git status`, `git log --oneline -5`, outputs actuales | Estado inicial documentado | `experiments/current_evaluation/baseline_snapshot.md` |
| B-1.7 | **Crear estructura de continuidad** (nuevo) | `experiments/current_evaluation/closures/`, `PHASE_STATUS.md` | Carpeta de cierres y archivo de estado inicial | Archivos presentes y commiteados |

Criterio de cierre del bloque:

```text
No se modifica código funcional hasta tener rama separada, baseline de tests, snapshot,
reporte de entorno con herramientas verificadas y estructura de continuidad creada.
```

---

## Bloque 0 — Quick wins de reproducibilidad

**Prioridad:** crítica.
**Momento:** Día 1, después del baseline.
**Objetivo:** eliminar barreras básicas de reproducción sin tocar aún la lógica profunda del pipeline.

| ID | Tarea | Archivos | Resultado mínimo viable | Validación |
|---|---|---|---|---|
| F0-1 | Eliminar rutas absolutas | `configs/default.yaml`, `src/futbotmx/config.py` | Rutas reemplazadas por variables `${FUTBOTMX_VIDEO_*}` | `grep -n "/home/" configs/default.yaml` sin coincidencias en valores de configuración (ver nota de grep) |
| F0-2 | Expandir variables de entorno desde config según el mecanismo de la sección 2.7 | `src/futbotmx/config.py` | `load_config()` resuelve `${VAR}` y falla con mensaje claro si falta una variable | Test manual con variables exportadas y con una variable ausente |
| F0-3 | Crear plantillas locales | `configs/local_paths.example.yaml`, `.env.example` | Plantillas versionadas sin rutas reales privadas | Archivos presentes y documentados |
| F0-4 | **Higiene de `.gitignore`** (nuevo) | `.gitignore` | `.env` y `configs/local_paths.yaml` ignorados | `git check-ignore .env configs/local_paths.yaml` confirma; ningún archivo con rutas personales queda rastreado |
| F0-5 | Crear licencia y notices | `LICENSE`, `THIRD_PARTY_NOTICES.md` | Archivos presentes en raíz | README puede enlazarlos después |
| F0-6 | Corregir campo `project.level` | `configs/default.yaml` | El config deja de presentar un nivel como estado final | Sin `project.level: 2` como narrativa activa |
| F0-7 | Registrar dependencias reales instaladas | `experiments/current_evaluation/requirements-freeze.txt` | Snapshot de entorno real antes de pinear | `pip freeze` guardado como evidencia |

Notas:

- El pinning final no tiene que cerrarse en este bloque, pero sí debe registrarse el entorno real desde el inicio.
- No se debe romper `requirements-gpu.txt` sin probar instalación limpia en la MSI.
- **Nota de grep (nuevo):** el criterio es que no queden rutas absolutas personales en *valores de configuración* (videos, checkpoints, outputs). Coincidencias en comentarios o texto descriptivo se reportan y se justifican una por una; no se ocultan ni se eliminan silenciosamente.

---

## Bloque 1 — Segmentación real: inspección SAM 3, masks y portería

**Prioridad:** crítica.
**Momento:** Día 1 tarde – Día 3.
**Objetivo:** demostrar que SAM 3 produce segmentación verificable y que el proyecto cubre campo, robot, balón y portería.

### S0 — Inspección real de la API de SAM 3

Antes de implementar extracción de masks, no se debe asumir que la salida viene en `output.get("masks")`.

| ID | Tarea | Archivos | Resultado mínimo viable | Validación |
|---|---|---|---|---|
| S0-1 | Inspeccionar salida real de `Sam3Processor` | `scripts/inspect_sam3_output.py` o script temporal | Reporte con claves, shapes y tipos de salida | `experiments/current_evaluation/sam3_output_inspection.md` |
| S0-2 | Revisar ejemplos locales/oficiales incluidos en `.deps/sam3/` | `.deps/sam3/examples/` | Identificar método correcto para obtener masks | Notas técnicas en `sam3_output_inspection.md` |
| S0-3 | Definir estrategia de exportación | `sam3_segmenter.py`, `detections.py` | Elegir PNG, RLE o ambos | Decisión documentada antes de codificar |

Criterio de aceptación:

```text
No implementar S2 hasta confirmar la estructura real de salida de SAM 3.
```

### S1 — Comparación de prompts para portería

| ID | Tarea | Archivos | Resultado mínimo viable | Validación |
|---|---|---|---|---|
| S1 | Comparar prompts de portería en video real | `scripts/run_prompt_comparison.py`, `configs/default.yaml` | CSV con recall/confianza por prompt | `experiments/current_evaluation/goalpost_prompt_comparison/comparison.csv` |

Prompts mínimos:

```text
goal
soccer goal
goalpost
small soccer goal
robot soccer goal
```

Criterios de selección:

- Recall visual.
- Confianza promedio.
- Falsos positivos.
- Estabilidad entre frames.
- Utilidad para eventos de tiro/gol.

### S2 — Extraer masks de SAM 3

| ID | Tarea | Archivos | Resultado mínimo viable | Validación |
|---|---|---|---|---|
| S2 | Extraer masks usando la API real confirmada en S0 | `src/futbotmx/segmentation/sam3_segmenter.py`, `src/futbotmx/io/detections.py` | ≥1 frame con mask exportada | `detections.json` con `mask_path` no nulo y PNG/RLE válido |

Reglas:

- No hardcodear una clave de salida sin validarla.
- Guardar masks de forma controlada para no inflar el repo.
- Para muestras pequeñas: PNG es aceptable.
- Para muchas masks: RLE/COCO o manifest externo es preferible.
- `save_detections()` y `load_detections()` deben preservar `mask_path` (validar round-trip).

### S3 — Overlay de masks

| ID | Tarea | Archivos | Resultado mínimo viable | Validación |
|---|---|---|---|---|
| S3 | Crear overlay semitransparente de masks | `src/futbotmx/visualization/overlay.py` | ≥1 PNG con mask visible sobre frame real | Inspección visual: mask distinguible de bbox |

Requisitos:

- Función tipo `apply_mask_overlay()`.
- Alpha aproximado: 40-60%.
- Color por clase.
- Portería debe tener color diferenciado si se detecta.
- El overlay debe poder mostrarse en el video demo o dashboard.

### S4 — Portería en schema, overlays, eventos y fallback

| ID | Tarea | Archivos | Resultado mínimo viable | Validación |
|---|---|---|---|---|
| S4-1 | Agregar portería como clase | `configs/default.yaml`, schemas de detección | Clase `goalpost` o nombre elegido presente | `detections.json` puede contener portería |
| S4-2 | Usar portería en overlay | `overlay.py` | Portería visible si SAM 3 la detecta | PNG/frames con bbox/mask de portería |
| S4-3 | Integrar portería en eventos si es estable | `events/detector.py` | Eventos de tiro/gol pueden usar posición real de portería | Eventos documentan fuente: detección real o fallback |
| S4-4 | Implementar fallback geométrico si SAM 3 falla | `FieldModel`, `events/detector.py`, docs | Zona de portería estimada por modelo de campo | README/SAM3_PIPELINE aclara que es fallback, no mask real |

Regla de honestidad técnica:

```text
Si la portería no se detecta de forma confiable con SAM 3, no afirmar que está segmentada
consistentemente. Documentar el intento, resultados y fallback.
```

---

## Bloque 2 — Entrega visible: video demo

**Prioridad:** crítica.
**Momento:** Día 3 – Día 4.
**Objetivo:** entregar una evidencia visual clara, accesible y defendible.

| ID | Tarea | Archivos | Resultado mínimo viable | Validación |
|---|---|---|---|---|
| D1 | Generar video demo ≤2 min | `scripts/create_demo_video.py`, `outputs/videos/` | MP4 con tracking visible y al menos una mask SAM 3 | `ffprobe` confirma duración ≤120 s; reproducción completa |
| D2 | Incluir elementos técnicos clave | `outputs/videos/futbotmx_demo.mp4` | Tracking, masks, eventos, métricas y visualización táctica | Revisión manual completa |
| D3 | Definir entrega del MP4 | `README.md`, `ARTIFACTS_INDEX.md` | MP4 accesible o enlace público funcional | Jurado puede abrirlo sin pasos manuales complejos |
| D4 | **Confirmación visual del usuario** (nuevo — humano en el loop) | — | El usuario revisa el MP4 y confirma que es correcto y presentable | Registro de confirmación en el cierre de fase |

Contenido mínimo del demo:

- Frames reales del video.
- Bounding boxes/tracks.
- Al menos una sección con mask visible.
- Portería detectada o fallback visual claramente identificado.
- Métricas principales.
- Al menos una visualización táctica: Voronoi, heatmap, minimap o grafo.
- Duración máxima: 2 minutos.

Política de versionado:

- Si el MP4 pesa poco y las reglas lo permiten, puede ir en `outputs/videos/`.
- Si supera el tamaño razonable, usar enlace público o GitHub Release.
- Siempre incluir comando de regeneración en `ARTIFACTS_INDEX.md`.

---

## Bloque 3 — Team assignment y valor táctico

**Prioridad:** alta.
**Momento:** Día 4, paralelo al demo si es posible.
**Objetivo:** evitar que el análisis de aliados/rivales quede semánticamente vacío.

| ID | Tarea | Archivos | Resultado mínimo viable | Validación |
|---|---|---|---|---|
| T1 | Ejecutar `team_assignment.py` de forma aislada | `src/futbotmx/level3/team_assignment.py` o futuro `tactical/team_assignment.py` | Salida de asignación generada | CSV/JSON con equipos asignados |
| T2 | Conectar al pipeline post-tracking | `scripts/run_full_analysis.py`, `scripts/run_team_assignment.py` | Tracks con `team_A`/`team_B` o equivalente | `tracks.csv` no queda todo en `neutral` |
| T3 | Documentar método usado | `README.md`, `TECHNICAL_ARCHITECTURE.md` | Se aclara si es visual, heurístico o manual | No se sobrevende como modelo robusto si es fallback |

Estrategias aceptables:

1. Clasificación visual por color/crop si funciona.
2. Heurística por posición inicial si es razonable.
3. CSV manual validado para el clip principal si las dos anteriores fallan.

**Si se llega a la estrategia 3 (nuevo — humano en el loop):** el agente genera el CSV con los `track_id` del clip principal y un contactsheet de crops/frames marcados que permita identificar cada robot; el **usuario** asigna o valida los equipos. El agente no asigna equipos visualmente por su cuenta ni los presenta como validados.

Regla de honestidad:

```text
Si la asignación de equipo es heurística o manual, declararlo explícitamente.
```

---

## Bloque 4 — Documentación para evaluación

**Prioridad:** crítica.
**Momento:** después del Bloque 5 según el prompt de ejecución (las métricas alimentan los documentos finales); paralelizable si las métricas pendientes se marcan como tales.
**Objetivo:** que el evaluador encuentre demo, dashboard, métricas y evidencia en menos de 5 minutos.

| ID | Tarea | Archivos | Resultado mínimo viable |
|---|---|---|---|
| G1 | Crear `docs/EVALUATOR_GUIDE.md` | `docs/` | Guía de 1-2 páginas con acceso rápido a demo, dashboard y métricas |
| G2 | Reescribir README final | `README.md` | Sin narrativa de niveles ni flujo dual de hardware |
| G3 | Crear `docs/TECHNICAL_ARCHITECTURE.md` | `docs/` | Pipeline modular explicado por entradas/salidas |
| G4 | Crear `docs/SAM3_PIPELINE.md` | `docs/` | Explica prompts, masks, outputs, limitaciones y portería/fallback |
| G5 | Crear `docs/REPRODUCIBILITY.md` | `docs/` | Instalación y ejecución en MSI Ubuntu RTX 4050 |
| G6 | Crear `docs/RESULTS_SUMMARY.md` | `docs/` | Resultados finales con las métricas reales del Bloque 5; lo pendiente de anotación humana se marca como pendiente, no se estima |
| G7 | Crear índice de artefactos | `experiments/current_evaluation/ARTIFACTS_INDEX.md` | Manifest único de outputs finales |

README final debe incluir:

- Descripción breve del sistema.
- Arquitectura funcional.
- Entorno: MSI Ubuntu RTX 4050.
- Instalación.
- Configuración de variables de entorno (mecanismo de la sección 2.7).
- Modo GPU.
- Modo replay si existe.
- Enlace al video demo.
- Enlace al dashboard.
- Enlace a métricas/resultados.
- Licencia y notices.

**Nota de grep documental (nuevo):** al validar la ausencia de narrativa de niveles/flujo dual, las coincidencias dentro de `docs/archived/` o en contexto claramente histórico son aceptables; las coincidencias en narrativa activa no. Cada coincidencia se reporta y clasifica.

---

## Bloque 5 — Rigor profesional

**Prioridad:** alta para Categoría Profesional.
**Momento:** Día 5 – Día 7; según el prompt de ejecución, antes del Bloque 4 (documentación).
**Objetivo:** elevar la defensa técnica con métricas y benchmark.

| ID | Tarea | Archivos | Resultado mínimo viable | Validación |
|---|---|---|---|---|
| R1 | Infraestructura de mini ground truth | `data/annotations/` | Frames exportados + plantilla + instrucciones de anotación | Archivos presentes |
| R1-H | **Anotación humana** (nuevo — humano en el loop) | `data/annotations/` | 20-50 frames anotados por el usuario (o validados si fueron asistidos) | Anotaciones presentes y marcadas con su origen |
| R2 | Métricas supervisadas | `src/futbotmx/metrics/`, scripts nuevos | IoU/Dice/precision/recall/F1 por clase | CSV/JSON reproducible |
| R3 | Benchmark completo SAM 3 | `scripts/run_sam3_benchmark.py` | ms/frame, FPS, VRAM, CPU | `benchmark.json` actualizado |
| R4 | Pinning final de dependencias | `requirements-gpu.txt`, `requirements.txt`, opcional `constraints.txt` | Versiones exactas probadas | Instalación limpia en MSI |
| R5 | Validación completa del pipeline | `scripts/run_full_analysis.py` o `scripts/run_pipeline.py` | Pipeline corre de inicio a fin en MSI | Logs y outputs en `current_evaluation/` |

Notas sobre pinning:

- No pinear a ciegas.
- Usar el entorno real verificado como base.
- Probar instalación limpia antes de commitear.
- Agregar explícitamente: `einops`, `pycocotools`, `psutil` si son requeridos.

Nota sobre R1-H: el agente no fabrica anotaciones. Si la anotación humana no llega a tiempo, R2 se entrega con la infraestructura lista y el estado "pendiente de anotación", documentado así en `RESULTS_SUMMARY.md`.

---

## Bloque 6 — Limpieza de arquitectura y legado

**Prioridad:** media.
**Momento:** solo después de validar pipeline, demo y tests.
**Objetivo:** mejorar presentación sin romper funcionalidad.

| ID | Tarea | Riesgo | Mitigación |
|---|---|---|---|
| L1 | Migrar módulos `level2/level3` a nombres funcionales | Alto | Tests antes/después; aliases temporales |
| L2 | Renombrar scripts `run_level*` | Medio | Crear wrappers antes de archivar scripts viejos |
| L3 | Unificar checks en `scripts/validate_pipeline.py` | Medio | Conservar checks anteriores como referencia |
| L4 | Archivar experimentos legacy | Bajo | No eliminar nada; crear `experiments/archived/INDEX.md` |
| L5 | Archivar documentación obsoleta | Bajo | `docs/archived/` con índice |
| L6 | CI básico con GitHub Actions | Bajo | Workflow mínimo que no requiera GPU |
| L7 | Clip de muestra o enlace público | Bajo | Permitir replay o demo rápida sin videos privados |

Regla principal:

```text
Si el tiempo se agota, no hacer este bloque antes de entregar. Es preferible entregar
funcional y documentado que limpio pero roto.
```

---

## 5. Gates de entrega

Para evitar confundir "entrega mínima" con "entrega profesional fuerte", se definen dos gates.

---

## Gate A — Entrega mínima defendible

El proyecto puede entregarse si cumple estos puntos:

- [ ] Se trabajó en rama separada y no directamente en `main/master`.
- [ ] Existe trazabilidad de fases: cierres en `closures/` y `PHASE_STATUS.md` actualizado.
- [ ] Video demo ≤2 minutos accesible en repo, release o enlace público desde README, **con confirmación visual del usuario registrada**.
- [ ] SAM 3 produce al menos una mask pixel-level visible en frames de evaluación y/o demo.
- [ ] Portería incluida como clase intentada con evidencia de prompt comparison; si falla, fallback geométrico documentado.
- [ ] Robots clasificados por equipo en el clip principal o con CSV manual **validado por el usuario**; no todo queda como `neutral`.
- [ ] `configs/default.yaml` sin rutas absolutas; `configs/local_paths.example.yaml` versionado; `.env` y `local_paths.yaml` reales ignorados por Git.
- [ ] `docs/EVALUATOR_GUIDE.md` permite encontrar demo, dashboard y métricas en ≤5 minutos.
- [ ] `LICENSE` y `THIRD_PARTY_NOTICES.md` presentes.
- [ ] Tests existentes ejecutados y resultado documentado. Idealmente los 27 tests pasan.

> Nota: si algún test falla por estado previo del proyecto, debe documentarse con evidencia. No se debe ocultar.

---

## Gate B — Entrega profesional fuerte

Para maximizar probabilidad en Categoría Profesional, además del Gate A se debe cumplir:

- [ ] Los 27 tests pasan sin regresiones.
- [ ] Benchmark SAM 3 incluye ms/frame, FPS efectivo, VRAM y CPU.
- [ ] Mini ground truth disponible con 20-50 frames **anotados o validados por el usuario**.
- [ ] Métricas IoU/Dice/precision/recall/F1 por clase publicadas.
- [ ] `docs/RESULTS_SUMMARY.md` resume métricas, limitaciones y evidencias.
- [ ] `requirements-gpu.txt` o `constraints.txt` tiene versiones probadas.
- [ ] Pipeline completo o modo replay validado en MSI RTX 4050.
- [ ] `experiments/current_evaluation/ARTIFACTS_INDEX.md` contiene todos los outputs finales.

---

## 6. Criterios de aceptación por área

| Área | Criterio de aceptación | Evidencia requerida |
|---|---|---|
| Rama de trabajo | Correcciones hechas fuera de `main/master` | `git branch --show-current`, commits en rama `fix/master-audit-corrections` |
| Continuidad | Cierres de fase versionados y estado vivo | `closures/FASE_X_cierre.md`, `PHASE_STATUS.md` |
| Entorno | MSI Ubuntu RTX 4050 documentada con herramientas verificadas | `environment_report.md` (incl. ffmpeg/ffprobe) |
| Reproducibilidad | Config sin rutas absolutas y archivos locales ignorados | `configs/default.yaml`, `local_paths.example.yaml`, `.env.example`, `.gitignore` |
| SAM 3 masks | `mask_path` no nulo en detecciones de muestra | `detections.json`, PNG/RLE de mask, `sam3_output_inspection.md` |
| Overlay | Máscara visible sobre frame real | PNG/frames de evaluación |
| Portería | Prompt comparison ejecutado y fallback documentado si aplica | `goalpost_prompt_comparison/comparison.csv`, `SAM3_PIPELINE.md` |
| Team assignment | Robots no quedan todos como `neutral`; método declarado | `tracks.csv` o archivo de asignación validado |
| Demo | MP4 ≤2 min reproducible/accesible y confirmado por el usuario | `outputs/videos/futbotmx_demo.mp4` o enlace público |
| Métricas | Métricas operativas y/o supervisadas publicadas (o pendientes declaradas) | CSV/JSON + `RESULTS_SUMMARY.md` |
| Benchmark | FPS, ms/frame y VRAM medidos | `benchmark.json` |
| Documentación | Evaluador encuentra todo en ≤5 min | `EVALUATOR_GUIDE.md`, `ARTIFACTS_INDEX.md` |
| Licencias | Proyecto y terceros atribuidos | `LICENSE`, `THIRD_PARTY_NOTICES.md` |

---

## 7. Riesgos restantes y mitigaciones

| Riesgo | Probabilidad | Impacto | Mitigación |
|---|---|---|---|
| SAM 3 no expone masks como `output.get("masks")` | Media | Alto | Inspeccionar API real antes de implementar (S0). No hardcodear estructura no confirmada |
| SAM 3 no detecta portería consistentemente | Media | Alto | Comparar prompts. Si falla, usar fallback geométrico documentado |
| Masks aumentan mucho el peso del repo | Media | Medio | Exportar solo muestra evaluable; usar RLE/COCO para el resto |
| MP4 supera 50 MB | Media | Medio | Usar GitHub Release, Drive público o enlace documentado |
| Pinning rompe instalación | Media | Alto | Registrar entorno real, probar instalación limpia y usar constraints si hace falta |
| Team assignment por color no es robusto | Media | Medio | Fallback por posición o CSV manual validado por el usuario, documentándolo |
| Renombrar niveles rompe imports/tests | Alta | Alto | Hacer al final, con aliases temporales y tests antes/después |
| Cambios directos en `main/master` complican rollback | Alta si no se controla | Alto | Rama obligatoria y commits pequeños por bloque |
| Sesión del agente se reinicia a mitad de fase | Media | Alto | Protocolo de continuidad (sección 2.2): cierres versionados + `PHASE_STATUS.md` + protocolo de reanudación |
| Rutas personales se filtran por `.env` o config local | Media | Medio | Higiene de `.gitignore` en Bloque 0 (F0-4) verificada con `git check-ignore` |
| `ffmpeg`/`ffprobe` ausentes al llegar al demo | Baja | Alto | Verificación de herramientas en el baseline (B-1.5) |
| El agente fabrica anotaciones o asignaciones manuales | Baja | Crítico | Regla de humano en el loop (sección 2.3): el agente prepara, el usuario anota/valida |

---

## 8. Checklist final de cierre

### Seguridad de trabajo y continuidad

- [ ] Se creó rama distinta: `fix/master-audit-corrections` o equivalente.
- [ ] No se trabajó directamente en `main/master`.
- [ ] Se guardó baseline de tests.
- [ ] Se guardó baseline de outputs actuales.
- [ ] Se generó `environment_report.md` confirmando MSI Ubuntu RTX 4050 y herramientas (ffmpeg/ffprobe/nvidia-smi).
- [ ] Cierres de fase guardados en `closures/` y `PHASE_STATUS.md` actualizado.

### Reproducibilidad

- [ ] `configs/default.yaml` no contiene rutas absolutas personales en valores de configuración.
- [ ] `configs/local_paths.example.yaml` existe.
- [ ] `.env.example` existe si aplica.
- [ ] `.env` y `configs/local_paths.yaml` están en `.gitignore` y no rastreados.
- [ ] `LICENSE` existe.
- [ ] `THIRD_PARTY_NOTICES.md` existe.
- [ ] Dependencias reales registradas.
- [ ] Dependencias finales pinadas/probadas.

### Segmentación

- [ ] API real de SAM 3 inspeccionada y documentada (`sam3_output_inspection.md`).
- [ ] Masks exportadas o representación equivalente.
- [ ] `mask_path` no queda nulo en muestra evaluable (round-trip validado).
- [ ] Overlay semitransparente funcionando.
- [ ] Portería evaluada con prompts.
- [ ] Portería segmentada o fallback documentado.

### Demo y artefactos

- [ ] Video demo ≤2 minutos generado y validado con `ffprobe`.
- [ ] Demo confirmado visualmente por el usuario.
- [ ] Demo accesible desde README.
- [ ] Dashboard enlazado o documentado.
- [ ] `ARTIFACTS_INDEX.md` creado.
- [ ] Outputs finales en `experiments/current_evaluation/`.

### Valor táctico

- [ ] Team assignment conectado.
- [ ] Robots no quedan todos como `neutral`.
- [ ] Método de asignación documentado (y validado por el usuario si fue manual).
- [ ] Eventos y métricas actualizados si aplica.

### Documentación

- [ ] `README.md` actualizado sin narrativa activa de niveles ni flujo dual de equipos.
- [ ] `docs/EVALUATOR_GUIDE.md` creado.
- [ ] `docs/TECHNICAL_ARCHITECTURE.md` creado.
- [ ] `docs/SAM3_PIPELINE.md` creado.
- [ ] `docs/REPRODUCIBILITY.md` creado.
- [ ] `docs/RESULTS_SUMMARY.md` creado (con pendientes declarados si los hay).

### Calidad profesional

- [ ] Infraestructura de mini ground truth creada.
- [ ] Ground truth anotado o validado por el usuario (o pendiente declarado).
- [ ] IoU/Dice/precision/recall/F1 reportados.
- [ ] Benchmark incluye FPS, ms/frame y VRAM.
- [ ] Tests ejecutados después de cambios.
- [ ] Los 27 tests pasan o fallos previos están documentados.
- [ ] Refactor de niveles solo se ejecutó después de validar pipeline.

---

## 9. Recomendación final de ejecución

La ejecución debe respetar esta prioridad:

```text
1. Rama separada, baseline y verificación de herramientas.
2. Config portable (con .gitignore) y entorno MSI RTX 4050 documentado.
3. Inspección real de SAM 3.
4. Masks exportadas y overlay visible.
5. Portería con prompt comparison y fallback si aplica.
6. Demo final ≤2 minutos con confirmación visual del usuario.
7. Team assignment (con validación humana si es manual).
8. Métricas supervisadas y benchmark (con anotación humana del ground truth).
9. Guía de evaluador y README final con métricas reales.
10. Limpieza de niveles y CI solo si el pipeline ya está estable.
```

La regla principal del proyecto debe ser:

> Primero hacer el sistema reproducible, demostrable y honesto técnicamente. Después hacerlo elegante internamente.

No se debe sacrificar una entrega funcional por un refactor de nombres o carpetas. Si el tiempo se reduce, cumplir Gate A. Si el tiempo lo permite, avanzar a Gate B.