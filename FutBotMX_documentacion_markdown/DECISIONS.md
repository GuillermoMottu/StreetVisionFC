# DECISIONS

Este documento registra decisiones técnicas importantes del proyecto FutBotMX.

---

## DEC-001 - Mantener los 3 niveles del proyecto

**Estado:** Aprobada

**Contexto:**  
Se decidió no eliminar ningún nivel del alcance original del proyecto.

**Decisión:**  
Los niveles se conservarán como alcance progresivo:

- Nivel 1: MVP obligatorio.
- Nivel 2: extensión intermedia.
- Nivel 3: extensión avanzada.

**Consecuencia:**  
Nivel 1 será obligatorio. Nivel 2 y Nivel 3 dependerán del avance real, estabilidad del pipeline y tiempo disponible.

---

## DEC-002 - Usar implementación progresiva

**Estado:** Aprobada

**Contexto:**  
El proyecto tiene elementos avanzados, pero depende primero de lograr segmentación y tracking confiables.

**Decisión:**  
Se implementará primero Nivel 1 antes de avanzar a Nivel 2 o Nivel 3.

**Consecuencia:**  
No se deben desarrollar visualizaciones avanzadas si el pipeline base aún no funciona.

---

## DEC-003 - Usar escritorio como estación principal de desarrollo

**Estado:** Aprobada

**Contexto:**  
El escritorio cuenta con Codex y Claude Desktop, pero tiene una GPU GT 1030 de 2 GB.

**Decisión:**  
El escritorio será usado para desarrollo, documentación, análisis de resultados, eventos y preparación de entregables.

**Consecuencia:**  
No será la máquina principal para inferencia pesada con SAM 3.

---

## DEC-004 - Usar laptop MSI como estación de inferencia

**Estado:** Aprobada

**Contexto:**  
La laptop MSI cuenta con RTX 4050 y Ubuntu/Linux.

**Decisión:**  
La laptop será usada para SAM 3, segmentación, tracking, overlays, benchmarks y generación de resultados pesados.

**Consecuencia:**  
Las pruebas pesadas se ejecutarán en laptop y se subirán a GitHub solo resultados ligeros.

---

## DEC-005 - Usar GitHub como integración principal

**Estado:** Aprobada

**Contexto:**  
Se requiere sincronización clara entre escritorio y laptop.

**Decisión:**  
GitHub será el centro de integración del proyecto.

**Consecuencia:**  
Todo cambio de equipo debe pasar por commit, push y pull.

---

## DEC-006 - No usar Obsidian

**Estado:** Aprobada

**Contexto:**  
Se decidió mantener trazabilidad dentro del repositorio.

**Decisión:**  
No se usará Obsidian para la documentación técnica principal.

**Consecuencia:**  
Bitácoras, decisiones, errores y resultados ligeros se documentarán en Markdown dentro de GitHub.

---

## DEC-007 - No subir archivos pesados a GitHub

**Estado:** Aprobada

**Contexto:**  
Los videos, frames, máscaras y checkpoints pueden ser demasiado pesados.

**Decisión:**  
Solo se subirán archivos ligeros y reproducibles.

**Consecuencia:**  
Los archivos pesados se conservarán localmente o en almacenamiento externo si se decide después.

---

## DEC-008 - Documentar pruebas dentro del repositorio

**Estado:** Aprobada

**Contexto:**  
Se necesita trazabilidad técnica.

**Decisión:**  
Cada prueba relevante tendrá registro en `TESTING_LOG.md` o en `experiments/test_xxx/summary.md`.

**Consecuencia:**  
No se considerará válida una prueba sin evidencia documentada.

---

## DEC-009 - Validar SAM 3 antes de módulos avanzados

**Estado:** Aprobada

**Contexto:**  
SAM 3 es la tecnología base del proyecto.

**Decisión:**  
Antes de desarrollar Nivel 2 o Nivel 3, se debe validar SAM 3 en la laptop MSI.

**Consecuencia:**  
No se debe afirmar que SAM 3 funciona hasta tener evidencia en `experiments/`.

---

## DEC-010 - Desbloquear Nivel 2

**Estado:** Aprobada

**Contexto:**
Nivel 1 cuenta con evidencia real de SAM 3, tracking ByteTrack, eventos Nivel 1, demo local no versionada, paquete de evidencia ligera y reporte automatico con `10 pass`, `0 warn`, `0 fail`.

**Decisión:**
Nivel 2 queda desbloqueado para planeacion e implementacion inicial. El trabajo debe empezar por metricas deportivas intermedias, eventos intermedios y visualizaciones ligeras, usando `docs/TODO_LEVEL2.md` como checklist operativo.

**Consecuencia:**
Nivel 3 permanece bloqueado hasta que Nivel 2 tenga resultados documentados. Los videos/checkpoints siguen fuera de Git.

---

## DEC-011 - Cierre tecnico Nivel 2 y gate hacia Nivel 3

**Estado:** Aprobada

**Contexto:**
Nivel 2 ya cuenta con metricas, eventos, visualizaciones, comparacion multi-clip y demo ligera. Antes de iniciar Nivel 3 se requiere cerrar discrepancias de documentacion, corregir deudas tecnicas y generar un gate reproducible de cierre.

**Decision:**
Nivel 2 se considera cerrado solo si `scripts/check_level2_closure.py` pasa con evidencia densa para clips candidatos, diagnostico formal de `video_480`, tests verdes y sin archivos pesados versionados.

**Consecuencia:**
Nivel 3 queda listo para gate/decision, no iniciado automaticamente. La rectificacion/homografia queda como recomendacion para Nivel 3, no requisito de cierre Nivel 2.
