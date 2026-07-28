"""Falling rain with expanding ripple splashes where each drop lands.
Each drop's fall + splash cycle is a closed-form function of frame_idx
modulo a per-drop period chosen to divide loop_frames*speed exactly -- the
same technique the matrix-rain columns use -- so any frame is independently
computable and the loop closes exactly."""
from __future__ import annotations

import random
from functools import lru_cache

import numpy as np

from ascii_video.core.grid import FrameGrid

from .base import GeneratorSpec, ParamSpec, hsv_to_rgb_u8, register

DROP_CHARS = "'.|"  # trailing -> leading
RIPPLE_CHARS = " .:-=~"
SPLASH_FRAMES = 8


@lru_cache(maxsize=32)
def _build_drops(cols: int, rows: int, seed: int, loop_frames: int, density: float) -> tuple:
    rng = random.Random(seed)
    num_drops = max(1, int(cols * density))
    drops = []
    for _ in range(num_drops):
        speed = rng.choice([1, 1, 2])
        x = rng.randint(0, cols - 1)
        period_base = rows + SPLASH_FRAMES + rng.randint(0, 6)
        total_dist = loop_frames * speed
        valid = [p for p in range(max(1, period_base - 5), period_base + 10) if total_dist % p == 0]
        if not valid:
            valid = [p for p in range(rows + SPLASH_FRAMES, rows + SPLASH_FRAMES + 30) if total_dist % p == 0]
        period = rng.choice(valid) if valid else total_dist
        start_offset = rng.randint(0, period - 1)
        drops.append({"x": x, "speed": speed, "period": period, "start_offset": start_offset})
    return tuple(drops)


def generate(t: float, frame_idx: int, cols: int, rows: int, params: dict) -> FrameGrid:
    seed = int(params.get("seed", 11))
    speed = params.get("speed", 1.0)
    density = params.get("density", 0.5)
    splash_size = params.get("splash_size", 1.0)
    hue_deg = params.get("hue", 200.0)
    color = params.get("color", True)
    loop_frames = int(params.get("loop_frames", 150))

    max_ripple = max(3.0, cols * 0.12 * splash_size)
    base_rgb = tuple(int(v) for v in hsv_to_rgb_u8(np.array(hue_deg / 360.0), np.array(0.55), np.array(1.0)))

    drops = _build_drops(cols, rows, seed, loop_frames, density)
    chars = np.full((rows, cols), " ", dtype="<U1")
    colors = np.zeros((rows, cols, 3), dtype=np.uint8) if color else None

    for d in drops:
        # d["period"] was chosen (in _build_drops) to divide loop_frames *
        # d["speed"] exactly -- both the global speed multiplier and the
        # drop's own randomized fall-rate must be applied here, or a period
        # built for one distance gets driven by a different one and the
        # loop seam no longer lines up.
        pos = (d["start_offset"] + frame_idx * speed * d["speed"]) % d["period"]
        if pos < rows:
            y = int(pos)
            for k, ch in enumerate(reversed(DROP_CHARS)):
                yy = y - k
                if 0 <= yy < rows:
                    chars[yy, d["x"]] = ch
                    if color:
                        fade = 1.0 - k / len(DROP_CHARS)
                        colors[yy, d["x"]] = tuple(int(c * fade) for c in base_rgb)
        else:
            splash_age = pos - rows
            if splash_age < SPLASH_FRAMES and rows >= 1:
                progress = splash_age / SPLASH_FRAMES
                radius = progress * max_ripple
                fade = 1.0 - progress
                for dx in range(-int(radius) - 1, int(radius) + 2):
                    xx = d["x"] + dx
                    if not (0 <= xx < cols):
                        continue
                    dist_ratio = abs(abs(dx) - radius)
                    if dist_ratio < 1.0:
                        intensity = fade * (1.0 - dist_ratio)
                        ci = min(len(RIPPLE_CHARS) - 1, max(0, int(intensity * (len(RIPPLE_CHARS) - 1))))
                        if RIPPLE_CHARS[ci] != " ":
                            chars[rows - 1, xx] = RIPPLE_CHARS[ci]
                            if color:
                                colors[rows - 1, xx] = tuple(int(c * intensity) for c in base_rgb)

    return FrameGrid(cols=cols, rows=rows, chars=chars, colors=colors)


SPEC = GeneratorSpec(
    key="rain_drops",
    display_name="Rain Drops",
    fn=generate,
    params=[
        ParamSpec("seed", "Seed", "int", 11, 0, 9999, 1),
        ParamSpec("speed", "Speed", "float", 1.0, 0.1, 3.0, 0.1),
        ParamSpec("density", "Density", "float", 0.5, 0.1, 1.0, 0.05),
        ParamSpec("splash_size", "Splash size", "float", 1.0, 0.3, 2.5, 0.1),
        ParamSpec("hue", "Hue", "float", 200.0, 0.0, 360.0, 5.0),
        ParamSpec("color", "Color", "bool", True),
    ],
    loop_frames=150,
    default_cols=64,
    default_rows=26,
)
register(SPEC)
