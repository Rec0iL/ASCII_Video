"""Brightness ramp charset mapping."""
from __future__ import annotations

import numpy as np

DEFAULT_RAMP = " .:-=+*#%@"

RAMP_PRESETS: dict[str, str] = {
    "classic": " .:-=+*#%@",
    "blocks": " ░▒▓█",
    "binary": " #",
    "minimal": " .:coP0#@",
    "reverse_classic": "@%#*+=-:. ",
}


def luminance(rgb: np.ndarray) -> np.ndarray:
    """rgb: (..., 3) array in BGR (OpenCV) order, float or uint8. Returns 0..1 float."""
    b = rgb[..., 0].astype(np.float32)
    g = rgb[..., 1].astype(np.float32)
    r = rgb[..., 2].astype(np.float32)
    lum = 0.299 * r + 0.587 * g + 0.114 * b
    return np.clip(lum / 255.0, 0.0, 1.0)


def brightness_to_chars(brightness: np.ndarray, ramp: str = DEFAULT_RAMP, invert: bool = False) -> np.ndarray:
    """brightness: 0..1 float array. Returns an array of characters, same shape."""
    if invert:
        brightness = 1.0 - brightness
    ramp_arr = np.array(list(ramp), dtype="<U1")
    n = len(ramp_arr)
    idx = np.clip((brightness * n).astype(np.int64), 0, n - 1)
    return ramp_arr[idx]
