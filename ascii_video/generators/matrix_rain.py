"""Matrix-style digital rain. Column layout is deterministic (seeded) and
cached, so every frame is a closed-form function of frame_idx alone."""
from __future__ import annotations

import random
from functools import lru_cache

import numpy as np

from ascii_video.core.grid import FrameGrid

from .base import GeneratorSpec, ParamSpec, register

CHARS = "0123456789AZXCVBNM<>*+:!?"


@lru_cache(maxsize=16)
def _build_columns(cols: int, rows: int, seed: int, loop_frames: int) -> tuple:
    """cycle_h is chosen to evenly divide loop_frames*speed for every column,
    so frame[0] == frame[loop_frames] exactly (closed-loop, no seam jump)."""
    rng = random.Random(seed)
    columns = []
    for _ in range(cols):
        speed = rng.choice([1, 1, 2, 2, 3])
        length = rng.randint(4, max(5, rows // 2))
        total_dist = loop_frames * speed
        target_h = rows + length + rng.randint(4, 12)
        valid_h = [h for h in range(max(1, target_h - 4), target_h + 8) if total_dist % h == 0]
        if not valid_h:
            valid_h = [h for h in range(16, 50) if total_dist % h == 0]
        cycle_h = rng.choice(valid_h) if valid_h else total_dist
        start_offset = rng.randint(0, cycle_h - 1)
        col_chars = tuple(rng.choice(CHARS) for _ in range(cycle_h))
        columns.append({
            "speed": speed, "length": length, "cycle_h": cycle_h,
            "start_offset": start_offset, "chars": col_chars,
        })
    return tuple(columns)


def generate(t: float, frame_idx: int, cols: int, rows: int, params: dict) -> FrameGrid:
    seed = int(params.get("seed", 42))
    color = params.get("color", False)
    loop_frames = int(params.get("loop_frames", 360))

    columns = _build_columns(cols, rows, seed, loop_frames)
    chars = np.full((rows, cols), " ", dtype="<U1")
    colors = np.zeros((rows, cols, 3), dtype=np.uint8) if color else None

    for x, col in enumerate(columns):
        head_pos = (col["start_offset"] + frame_idx * col["speed"]) % col["cycle_h"]
        head_y = head_pos - 5
        for j in range(col["length"]):
            cy = head_y - j
            if 0 <= cy < rows:
                char_idx = (head_pos + j) % col["cycle_h"]
                ch = col["chars"][char_idx]
                chars[cy, x] = ch.upper() if j == 0 else ch
                if color:
                    colors[cy, x] = (200, 255, 200) if j == 0 else (0, max(60, 255 - j * 15), 0)

    return FrameGrid(cols=cols, rows=rows, chars=chars, colors=colors)


SPEC = GeneratorSpec(
    key="matrix_rain",
    display_name="Matrix Digital Rain",
    fn=generate,
    params=[
        ParamSpec("seed", "Seed", "int", 42, 0, 9999, 1),
        ParamSpec("color", "Color", "bool", False),
    ],
    loop_frames=360,
    default_cols=64,
    default_rows=28,
)
register(SPEC)
