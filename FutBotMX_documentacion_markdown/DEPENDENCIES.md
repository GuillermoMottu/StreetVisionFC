# FutBotMX — Dependencies

## 1. Propósito

Este documento define las dependencias técnicas de FutBotMX considerando dos entornos de trabajo:

1. **Escritorio Windows:** desarrollo, documentación, lógica, revisión y coordinación con agentes IA.
2. **Laptop MSI Ubuntu:** inferencia pesada, SAM 3, segmentación, tracking y generación de resultados.

---

# 2. Stack técnico general

| Componente | Uso |
|---|---|
| Python 3.10+ | Lenguaje principal |
| Git + GitHub | Sincronización entre equipos |
| OpenCV | Procesamiento de video |
| NumPy | Cálculo numérico |
| pandas | CSV, métricas y análisis |
| matplotlib | Gráficos ligeros |
| PyYAML | Configuración |
| PyTorch | Deep learning |
| SAM 3 | Segmentación principal |
| supervision / ByteTrack | Tracking |
| ffmpeg | Manejo de video |
| Jupyter | Exploración opcional |

---

# 3. Entorno de desarrollo - Escritorio

## 3.1 Hardware

- Intel Core i7-12700.
- 16 GB RAM.
- NVIDIA GeForce GT 1030 2 GB.
- Windows.

## 3.2 Rol del escritorio

El escritorio será la estación principal para:

- Desarrollo de código.
- Edición de documentación.
- Coordinación con Codex.
- Coordinación con Claude Desktop.
- Revisión de resultados ligeros.
- Ajuste de eventos.
- Análisis de JSON y CSV.
- Preparación de README.
- Preparación de dashboard ligero.
- Planeación de entregables.

## 3.3 Restricción importante

El escritorio **no debe utilizarse como máquina principal para inferencia SAM 3**, porque la GT 1030 de 2 GB no es adecuada para cargas pesadas de segmentación.

Uso permitido en escritorio:

- Validar imports.
- Ejecutar pruebas unitarias.
- Analizar CSV/JSON.
- Generar gráficos ligeros.
- Revisar capturas.
- Preparar documentación.
- Ejecutar scripts pequeños sin inferencia pesada.

## 3.4 Dependencias recomendadas en escritorio

| Dependencia | Uso |
|---|---|
| Git | Sincronización con GitHub |
| VS Code | Edición de código |
| Python 3.10+ | Desarrollo |
| Codex | Apoyo en programación |
| Claude Desktop | Revisión de documentación y razonamiento |
| pandas | Análisis de CSV |
| NumPy | Cálculo ligero |
| matplotlib | Visualizaciones simples |
| PyYAML | Configuración |
| OpenCV | Pruebas ligeras de video |
| Jupyter | Exploración opcional |
| markdownlint | Revisión de documentación opcional |

## 3.5 Instalación sugerida en escritorio

```bash
git clone <repo-url>
cd FutBotMX

python -m venv .venv
.venv\Scripts\activate

python -m pip install --upgrade pip
pip install -r requirements-dev.txt
```

## 3.6 `requirements-dev.txt` sugerido

```text
numpy
pandas
matplotlib
pyyaml
opencv-python
jupyter
tqdm
```

---

# 4. Entorno de inferencia - Laptop MSI

## 4.1 Hardware

- MSI Thin GF63 12VE.
- Intel Core i5-12450H.
- 16 GB RAM.
- NVIDIA GeForce RTX 4050 Laptop GPU.
- Linux/Ubuntu.

## 4.2 Rol de la laptop

La laptop MSI será la estación recomendada para:

- Ejecutar SAM 3.
- Ejecutar segmentación.
- Ejecutar tracking.
- Generar máscaras.
- Generar overlays.
- Generar videos anotados.
- Ejecutar benchmarks.
- Exportar resultados pesados localmente.
- Generar resultados ligeros para subir a GitHub.

## 4.3 Dependencias recomendadas en laptop

| Dependencia | Uso |
|---|---|
| Ubuntu/Linux | Entorno recomendado para GPU |
| NVIDIA Driver | Uso correcto de RTX 4050 |
| CUDA compatible | Aceleración GPU |
| PyTorch CUDA | Inferencia con GPU |
| SAM 3 | Segmentación base |
| OpenCV | Video y anotaciones |
| NumPy | Cálculo numérico |
| pandas | Métricas |
| matplotlib | Visualizaciones |
| supervision | Tracking/anotaciones |
| ByteTrack | Tracking multiobjeto |
| ffmpeg | Exportación de video |
| tqdm | Progreso de procesamiento |
| Hugging Face authentication | Si SAM 3/modelos lo requieren |

## 4.4 Instalación base en laptop

```bash
git clone <repo-url>
cd FutBotMX

python3 -m venv .venv
source .venv/bin/activate

python -m pip install --upgrade pip
pip install -r requirements-gpu.txt
```

## 4.5 `requirements-gpu.txt` sugerido

```text
numpy
pandas
matplotlib
pyyaml
opencv-python
tqdm
torch
torchvision
supervision
```

SAM 3 debe agregarse siguiendo su instalación oficial.

**Decisión inicial sujeta a validación:** el comando exacto de instalación de SAM 3 queda pendiente hasta confirmar versión, repositorio, pesos y compatibilidad.

---

# 5. Verificación de GPU en laptop

Ejecutar:

```bash
nvidia-smi
```

Verificar PyTorch CUDA:

```bash
python -c "import torch; print(torch.cuda.is_available()); print(torch.cuda.get_device_name(0))"
```

Resultado esperado:

```text
True
NVIDIA GeForce RTX 4050 Laptop GPU
```

Si no aparece `True`, no ejecutar pruebas pesadas hasta corregir drivers, CUDA o instalación de PyTorch.

---

# 6. SAM 3

SAM 3 es la tecnología base del proyecto.

## Uso esperado

- Segmentación del campo.
- Segmentación de robots.
- Segmentación del balón.
- Generación de máscaras.
- Preparación de detecciones para tracking.

## Regla de integración

SAM 3 debe encapsularse dentro de un módulo propio:

```text
src/futbotmx/segmentation/sam3_segmenter.py
```

El resto del pipeline no debe depender directamente de detalles internos de SAM 3.

## Salida normalizada esperada

```json
{
  "frame": 120,
  "detections": [
    {
      "class_name": "ball",
      "bbox": [100, 120, 116, 136],
      "centroid": [108, 128],
      "confidence": 0.72,
      "mask_path": "local_optional_path"
    }
  ]
}
```

---

# 7. Archivos que no deben subirse a GitHub

No subir:

- Checkpoints de modelos.
- Pesos de SAM 3.
- Videos completos pesados.
- Frames masivos.
- Máscaras masivas.
- Archivos `.npy` grandes.
- Outputs de video pesados.
- Datasets completos.
- Cachés.
- Entornos virtuales.
- Carpetas temporales.
- Archivos generados automáticamente de gran tamaño.

Ejemplos:

```text
models/
checkpoints/
data/raw/full_match.mp4
data/processed/frames/
outputs/videos/full_annotated_match.mp4
outputs/masks/
*.npy
.venv/
__pycache__/
```

---

# 8. Archivos que sí pueden subirse a GitHub

Sí subir:

- Código fuente.
- Scripts.
- Configuración YAML.
- Documentación.
- Logs resumidos.
- Métricas CSV ligeras.
- Eventos JSON.
- Capturas pequeñas.
- Thumbnails.
- Summaries markdown.
- Archivos de prueba pequeños si son necesarios.

---

# 9. Variables de entorno sugeridas

```bash
FUTBOTMX_CONFIG=configs/default.yaml
FUTBOTMX_DATA_DIR=data
FUTBOTMX_OUTPUT_DIR=outputs
SAM3_CHECKPOINT_PATH=models/sam3/checkpoint.pt
```

La variable `SAM3_CHECKPOINT_PATH` no debe apuntar a un archivo versionado en GitHub si el checkpoint es pesado o tiene restricciones de licencia.

---

# 10. Riesgos técnicos

| Riesgo | Equipo afectado | Mitigación |
|---|---|---|
| SAM 3 no instala correctamente | Laptop | Documentar error en `ERRORS_AND_FIXES.md` |
| CUDA no disponible | Laptop | Validar con `nvidia-smi` y PyTorch |
| GT 1030 insuficiente | Escritorio | No ejecutar inferencia pesada ahí |
| Archivos pesados saturan GitHub | Ambos | Usar `.gitignore` y subir solo resultados ligeros |
| Tracking inestable | Laptop/Escritorio | Ajustar umbrales y documentar |
| Eventos falsos positivos | Escritorio | Validar con CSV/JSON y capturas |
