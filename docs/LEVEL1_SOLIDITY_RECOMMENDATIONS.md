# Recomendaciones Para Solidificar Nivel 1

Estas cinco recomendaciones dejan Nivel 1 mas defendible antes de abrir Nivel 2. No bloquean la evidencia actual, pero reducen ambiguedad tecnica y mejoran la reproducibilidad.

## 1. Sincronizar la documentacion operativa

`docs/TASK_LIST_DETAILED.md` debe reflejar que la segmentacion real de campo ya fue validada con `green soccer field` y que la evidencia ligera final existe en `experiments/evidence_level1/`.

Impacto: evita contradicciones entre el checklist general y el TODO de laptop.

## 2. Crear validacion automatica de solidez Nivel 1

Agregar un reporte que lea artefactos existentes y valide recall temporal, prompt de cancha, estabilidad de ByteTrack, eventos Nivel 1, clips adicionales, benchmark MSI y politica de archivos pesados.

Impacto: permite revisar si Nivel 1 sigue sano sin rerun pesado de SAM 3.

Estado: implementado con `scripts/run_level1_validation_report.py`.

## 3. Hacer reproducible el paquete de evidencia ligera

El paquete `experiments/evidence_level1/` debe poder reconstruirse desde artefactos canonicos ya generados.

Impacto: reduce trabajo manual y hace la entrega regenerable en escritorio o laptop.

Estado: implementado con `scripts/build_level1_evidence_package.py`.

## 4. Agregar limpieza de detecciones antes de eventos

Implementar deduplicacion/NMS o seleccion top-k por clase para resolver duplicados puntuales en `video_595` y multiples candidatos de robot en `video_667`.

Impacto: mejora tracking/eventos cuando se escale a mas clips.

Estado: recomendado para el siguiente ciclo antes de eventos multi-clip.

## 5. Preparar demo local no versionada

Generar un video corto anotado o secuencia de frames para `video_836` frames `120-180`, dejando fuera de Git el video completo y versionando solo capturas ligeras/metadata.

Impacto: mejora comunicacion visual del MVP sin cargar el repositorio.

Estado: recomendado para cierre de demo; no bloquea validacion tecnica.
