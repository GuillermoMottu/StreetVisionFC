from __future__ import annotations

from functools import lru_cache
from importlib.resources import files

UI_VERSION = "futbotmx-ui-v1"
_CSS_FILES = ("tokens.css", "layout.css", "components.css")


@lru_cache(maxsize=1)
def shared_css() -> str:
    """Return the shared FutBotMX UI layer for static, self-contained HTML."""
    package = files(__package__)
    chunks = []
    for name in _CSS_FILES:
        chunks.append(package.joinpath(name).read_text(encoding="utf-8").strip())
    return "\n\n".join(chunks) + "\n"


def ui_body_attrs(flow: str, extra_class: str = "") -> str:
    classes = " ".join(part for part in ("fb-page", extra_class.strip()) if part)
    return f'class="{classes}" data-ui-shell="{UI_VERSION}" data-product-flow="{flow}"'
