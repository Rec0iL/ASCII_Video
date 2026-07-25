"""Cross-platform app config/preset storage locations."""
from __future__ import annotations

from pathlib import Path

from platformdirs import user_config_dir

APP_NAME = "ascii-video"


def config_dir() -> Path:
    d = Path(user_config_dir(APP_NAME))
    d.mkdir(parents=True, exist_ok=True)
    return d


def presets_dir() -> Path:
    d = config_dir() / "presets"
    d.mkdir(parents=True, exist_ok=True)
    return d
