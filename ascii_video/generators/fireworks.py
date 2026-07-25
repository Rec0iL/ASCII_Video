"""Fireworks bursting in the night sky. Burst layout is seeded/cached; each
frame's spark positions are a closed-form function of age-since-launch
wrapped modulo loop_frames, so the loop seam has no jump."""
from __future__ import annotations

import math
import random
from functools import lru_cache

import numpy as np

from ascii_video.core.grid import FrameGrid

from .base import GeneratorSpec, ParamSpec, register

SPARK_CHARS = [".", "*", "+", "o", "O", "#", "@", "*"]


@lru_cache(maxsize=16)
def _build_bursts(cols: int, rows: int, seed: int, loop_frames: int, num_bursts: int = 6) -> tuple:
    rng = random.Random(seed)
    bursts = []
    spacing = max(1, loop_frames // max(1, num_bursts))
    for b in range(num_bursts):
        cx = rng.randint(max(1, int(cols * 0.15)), max(2, int(cols * 0.85)))
        cy = rng.randint(max(1, int(rows * 0.15)), max(2, int(rows * 0.6)))
        start_frame = b * spacing
        num_sparks = rng.randint(10, 20)
        sparks = tuple((rng.uniform(0, 2 * math.pi), rng.uniform(0.5, 2.5)) for _ in range(num_sparks))
        bursts.append({"cx": cx, "cy": cy, "start": start_frame, "sparks": sparks, "life": 10})
    return tuple(bursts)


@lru_cache(maxsize=16)
def _build_stars(cols: int, rows: int, seed: int, count: int = 15) -> tuple:
    rng = random.Random(seed + 1)
    return tuple((rng.randint(0, max(0, cols - 1)), rng.randint(0, max(1, rows - 3))) for _ in range(count))


def generate(t: float, frame_idx: int, cols: int, rows: int, params: dict) -> FrameGrid:
    seed = int(params.get("seed", 77))
    speed = params.get("speed", 1.0)
    color = params.get("color", False)
    loop_frames = int(params.get("loop_frames", 48))

    idx = int(frame_idx * speed)
    bursts = _build_bursts(cols, rows, seed, loop_frames)
    stars = _build_stars(cols, rows, seed)

    chars = np.full((rows, cols), " ", dtype="<U1")
    colors = np.zeros((rows, cols, 3), dtype=np.uint8) if color else None

    for sx, sy in stars:
        if (idx + sx) % 6 < 4:
            chars[sy, sx] = "."

    if rows > 0:
        chars[rows - 1, :] = "_"

    for burst in bursts:
        rel = (idx - burst["start"]) % loop_frames
        if rel >= burst["life"] and rel <= loop_frames - 6:
            continue
        if rel > loop_frames - 6:
            trail_age = loop_frames - rel
            if trail_age <= 5:
                trail_y = rows - 2 - int((5 - trail_age) * (rows - burst["cy"] - 2) / 5)
                if 0 <= trail_y < rows - 1:
                    chars[trail_y, burst["cx"]] = "|"
                    if trail_y + 1 < rows - 1:
                        chars[trail_y + 1, burst["cx"]] = ":"
            continue

        age = rel
        progress = age / burst["life"]
        for angle, spark_speed in burst["sparks"]:
            dx = math.cos(angle) * spark_speed * age * 0.8
            dy = math.sin(angle) * spark_speed * age * 0.5 + age * 0.15
            sx = int(burst["cx"] + dx)
            sy = int(burst["cy"] + dy)
            if 0 <= sx < cols and 0 <= sy < rows - 1:
                fade = max(0, min(len(SPARK_CHARS) - 1, len(SPARK_CHARS) - 1 - int(progress * len(SPARK_CHARS))))
                chars[sy, sx] = SPARK_CHARS[fade]
                if color:
                    colors[sy, sx] = (255, max(40, 220 - fade * 20), 60)

    return FrameGrid(cols=cols, rows=rows, chars=chars, colors=colors)


SPEC = GeneratorSpec(
    key="fireworks",
    display_name="Fireworks Display",
    fn=generate,
    params=[
        ParamSpec("seed", "Seed", "int", 77, 0, 9999, 1),
        ParamSpec("color", "Color", "bool", False),
    ],
    loop_frames=48,
    default_cols=60,
    default_rows=18,
)
register(SPEC)
