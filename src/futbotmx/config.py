from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any

import yaml

try:
    from dotenv import load_dotenv as _load_dotenv
    _HAS_DOTENV = True
except ImportError:
    _HAS_DOTENV = False

_ENV_VAR_RE = re.compile(r"\$\{([^}]+)\}")


def _expand_env_vars(value: Any) -> Any:
    if isinstance(value, str):
        def _replace(match: re.Match) -> str:
            var = match.group(1)
            result = os.environ.get(var, match.group(0))
            return result
        return _ENV_VAR_RE.sub(_replace, value)
    if isinstance(value, dict):
        return {k: _expand_env_vars(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_expand_env_vars(item) for item in value]
    return value


def _find_unexpanded(value: Any, path: str = "") -> list[str]:
    """Return list of 'path: ${VAR}' strings for any unresolved env vars."""
    if isinstance(value, str):
        found = _ENV_VAR_RE.findall(value)
        return [f"{path}: ${{{v}}}" for v in found]
    if isinstance(value, dict):
        result = []
        for k, v in value.items():
            result.extend(_find_unexpanded(v, f"{path}.{k}" if path else k))
        return result
    if isinstance(value, list):
        result = []
        for i, item in enumerate(value):
            result.extend(_find_unexpanded(item, f"{path}[{i}]"))
        return result
    return []


def load_config(path: str | Path = "configs/default.yaml") -> dict[str, Any]:
    config_path = Path(path)

    if _HAS_DOTENV:
        env_file = Path(".env")
        if env_file.exists():
            _load_dotenv(env_file, override=False)
    else:
        env_file = Path(".env")
        if env_file.exists():
            # Manual .env parsing for when python-dotenv is not installed
            with env_file.open("r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        key, _, val = line.partition("=")
                        key = key.strip()
                        val = val.strip().strip('"').strip("'")
                        if key and key not in os.environ:
                            os.environ[key] = val

    with config_path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    if not isinstance(data, dict):
        raise ValueError(f"Config must be a mapping: {config_path}")

    data = _expand_env_vars(data)

    missing = _find_unexpanded(data)
    if missing:
        lines = "\n  ".join(missing)
        raise EnvironmentError(
            f"Config loaded from '{config_path}' has {len(missing)} unresolved "
            f"environment variable(s):\n  {lines}\n\n"
            "Define these variables by:\n"
            "  1. Copying configs/local_paths.example.yaml → .env and filling in the paths, OR\n"
            "  2. Exporting them in your shell:  export FUTBOTMX_VIDEO_595=/path/to/video.mov\n"
            "See configs/local_paths.example.yaml for the full list of required variables."
        )

    return data


def write_config_snapshot(config: dict[str, Any], path: str | Path) -> None:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as handle:
        yaml.safe_dump(config, handle, sort_keys=False, allow_unicode=False)
