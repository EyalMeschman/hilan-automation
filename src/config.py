import json
from pathlib import Path

CONFIG_DIR = Path.home() / ".hilan-automation"
CONFIG_FILE = CONFIG_DIR / "config.json"


def load_config() -> dict:
    if not CONFIG_FILE.exists():
        return {}
    return json.loads(CONFIG_FILE.read_text(encoding="utf-8"))


def save_config(username: str, password: str):
    config = load_config()
    config["username"] = username
    config["password"] = password
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_FILE.write_text(
        json.dumps(config, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def update_config(confirm_before_save: bool):
    config = load_config()
    config["confirm_before_save"] = confirm_before_save
    CONFIG_FILE.write_text(
        json.dumps(config, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def clear_config():
    config = load_config()
    config.pop("username", None)
    config.pop("password", None)
    if config:
        CONFIG_FILE.write_text(
            json.dumps(config, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    elif CONFIG_FILE.exists():
        CONFIG_FILE.unlink()
