import json
from enum import StrEnum
from pathlib import Path

CONFIG_DIR = Path.home() / ".hilan-automation"
CONFIG_FILE = CONFIG_DIR / "config.json"


class ConfigKey(StrEnum):
    USERNAME = "username"
    PASSWORD = "password"
    CONFIRM_BEFORE_SAVE = "confirm_before_save"
    SHOW_LOGIN_TUTORIAL = "show_login_tutorial"
    SHOW_MAIN_TUTORIAL = "show_main_tutorial"


def load_config() -> dict:
    if not CONFIG_FILE.exists():
        return {}
    return json.loads(CONFIG_FILE.read_text(encoding="utf-8"))


def _write_config(config: dict):
    """Atomic write: write to temp file, then rename."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    tmp = CONFIG_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.rename(CONFIG_FILE)


def update_config(**fields):
    """Merge fields into existing config."""
    config = load_config()
    config.update(fields)
    _write_config(config)


def clear_fields(*keys: str):
    """Remove specific keys from config."""
    config = load_config()
    for key in keys:
        config.pop(key, None)
    if config:
        _write_config(config)
    elif CONFIG_FILE.exists():
        CONFIG_FILE.unlink()
