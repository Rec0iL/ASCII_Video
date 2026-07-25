"""Classic bouncing logo screensaver.

A logo reflecting off box walls at unit speed per axis is a triangle wave
on each axis with period 2*range - a closed form of frame_idx, no
accumulated simulation needed. loop_frames_for() returns lcm(2*range_x,
2*range_y), the exact frame count after which position AND direction repeat.
"""
from __future__ import annotations

import math

import numpy as np

from ascii_video.core.grid import FrameGrid

from .base import GeneratorSpec, ParamSpec, hsv_to_rgb_u8, register

LOGO = ["ASCII", "VIDEO"]


def _logo_dims() -> tuple[int, int]:
    return max(len(line) for line in LOGO), len(LOGO)


def _triangle(n: int, rng: int) -> int:
    if rng <= 0:
        return 0
    period = 2 * rng
    m = n % period
    return rng - abs(m - rng)


def loop_frames_for(cols: int, rows: int) -> int:
    logo_w, logo_h = _logo_dims()
    range_x = max(1, cols - logo_w)
    range_y = max(1, rows - logo_h)
    return (2 * range_x * 2 * range_y) // math.gcd(2 * range_x, 2 * range_y)


def generate(t: float, frame_idx: int, cols: int, rows: int, params: dict) -> FrameGrid:
    speed = params.get("speed", 1.0)
    color = params.get("color", False)

    logo_w, logo_h = _logo_dims()
    range_x = max(1, cols - logo_w)
    range_y = max(1, rows - logo_h)
    n = int(frame_idx * speed)

    x = _triangle(n, range_x)
    y = _triangle(n, range_y)

    chars = np.full((rows, cols), " ", dtype="<U1")
    for ly, line in enumerate(LOGO):
        for lx, ch in enumerate(line):
            if ch == " ":
                continue
            px, py = x + lx, y + ly
            if 0 <= px < cols and 0 <= py < rows:
                chars[py, px] = ch

    colors = None
    if color:
        colors = np.zeros((rows, cols, 3), dtype=np.uint8)
        period = loop_frames_for(cols, rows)
        hue = (n / max(1, period)) % 1.0
        rgb = hsv_to_rgb_u8(np.array([hue]), np.array([1.0]), np.array([1.0]))[0]
        colors[chars != " "] = rgb

    return FrameGrid(cols=cols, rows=rows, chars=chars, colors=colors)


SPEC = GeneratorSpec(
    key="dvd_bounce",
    display_name="DVD Bouncing Logo",
    fn=generate,
    params=[
        ParamSpec("speed", "Speed", "float", 1.0, 0.1, 4.0, 0.1),
        ParamSpec("color", "Color", "bool", False),
    ],
    loop_frames=200,  # placeholder; call loop_frames_for(cols, rows) for an exact seam
    default_cols=59,
    default_rows=18,
)
register(SPEC)
