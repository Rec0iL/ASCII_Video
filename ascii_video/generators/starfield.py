"""3D starfield flying outward from the center (classic "warp speed" effect).
Each star's radius is a closed-form sawtooth of frame_idx modulo the loop,
so any frame is independently computable and the loop closes exactly."""
from __future__ import annotations

import math
import random
from functools import lru_cache

import numpy as np

from ascii_video.core.grid import FrameGrid

from .base import GeneratorSpec, ParamSpec, hsv_to_rgb_u8, register

DEPTH_CHARS = " .:+*#@"


@lru_cache(maxsize=32)
def _build_stars(seed: int, count: int) -> tuple:
    rng = random.Random(seed)
    return tuple((rng.uniform(0, 2 * math.pi), rng.uniform(0.0, 1.0)) for _ in range(count))


def generate(t: float, frame_idx: int, cols: int, rows: int, params: dict) -> FrameGrid:
    seed = int(params.get("seed", 3))
    speed = params.get("speed", 1.0)
    count = int(params.get("count", 90))
    color = params.get("color", False)
    hue_deg = params.get("hue", 200.0)
    loop_frames = params.get("loop_frames", 100)

    char_aspect = 2.0  # monospace cells are ~2:1 h:w
    cx, cy = cols / 2.0, rows / 2.0
    max_radius = max(cx, cy * char_aspect) * 1.3

    stars = _build_stars(seed, count)
    chars = np.full((rows, cols), " ", dtype="<U1")
    colors = np.zeros((rows, cols, 3), dtype=np.uint8) if color else None
    base_rgb = tuple(int(v) for v in hsv_to_rgb_u8(np.array((hue_deg % 360) / 360.0), np.array(0.35), np.array(1.0)))

    idx = (frame_idx * speed) % loop_frames
    travel = (idx / loop_frames) * max_radius

    for angle, r0 in stars:
        cos_a, sin_a = math.cos(angle), math.sin(angle)
        r = (r0 * max_radius + travel) % max_radius
        if r < 1.0:
            continue
        depth = r / max_radius
        ci = min(len(DEPTH_CHARS) - 1, int(depth * (len(DEPTH_CHARS) - 1)))

        # A short two-step trail behind the star reads as motion at speed.
        for step, fade in ((0, 1.0), (1, 0.5)):
            rr = r - step
            if rr < 1.0:
                continue
            x = int(round(cx + cos_a * rr))
            y = int(round(cy + sin_a * rr / char_aspect))
            if 0 <= x < cols and 0 <= y < rows:
                chars[y, x] = DEPTH_CHARS[ci] if step == 0 else DEPTH_CHARS[max(0, ci - 1)]
                if color:
                    colors[y, x] = tuple(int(c * depth * fade + 30 * fade) for c in base_rgb)
                elif chars[y, x] == " ":
                    chars[y, x] = DEPTH_CHARS[ci]

    return FrameGrid(cols=cols, rows=rows, chars=chars, colors=colors)


SPEC = GeneratorSpec(
    key="starfield",
    display_name="Starfield",
    fn=generate,
    params=[
        ParamSpec("seed", "Seed", "int", 3, 0, 9999, 1),
        ParamSpec("speed", "Speed", "float", 1.0, 0.1, 4.0, 0.1),
        ParamSpec("count", "Star count", "int", 90, 20, 250, 10),
        ParamSpec("hue", "Hue", "float", 200.0, 0.0, 360.0, 5.0),
        ParamSpec("color", "Color", "bool", False),
    ],
    loop_frames=100,
    default_cols=70,
    default_rows=30,
)
register(SPEC)
