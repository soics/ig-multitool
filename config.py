"""Configuration loader for Instagram Multi-Tool.

Reads config.json (gitignored, real secrets) falling back to
config.example.json (committed, placeholder values). First run should
copy config.example.json to config.json and fill in real values.
"""

import json
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
CONFIG_PATH = BASE_DIR / "config.json"
EXAMPLE_PATH = BASE_DIR / "config.example.json"

DEFAULTS = {
    "username": "",
    "password": "",
    "session_path": str(BASE_DIR / "session.json"),
    "pacing": {
        "action_delay_min": 3,
        "action_delay_max": 15,
        "batch_pause_every": 10,
        "batch_pause_seconds": 60,
    },
    "ai": {
        "enabled": False,
        "base_url": "http://localhost:20128/v1",
        "api_key": "",
        "model": "ollama/gpt-oss:120b",
        "whitelist_only": False,
        "poll_interval_seconds": 20,
        "system_prompt": (
            "You are a helpful Instagram assistant. Answer concisely. "
            "You may answer questions about the account owner's posts, "
            "captions, and DMs when asked."
        ),
    },
    "whitelist": [],
}


def _deep_merge(base: dict, override: dict) -> dict:
    out = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key] = _deep_merge(out[key], value)
        else:
            out[key] = value
    return out


def load_config() -> dict:
    config = json.loads(json.dumps(DEFAULTS))
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH, encoding="utf-8") as fh:
            config = _deep_merge(config, json.load(fh))
    elif EXAMPLE_PATH.exists():
        with open(EXAMPLE_PATH, encoding="utf-8") as fh:
            config = _deep_merge(config, json.load(fh))
    if not config["session_path"] or not os.path.isabs(config["session_path"]):
        config["session_path"] = str(BASE_DIR / (config["session_path"] or "session.json"))
    return config


def save_config(config: dict) -> None:
    with open(CONFIG_PATH, "w", encoding="utf-8") as fh:
        json.dump(config, fh, indent=2)
        fh.write("\n")


def first_run() -> bool:
    return not CONFIG_PATH.exists() and EXAMPLE_PATH.exists()