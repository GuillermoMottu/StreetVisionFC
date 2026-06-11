# Cierre de Fase 1 — Reproducibilidad rápida

## 1. Resumen de cambios

- Eliminadas rutas absolutas (`/home/guillermo/Vídeos/...`) de `configs/default.yaml`; reemplazadas por `${FUTBOTMX_VIDEO_595}`, `${FUTBOTMX_VIDEO_667}`, `${FUTBOTMX_VIDEO_480}`
- Eliminado `project.level: 2` de `default.yaml` (campo no referenciado en código; narrativa de nivel eliminada)
- Actualizado `src/futbotmx/config.py`: expansión de `${VAR}` via `os.path.expandvars`, soporte opcional de `.env` (con fallback manual si `python-dotenv` no está instalado), y fallo explícito con mensaje claro cuando falta una variable
- Creados `configs/local_paths.example.yaml` y `.env.example` como plantillas de documentación
- Actualizado `.gitignore`: añadidos `.env` y `configs/local_paths.yaml` (verificado con `git check-ignore`)
- Creados `LICENSE` (MIT, 2026 Guillermo Mottu) y `THIRD_PARTY_NOTICES.md` (SAM3, PyTorch, OpenCV, supervision, ByteTrack, NumPy, pandas, matplotlib, Pillow, pycocotools, einops, scipy, psutil, timm, PyYAML, tqdm)

## 2. Archivos modificados

| Archivo | Cambio realizado | Motivo |
|---|---|---|
| `configs/default.yaml` | Rutas absolutas → `${FUTBOTMX_VIDEO_*}`; eliminado `project.level: 2` | Portabilidad (brecha C4) |
| `src/futbotmx/config.py` | Añadida expansión de env vars, carga de `.env`, fallo explícito con mensaje claro | Reproducibilidad |
| `.gitignore` | Añadidos `.env` y `configs/local_paths.yaml` | Evitar que rutas privadas lleguen a git |
| `configs/local_paths.example.yaml` | Creado — plantilla de variables de entorno | Documentación de reproducibilidad |
| `.env.example` | Creado — plantilla `.env` | Documentación de reproducibilidad |
| `LICENSE` | Creado — MIT License, 2026 Guillermo Mottu | Requisito brecha alta (Bloque 0) |
| `THIRD_PARTY_NOTICES.md` | Creado — 16 dependencias documentadas | Requisito brecha alta (Bloque 0) |

## 3. Pruebas ejecutadas

| Comando | Resultado | Evidencia/log |
|---|---|---|
| `grep -n "/home/" configs/default.yaml` | Sin coincidencias — OK | Terminal |
| `git check-ignore .env configs/local_paths.yaml` | Ambos ignorados — OK | `.gitignore` líneas 58-59 |
| `python3 -m unittest discover -s tests` | FAILED (errors=21) — mismo set que baseline | Sin regresiones |
| `load_config()` sin env vars definidas | `EnvironmentError` con mensaje claro (PASS) | Test funcional inline |
| `load_config()` con env vars definidas | Config expandida correctamente (PASS) | Test funcional inline |

## 4. Validación QA

| Criterio | Estado | Observaciones |
|---|---|---|
| Tests ejecutados | Cumplido | 268 tests, 21 errores — idénticos al baseline |
| Sin regresiones detectadas | Cumplido | Error set exactamente igual que en `baseline_tests.txt` |
| `default.yaml` sin rutas privadas en valores | Cumplido | `grep -n "/home/"` sin coincidencias |
| `configs/local_paths.example.yaml` existe | Cumplido | Creado |
| `.env.example` existe | Cumplido | Creado |
| `.env` y `configs/local_paths.yaml` en `.gitignore` | Cumplido | Verificado con `git check-ignore -v` |
| `load_config()` expande vars y falla con mensaje claro | Cumplido | Dos tests funcionales pasados |
| `LICENSE` existe | Cumplido | MIT License, 2026 |
| `THIRD_PARTY_NOTICES.md` existe | Cumplido | 16 dependencias documentadas |
| `project.level: 2` eliminado | Cumplido | No referenciado en código |

### Nota sobre grep de rutas absolutas

El grep `grep -n "/home/" configs/default.yaml` no arrojó ninguna coincidencia en valores de configuración. La sección `level2_closure.clips[*].video` ahora contiene `${FUTBOTMX_VIDEO_*}`. No hay rutas privadas en comentarios ni en texto descriptivo del YAML.

## 5. Riesgos o pendientes

- **BLOQUEO Fase 3 persiste:** `ffmpeg`/`ffprobe` no instalados. Requiere `sudo apt-get install ffmpeg` antes de iniciar Fase 3.
- **21 errores de test pre-existentes:** Sin cambio respecto al baseline. Causa: paquetes del sistema Python vs. `.venv` (ver Fase 0).
- **`python-dotenv` no está instalado:** El fallback manual de lectura de `.env` está implementado y funciona. Si se desea soporte más robusto (variables multilínea, etc.), instalar `pip install python-dotenv`.
- **`project.level` en pyproject.toml:** No existía en `pyproject.toml`, solo en `default.yaml`. Eliminado. Si algún script externo dependía de ese campo, registrar como regresión al detectarlo.

## 6. Tareas pendientes del usuario (humano en el loop)

- Ninguna para esta fase.
- **Recordatorio Fase 3:** instalar `ffmpeg` con `sudo apt-get install ffmpeg` antes de aprobar la Fase 3.

## 7. Recomendación

**La fase está lista para aprobación.** La config es portable, los archivos legales existen, `.gitignore` protege rutas privadas, y `load_config()` tiene comportamiento explícito y documentado. Sin regresiones.

## 8. Espera de aprobación

No continuaré con la Fase 2 hasta que el usuario indique explícitamente que puede avanzar.
