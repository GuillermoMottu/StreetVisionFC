# FutBotMX — Development Rules

## 1. Propósito

Este documento define reglas estrictas de desarrollo para FutBotMX.

Aplica para:

- Desarrolladores humanos.
- ChatGPT.
- Codex.
- Claude Desktop.
- Cualquier agente IA que edite código, documentación o configuración.

---

# 2. Reglas de alcance

1. No eliminar Nivel 1, Nivel 2 ni Nivel 3.
2. Nivel 1 es obligatorio.
3. Nivel 2 solo puede iniciarse cuando Nivel 1 tenga resultados documentados.
4. Nivel 3 solo puede iniciarse cuando Nivel 2 tenga resultados documentados.
5. No agregar arquitectura SaaS, cloud compleja o producto comercial.
6. No cambiar SAM 3 como tecnología base sin aprobación.
7. No declarar funciones como terminadas sin evidencia.

---

# 3. Reglas por equipo

## Escritorio

Debe usarse para:

- Desarrollo.
- Documentación.
- Codex.
- Claude Desktop.
- Revisión de resultados.
- Análisis de CSV/JSON.
- Ajuste de eventos.
- Preparación de README.
- Preparación de entregables.

No debe usarse para:

- Inferencia pesada SAM 3.
- Generación masiva de máscaras.
- Render pesado de videos.
- Benchmarks principales.

## Laptop MSI

Debe usarse para:

- SAM 3.
- Segmentación.
- Tracking pesado.
- Overlays.
- Videos anotados.
- Benchmarks.
- Pruebas con GPU.

No debe usarse como único lugar de documentación. Los resultados deben sincronizarse en GitHub.

---

# 4. Reglas de GitHub

1. Todo cambio de equipo debe pasar por commit, push y pull.
2. Antes de trabajar:

```bash
git pull origin main
```

3. Antes de cambiar de equipo:

```bash
git status
git add .
git commit -m "tipo: descripción"
git push origin main
```

4. Toda ejecución en laptop debe registrar commit hash.
5. No trabajar en el mismo archivo simultáneamente en ambos equipos.
6. Los resultados ligeros deben ir en `experiments/`.

---

# 5. Reglas sobre archivos pesados

No subir a GitHub:

- Modelos.
- Checkpoints.
- Videos pesados.
- Datasets completos.
- Frames masivos.
- Máscaras masivas.
- `.npy` grandes.
- Cachés.
- Entornos virtuales.
- Outputs pesados.

Sí subir:

- Código.
- Configuración.
- Documentación.
- Summaries.
- Logs resumidos.
- Métricas CSV.
- Eventos JSON.
- Capturas ligeras.
- Thumbnails.

---

# 6. Reglas de pruebas

1. Toda prueba pesada debe documentarse.
2. Usar `TESTING_LOG.md` o `experiments/test_xxx/summary.md`.
3. Toda prueba debe indicar:
   - Fecha.
   - Equipo.
   - Commit hash.
   - Configuración.
   - Video local usado.
   - Resultados.
   - Archivos subidos.
   - Archivos no subidos.
   - Conclusión.
   - Siguiente acción.
4. No declarar que SAM 3 funciona hasta tener evidencia documentada.
5. No modificar umbrales sin registrar la razón.
6. Toda configuración usada debe guardarse como `config.yaml` dentro de la carpeta de experimento.

---

# 7. Reglas para agentes IA

Un agente IA debe:

- Leer `PROJECT_SCOPE.md`.
- Leer `TASK_BREAKDOWN.md`.
- Leer `DEVELOPMENT_RULES.md`.
- Mantener los 3 niveles.
- Respetar el flujo escritorio/laptop.
- No inventar resultados.
- No marcar pruebas como exitosas si no existen.
- No crear dependencias innecesarias.
- No cambiar rutas sin actualizar documentación.
- No modificar esquemas JSON sin actualizar `EVENTS_DEFINITION.md`.
- No avanzar a Nivel 2 sin evidencia de Nivel 1.
- No avanzar a Nivel 3 sin evidencia de Nivel 2.

---

# 8. Estructura recomendada

```text
FutBotMX/
├── README.md
├── requirements-dev.txt
├── requirements-gpu.txt
├── .gitignore
├── configs/
├── data/
├── docs/
├── experiments/
├── outputs/
├── scripts/
├── src/
└── tests/
```

---

# 9. Convenciones de commits

Usar:

```text
tipo: descripción breve
```

Tipos:

```text
feat
fix
docs
refactor
test
config
exp
demo
```

Ejemplos:

```bash
git commit -m "docs: add dual machine workflow"
git commit -m "feat: add SAM3 test script"
git commit -m "exp: add tracking test 003 results"
git commit -m "fix: correct possession threshold handling"
```

---

# 10. Reglas de configuración

1. Usar YAML.
2. No hardcodear rutas.
3. Registrar configuración usada en cada prueba.
4. Mantener umbrales documentados.
5. Si se cambia un umbral, registrar motivo en `summary.md` o `DECISIONS.md`.

---

# 11. Regla de reproducibilidad

Una prueba debe poder reconstruirse a partir de:

- Commit hash.
- Configuración YAML.
- Script usado.
- Descripción del video local.
- Resultados ligeros.
- Notas de ejecución.
