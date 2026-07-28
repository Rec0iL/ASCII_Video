"""Matrix-style digital rain: half-width katakana glyphs falling in columns,
a bright white leading character fading down through a selectable color.
Column layout is deterministic (seeded) and cached, so every frame is a
closed-form function of frame_idx alone.

On top of the downward scroll, a scattered subset of trail positions also
mutate to a different glyph every few frames while otherwise sitting still --
the flicker real "code rain" glyphs have, independent of the fall speed."""
from __future__ import annotations

import random
from functools import lru_cache

import numpy as np

from ascii_video.core.grid import FrameGrid

from .base import GeneratorSpec, ParamSpec, register

# Half-width katakana (U+FF66-FF9D) plus a few digits -- the same glyph
# range the "Matrix code rain" look is built from -- not copied source, just
# the public Unicode block.
_KATAKANA = "".join(chr(c) for c in range(0xFF66, 0xFF9E))
CHARS = _KATAKANA + "0123456789"

HEAD_COLOR = (235, 255, 235)  # near-white with a faint green tint
HUE_PALETTE: dict[str, tuple[int, int, int]] = {
    "green": (0, 255, 70),
    "cyan": (0, 230, 255),
    "blue": (60, 120, 255),
    "red": (255, 40, 40),
    "purple": (190, 60, 255),
    "amber": (255, 170, 30),
    "white": (230, 230, 230),
}

# Flicker cadence: every FLICKER_PERIOD frames, flickery slots may show a
# different glyph from their small precomputed pool. Chosen so that with the
# default loop_frames=360, (loop_frames // FLICKER_PERIOD) % FLICKER_POOL == 0
# -- i.e. the flicker state is back where it started at the seam too.
FLICKER_PERIOD = 5
FLICKER_POOL = 4


@lru_cache(maxsize=32)
def _build_columns(
    cols: int, rows: int, seed: int, loop_frames: int, density: float, trail_length: float, flicker_chance: float
) -> tuple:
    """cycle_h is chosen to evenly divide loop_frames*speed for every active
    column, so frame[0] == frame[loop_frames] exactly (closed loop, no seam
    jump). density thins out how many columns actually carry a stream."""
    rng = random.Random(seed)
    columns = []
    for _ in range(cols):
        if rng.random() > density:
            columns.append(None)
            continue
        speed = rng.choice([1, 1, 2, 2, 3])
        base_length = rng.randint(4, max(5, rows // 2))
        length = max(2, int(base_length * trail_length))
        total_dist = loop_frames * speed
        target_h = rows + length + rng.randint(4, 12)
        valid_h = [h for h in range(max(1, target_h - 4), target_h + 8) if total_dist % h == 0]
        if not valid_h:
            valid_h = [h for h in range(16, 50) if total_dist % h == 0]
        cycle_h = rng.choice(valid_h) if valid_h else total_dist
        start_offset = rng.randint(0, cycle_h - 1)

        # Each reel slot gets a pool of FLICKER_POOL glyph choices. A slot
        # that isn't flickery just repeats the same glyph in every pool slot
        # (so it never visibly changes); a flickery one gets independent
        # random glyphs plus a random phase, so different slots flicker at
        # different moments instead of the whole column changing in lockstep.
        variant_pool = []
        phase = []
        for _ in range(cycle_h):
            if rng.random() < flicker_chance:
                variant_pool.append(tuple(rng.choice(CHARS) for _ in range(FLICKER_POOL)))
            else:
                ch = rng.choice(CHARS)
                variant_pool.append((ch,) * FLICKER_POOL)
            phase.append(rng.randrange(FLICKER_POOL))

        columns.append({
            "speed": speed, "length": length, "cycle_h": cycle_h,
            "start_offset": start_offset, "variant_pool": tuple(variant_pool), "phase": tuple(phase),
        })
    return tuple(columns)


def generate(t: float, frame_idx: int, cols: int, rows: int, params: dict) -> FrameGrid:
    seed = int(params.get("seed", 42))
    color = params.get("color", True)
    hue = params.get("hue", "green")
    density = float(params.get("density", 0.85))
    trail_length = float(params.get("trail_length", 1.0))
    flicker_chance = float(params.get("flicker_chance", 0.12))
    loop_frames = int(params.get("loop_frames", 360))
    base_rgb = HUE_PALETTE.get(hue, HUE_PALETTE["green"])

    columns = _build_columns(cols, rows, seed, loop_frames, density, trail_length, flicker_chance)
    chars = np.full((rows, cols), " ", dtype="<U1")
    colors = np.zeros((rows, cols, 3), dtype=np.uint8) if color else None

    flicker_bucket = frame_idx // FLICKER_PERIOD

    for x, col in enumerate(columns):
        if col is None:
            continue
        head_pos = (col["start_offset"] + frame_idx * col["speed"]) % col["cycle_h"]
        head_y = head_pos - 5
        length = col["length"]
        for j in range(length):
            cy = head_y - j
            if 0 <= cy < rows:
                char_idx = (head_pos + j) % col["cycle_h"]
                variant_idx = (flicker_bucket + col["phase"][char_idx]) % FLICKER_POOL
                ch = col["variant_pool"][char_idx][variant_idx]
                chars[cy, x] = ch
                if color:
                    if j == 0:
                        colors[cy, x] = HEAD_COLOR
                    else:
                        fade = max(0.0, 1.0 - j / length)
                        colors[cy, x] = tuple(int(c * fade) for c in base_rgb)

    return FrameGrid(cols=cols, rows=rows, chars=chars, colors=colors)


SPEC = GeneratorSpec(
    key="matrix_rain",
    display_name="Matrix Digital Rain",
    fn=generate,
    params=[
        ParamSpec("seed", "Seed", "int", 42, 0, 9999, 1),
        ParamSpec("density", "Density", "float", 0.85, 0.1, 1.0, 0.05),
        ParamSpec("trail_length", "Trail length", "float", 1.0, 0.3, 2.5, 0.1),
        ParamSpec("flicker_chance", "Flicker amount", "float", 0.12, 0.0, 0.6, 0.02),
        ParamSpec("color", "Color", "bool", True),
        ParamSpec("hue", "Fade color", "choice", "green", choices=list(HUE_PALETTE.keys())),
    ],
    loop_frames=360,
    default_cols=64,
    default_rows=28,
)
register(SPEC)
