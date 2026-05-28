# FutBotMX — Project Scope

## 1. Nombre del proyecto

**FutBotMX**

Proyecto de visión por computadora aplicado al análisis de videos de partidos de fútbol robótico usando **SAM 3** como tecnología base de segmentación.

---

## 2. Propósito

FutBotMX busca construir un pipeline reproducible que procese videos de fútbol robótico para segmentar, rastrear, analizar y visualizar elementos clave del partido: campo de juego, robots aliados, robots rivales, balón, trayectorias, eventos deportivos y visualizaciones tácticas/narrativas.

El proyecto está orientado a cumplir la convocatoria **Copa FutBotMX — Capítulo Visión por Computadora**, no a convertirse en producto SaaS, plataforma empresarial o solución comercial compleja.

---

## 3. Problema que resuelve

Los videos de fútbol robótico contienen información útil sobre posesión, trayectorias, zonas de actividad, tiros, pases, colisiones e interacciones entre robots, pero dicha información no está estructurada ni visualizada automáticamente.

FutBotMX resuelve este problema mediante un pipeline que:

1. Procesa videos de partidos.
2. Usa SAM 3 para segmentar objetos relevantes.
3. Aplica tracking para mantener IDs.
4. Detecta eventos deportivos mediante reglas heurísticas.
5. Genera visualizaciones comprensibles.
6. Exporta resultados ligeros y reproducibles para documentación y evaluación.

---

## 4. Objetivo general

Desarrollar un pipeline funcional de visión por computadora para analizar partidos de fútbol robótico usando SAM 3, tracking y detección de eventos, generando visualizaciones deportivas útiles y documentación suficiente para reproducir el proyecto desde GitHub.

---

## 5. Objetivos específicos

- Cargar videos locales de fútbol robótico.
- Extraer frames y metadatos básicos.
- Ejecutar segmentación con SAM 3 sobre campo, robots y balón.
- Normalizar detecciones para tracking.
- Generar trayectorias de robots y balón.
- Detectar eventos deportivos básicos.
- Exportar resultados en JSON, CSV, imágenes y video anotado.
- Documentar pruebas, errores, decisiones y resultados dentro del repositorio.
- Usar GitHub como mecanismo central de sincronización entre equipos.
- Mantener una implementación progresiva en 3 niveles.

---

# 6. Alcance progresivo por niveles

El proyecto conserva los **3 niveles definidos originalmente**. No se elimina ningún nivel.

La implementación será progresiva:

- **Nivel 1:** MVP obligatorio y primera meta funcional.
- **Nivel 2:** extensión intermedia si Nivel 1 queda estable.
- **Nivel 3:** extensión avanzada solo si el pipeline base funciona correctamente y el tiempo lo permite.

---

## 6.1 Nivel 1 — MVP obligatorio

El Nivel 1 es la meta mínima obligatoria del proyecto.

### Objetivo

Construir un pipeline funcional de extremo a extremo que procese un video corto y genere resultados mínimos verificables.

### Funcionalidades incluidas

| Área | Funcionalidad |
|---|---|
| Ingesta | Cargar video local y extraer frames |
| Segmentación | Usar SAM 3 para segmentar campo, robots y balón |
| Tracking | Mantener IDs básicos de robots y balón |
| Eventos | Detectar posesión, tiro aproximado, pase simple y colisión básica |
| Visualizaciones | Overlay, IDs, trails simples, mapa de calor básico |
| Exportación | `tracks.csv`, `events.json`, capturas ligeras y resumen markdown |
| Documentación | README, bitácora de pruebas, decisiones y errores |

### Criterio de éxito del Nivel 1

El Nivel 1 se considera estable cuando:

- Existe al menos una prueba documentada en `experiments/test_xxx/summary.md`.
- SAM 3 fue ejecutado en la laptop MSI con evidencia documentada.
- Se genera al menos un CSV de trayectorias.
- Se genera al menos un JSON de eventos.
- Existe al menos una captura ligera del overlay.
- El README permite reproducir el flujo básico.
- Los errores principales están documentados en `ERRORS_AND_FIXES.md`.

---

## 6.2 Nivel 2 — Extensión intermedia

El Nivel 2 no se elimina, pero solo debe iniciarse cuando el Nivel 1 tenga una prueba funcional documentada.

### Objetivo

Mejorar la calidad del análisis deportivo y de las visualizaciones.

### Funcionalidades incluidas

| Área | Funcionalidad |
|---|---|
| Eventos | Intercepción, recuperación, zona de actividad, jugada destacada |
| Métricas | Posesión temporal, distancia recorrida, velocidad aproximada |
| Visualizaciones | Timeline de eventos, posesión por equipo, mapas de calor separados |
| Tracking | Suavizado de trayectorias y manejo básico de pérdidas |
| Exportación | Resumen de métricas en CSV/JSON/Markdown |
| Demo | Video anotado más claro y capturas seleccionadas |

### Condiciones para avanzar a Nivel 2

- Nivel 1 ejecutado exitosamente en laptop MSI.
- Resultados ligeros subidos a GitHub.
- Commit hash registrado en `TESTING_LOG.md`.
- Configuración usada guardada en `experiments/test_xxx/config.yaml`.
- Validación humana de al menos una prueba de segmentación/tracking.
- Documentación de errores principales.

---

## 6.3 Nivel 3 — Extensión avanzada

El Nivel 3 representa el máximo alcance deseable. Solo debe abordarse si Nivel 1 y Nivel 2 están estables.

### Objetivo

Generar una demo más destacada con visualizaciones avanzadas y narrativa deportiva.

### Funcionalidades incluidas

| Área | Funcionalidad |
|---|---|
| Visualización avanzada | Diagramas de Voronoi, grafos de interacción, mini-mapa |
| Narrativa | Anotaciones deportivas más expresivas |
| Highlights | Detección y exportación de jugadas destacadas |
| Dashboard | Resumen visual del partido |
| Reel/demo | Material final para presentación |
| Análisis táctico | Control espacial aproximado e interacción entre robots |

### Condiciones para avanzar a Nivel 3

- Nivel 2 documentado con resultados.
- Eventos intermedios funcionando con evidencia.
- Visualizaciones mínimas ya generadas.
- Pipeline reproducible desde GitHub.
- No existen errores críticos pendientes en segmentación o tracking.
- Hay tiempo suficiente para implementar sin comprometer entrega final.

---

# 7. Estrategia de ejecución con dos equipos

El desarrollo de FutBotMX se realizará usando dos equipos con responsabilidades separadas.

## 7.1 Equipo de escritorio

### Hardware

- Intel Core i7-12700.
- 16 GB RAM.
- NVIDIA GeForce GT 1030 2 GB.
- Windows.
- Codex.
- Claude Desktop.

### Rol principal

El escritorio será la estación principal para:

- Desarrollo de código ligero.
- Coordinación con agentes IA.
- Documentación.
- Revisión de resultados.
- Ajuste de lógica de eventos.
- README.
- Dashboard ligero.
- Preparación de entregables.
- Análisis de JSON, CSV y capturas generadas por la laptop.

### Restricción

El escritorio **no debe usarse como máquina principal de inferencia SAM 3**, debido a la GPU GT 1030 de 2 GB.

Puede usarse para pruebas mínimas de código, validación de estructura o análisis de resultados ligeros.

## 7.2 Laptop MSI Thin GF63 12VE

### Hardware

- Intel Core i5-12450H.
- 16 GB RAM.
- NVIDIA GeForce RTX 4050 Laptop GPU.
- Linux/Ubuntu.

### Rol principal

La laptop MSI será la estación de inferencia y pruebas pesadas. Debe usarse para:

- Ejecutar SAM 3.
- Pruebas de segmentación.
- Tracking pesado.
- Generación de máscaras.
- Generación de overlays.
- Benchmarks.
- Exportación de videos anotados.
- Generación de resultados preliminares de eventos.
- Pruebas con clips de mayor duración.

## 7.3 GitHub como centro de integración

GitHub será el mecanismo principal para sincronizar ambos equipos.

Se usará para versionar:

- Código fuente.
- Configuraciones.
- Scripts.
- Documentación.
- Bitácoras.
- Métricas ligeras.
- JSON de eventos.
- CSV de tracking.
- Capturas ligeras.
- Reportes markdown.

No se deben subir directamente archivos pesados como checkpoints de modelos, videos completos pesados, frames masivos, máscaras masivas, datasets completos, archivos `.npy` grandes u outputs de video pesados.

---

# 8. Entregables esperados

## Nivel 1 obligatorio

- Repositorio público en GitHub.
- README funcional.
- Código base.
- Configuración YAML.
- Script demo.
- Segmentación validada con SAM 3.
- Tracking básico.
- `tracks.csv`.
- `events.json`.
- Capturas ligeras.
- `TESTING_LOG.md`.
- `DECISIONS.md`.
- `ERRORS_AND_FIXES.md`.

## Nivel 2 deseable

- Eventos adicionales.
- Visualizaciones mejoradas.
- Timeline de posesión.
- Métricas resumidas.
- Reporte de resultados.
- Demo más clara.

## Nivel 3 avanzado

- Voronoi.
- Grafos de interacción.
- Highlights.
- Narrativa.
- Dashboard.
- Reel final.

---

# 9. Fuera de alcance

Queda fuera del alcance inicial:

- SaaS.
- Arquitectura cloud compleja.
- App móvil.
- Streaming en tiempo real.
- Sistema multiusuario.
- Fine-tuning obligatorio.
- Arbitraje automático completo.
- Reconocimiento perfecto de reglas oficiales.
- Subida de datasets pesados a GitHub.
- Uso de Obsidian como bitácora técnica principal.

---

# 10. Supuestos iniciales

| Supuesto | Estado |
|---|---|
| Se cuenta con al menos un video local de prueba | Pendiente de validación |
| SAM 3 puede ejecutarse en la laptop MSI | Pendiente de validación |
| La RTX 4050 permite pruebas de inferencia razonables | Pendiente de benchmark |
| GitHub será el centro de sincronización | Aprobado |
| No se usará Obsidian | Aprobado |
| El escritorio se usará para desarrollo y documentación | Aprobado |
| La laptop se usará para inferencia pesada | Aprobado |
| Nivel 1 es obligatorio | Aprobado |
| Nivel 2 y Nivel 3 dependen del avance real | Aprobado |
