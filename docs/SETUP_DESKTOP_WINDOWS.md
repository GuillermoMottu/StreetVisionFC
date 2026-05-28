# Configuracion del escritorio Windows

Este documento inicia la configuracion del equipo de escritorio descrito en la documentacion de FutBotMX.

## Rol de este equipo

Este escritorio debe usarse para:

- Desarrollo de codigo ligero.
- Documentacion.
- Coordinacion con Codex y Claude Desktop.
- Analisis de CSV/JSON.
- Ajuste de reglas de eventos.
- README y entregables.
- Visualizaciones ligeras.

Este escritorio no debe usarse como maquina principal para inferencia pesada con SAM 3, generacion masiva de mascaras o render pesado de videos.

## Estado detectado

- Repositorio base localizado en `%USERPROFILE%\Documents\GitHub\StreetVisionFC`.
- La documentacion inicial existe en `FutBotMX_documentacion_markdown/`.
- La estructura base del proyecto ya fue creada.
- Python 3.12.10 fue instalado desde Python.org.
- El entorno virtual `.venv` fue creado.
- Las dependencias de `requirements-dev.txt` fueron instaladas.
- La validacion de imports de escritorio fue exitosa.

## Estructura base creada

```text
configs/
data/
data/sample/
docs/
experiments/
outputs/
scripts/
src/futbotmx/
tests/
```

## Archivos de configuracion creados

```text
.gitignore
README.md
requirements-dev.txt
requirements-gpu.txt
configs/default.yaml
src/futbotmx/__init__.py
```

## Instalacion realizada

Python 3.12.10 quedo disponible en:

```text
%LOCALAPPDATA%\Programs\Python\Python312\python.exe
```

El entorno virtual del proyecto quedo disponible en:

```text
.venv/
```

## Uso diario en este equipo

Activar entorno:

```powershell
.\.venv\Scripts\Activate.ps1
```

Verificar Python:

```powershell
python --version
```

Validar imports de escritorio:

```powershell
python -c "import cv2, numpy, pandas, yaml, matplotlib; print('desktop environment ok')"
```

## Flujo antes de cambiar a laptop MSI

```powershell
git status
git add .
git commit -m "config: initialize desktop development setup"
git push origin main
```

En la laptop MSI:

```bash
git pull origin main
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements-gpu.txt
```

SAM 3 debe instalarse en la laptop siguiendo su documentacion oficial y registrando cualquier error en `FutBotMX_documentacion_markdown/ERRORS_AND_FIXES.md`.
