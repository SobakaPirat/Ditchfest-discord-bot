from pathlib import Path
from unittest.mock import patch

import pytest

from src.utils.config import _find_root, get_env_key, set_env_key


@pytest.fixture
def dotenv_path(tmp_path, monkeypatch):
    """Временный .env, на который указывает переменная DOTENV_PATH."""
    env_file = tmp_path / ".env"
    env_file.write_text('DB_HOST = "127.0.0.1"\nONLY_TEMP = "yes"\nEMPTY_VALUE = ""\n')
    monkeypatch.setenv("DOTENV_PATH", str(env_file))
    return env_file


@pytest.fixture
def no_dotenv_env(monkeypatch):
    """DOTENV_PATH не задан — используется config/.env относительно корня проекта."""
    monkeypatch.delenv("DOTENV_PATH", raising=False)


# ------------------------------------------------------------------
# _find_root

def test_find_root_returns_project_root(no_dotenv_env):
    root = _find_root()
    assert (root / "pyproject.toml").is_file()
    assert (root / "tests").is_dir()


def test_find_root_uses_custom_marker(no_dotenv_env):
    root = _find_root(marker="pyproject.toml")
    assert root == Path(__file__).resolve().parents[1]


def test_find_root_falls_back_to_app(no_dotenv_env):
    assert _find_root(marker="no_such_marker_xyz.txt") == Path("/app")


# ------------------------------------------------------------------
# get_env_key

def test_get_env_key_returns_value_without_quotes(dotenv_path):
    assert get_env_key("DB_HOST") == "127.0.0.1"


def test_get_env_key_returns_empty_string_for_empty_value(dotenv_path):
    assert get_env_key("EMPTY_VALUE") == ""


def test_get_env_key_returns_none_for_missing_key(dotenv_path):
    assert get_env_key("NO_SUCH_KEY") is None


def test_get_env_key_returns_none_when_file_missing(tmp_path, monkeypatch):
    monkeypatch.setenv("DOTENV_PATH", str(tmp_path / "missing.env"))
    assert get_env_key("DB_HOST") is None


def test_get_env_key_uses_dotenv_path_env_var(dotenv_path):
    assert get_env_key("ONLY_TEMP") == "yes"


def test_get_env_key_defaults_to_config_env(no_dotenv_env, tmp_path):
    (tmp_path / "config").mkdir()
    (tmp_path / "config" / ".env").write_text('UPDATER_TIME = "04:00"\n')
    with patch("src.utils.config._find_root", return_value=tmp_path):
        assert get_env_key("UPDATER_TIME") == "04:00"


def test_get_env_key_returns_none_when_default_config_env_missing(no_dotenv_env, tmp_path):
    with patch("src.utils.config._find_root", return_value=tmp_path):
        assert get_env_key("UPDATER_TIME") is None


# ------------------------------------------------------------------
# set_env_key

def test_set_env_key_updates_existing_key(dotenv_path):
    set_env_key("DB_HOST", "mariadb")
    assert get_env_key("DB_HOST") == "mariadb"
    assert "mariadb" in dotenv_path.read_text()


def test_set_env_key_adds_new_key(dotenv_path):
    set_env_key("NEW_KEY", "some value")
    assert get_env_key("NEW_KEY") == "some value"


def test_set_env_key_is_noop_when_file_missing(tmp_path, monkeypatch):
    missing = tmp_path / "missing.env"
    monkeypatch.setenv("DOTENV_PATH", str(missing))
    set_env_key("DB_HOST", "mariadb")
    assert not missing.exists()
