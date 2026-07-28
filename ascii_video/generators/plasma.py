"""Classic "plasma" effect: a sum of sine waves sampled over the grid,
mapped through a brightness ramp and a color palette. Every time-dependent
term uses an integer multiple of the loop phase, so it closes exactly."""
from __future__ import annotations

import numpy as np

from ascii_video.core.grid import FrameGrid
from ascii_video.core.ramp import RAMP_PRESETS

from .base import GeneratorSpec, ParamSpec, hsv_to_rgb_u8, register

PLASMA_RAMP = RAMP_PRESETS["classic"]

GRADIENT_PALETTES: dict[str, list[tuple[float, tuple[int, int, int]]]] = {
    "fire": [
        (0.0, (10, 0, 40)), (0.33, (160, 0, 60)), (0.66, (255, 120, 0)), (1.0, (255, 240, 180)),
    ],
    "ocean": [
        (0.0, (0, 5, 30)), (0.33, (0, 60, 120)), (0.66, (0, 170, 200)), (1.0, (200, 255, 250)),
    ],
    "mono": [
        (0.0, (0, 0, 0)), (1.0, (0, 255, 90)),
    ],
}


def _gradient_to_rgb(value: np.ndarray, palette: str) -> np.ndarray:
    stops = GRADIENT_PALETTES[palette]
    xs = [s[0] for s in stops]
    r = np.interp(value, xs, [s[1][0] for s in stops])
    g = np.interp(value, xs, [s[1][1] for s in stops])
    b = np.interp(value, xs, [s[1][2] for s in stops])
    return np.stack([r, g, b], axis=-1).astype(np.uint8)


def generate(t: float, frame_idx: int, cols: int, rows: int, params: dict) -> FrameGrid:
    loop_frames = params.get("loop_frames", 120)
    speed = params.get("speed", 1.0)
    scale = params.get("scale", 1.0)
    palette = params.get("palette", "rainbow")
    color = params.get("color", True)

    idx = (frame_idx * speed) % loop_frames
    phase = (idx / loop_frames) * 2 * np.pi

    x = np.arange(cols)
    y = np.arange(rows)
    X, Y = np.meshgrid(x, y)  # shape (rows, cols)
    cx, cy = cols / 2, rows / 2

    f1, f2, f3, f4 = 3.0 * scale, 3.0 * scale, 4.0 * scale, 5.0 * scale
    dist = np.hypot(X - cx, Y - cy) / max(cols, rows)

    value = (
        np.sin(2 * np.pi * f1 * X / cols + phase)
        + np.sin(2 * np.pi * f2 * Y / rows + phase)
        + np.sin(2 * np.pi * f3 * (X / cols + Y / rows) + 2 * phase)
        + np.sin(2 * np.pi * f4 * dist - phase)
    )
    value = (value + 4.0) / 8.0  # 0..1
    value = np.clip(value, 0.0, 1.0)

    ramp_arr = np.array(list(PLASMA_RAMP), dtype="<U1")
    idx_arr = np.clip((value * (len(ramp_arr) - 1)).astype(np.int64), 0, len(ramp_arr) - 1)
    chars = ramp_arr[idx_arr]

    colors = None
    if color:
        if palette == "rainbow":
            hue = (value + idx / loop_frames) % 1.0
            colors = hsv_to_rgb_u8(hue, np.full_like(hue, 0.85), np.full_like(hue, 1.0))
        else:
            colors = _gradient_to_rgb(value, palette)

    return FrameGrid(cols=cols, rows=rows, chars=chars, colors=colors)


SPEC = GeneratorSpec(
    key="plasma",
    display_name="Plasma",
    fn=generate,
    params=[
        ParamSpec("speed", "Speed", "float", 1.0, 0.1, 4.0, 0.1),
        ParamSpec("scale", "Scale", "float", 1.0, 0.3, 3.0, 0.1),
        ParamSpec("palette", "Palette", "choice", "rainbow", choices=["rainbow", "fire", "ocean", "mono"]),
        ParamSpec("color", "Color", "bool", True),
    ],
    loop_frames=120,
    default_cols=70,
    default_rows=28,
)
register(SPEC)
