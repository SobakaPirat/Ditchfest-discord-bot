import os
from pathlib import Path

from dotenv import get_key, set_key


def _find_root(marker: str = "pyproject.toml") -> Path:
    """Корень проекта — вверх от этого файла до pyproject.toml."""
    p = Path(__file__).resolve()
    for parent in [p, *p.parents]:
        if (parent / marker).exists():
            return parent
    return Path("/app")  # фолбэк для контейнера


# .env лежит в config/


def get_env_key(key: str) -> str | None:
    DOTENV_PATH = Path(os.environ.get("DOTENV_PATH", _find_root() / "config" / ".env"))
    if DOTENV_PATH.exists():
        return get_key(str(DOTENV_PATH), key)


def set_env_key(key: str, value: str) -> None:
    DOTENV_PATH = Path(os.environ.get("DOTENV_PATH", _find_root() / "config" / ".env"))
    if DOTENV_PATH.exists():
        set_key(str(DOTENV_PATH), key, value)
