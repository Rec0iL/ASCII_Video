"""Stylized ASCII fire/flame effect: a flickering heat gradient rising from
the bottom of the grid. The flicker is built from a handful of closed-form
sine waves (not a stochastic cellular-automaton simulation), so any frame is
computable independently of the others and the loop closes exactly."""
from __future__ import annotations

import numpy as np

from ascii_video.core.grid import FrameGrid

from .base import GeneratorSpec, ParamSpec, register

FIRE_RAMP = " .:;+=xX$&@"

PALETTES: dict[str, list[tuple[float, tuple[int, int, int]]]] = {
    "classic": [
        (0.0, (0, 0, 0)), (0.25, (140, 0, 0)), (0.5, (255, 90, 0)),
        (0.75, (255, 200, 0)), (1.0, (255, 255, 230)),
    ],
    "blue": [
        (0.0, (0, 0, 0)), (0.25, (0, 30, 120)), (0.5, (0, 110, 220)),
        (0.75, (100, 200, 255)), (1.0, (230, 250, 255)),
    ],
    "toxic": [
        (0.0, (0, 0, 0)), (0.25, (20, 90, 0)), (0.5, (70, 200, 0)),
        (0.75, (170, 255, 40)), (1.0, (240, 255, 210)),
    ],
    "violet": [
        (0.0, (0, 0, 0)), (0.25, (60, 0, 90)), (0.5, (150, 0, 200)),
        (0.75, (230, 120, 255)), (1.0, (255, 230, 255)),
    ],
}


def _palette_to_rgb(intensity: np.ndarray, palette: str) -> np.ndarray:
    stops = PALETTES.get(palette, PALETTES["classic"])
    xs = [s[0] for s in stops]
    r = np.interp(intensity, xs, [s[1][0] for s in stops])
    g = np.interp(intensity, xs, [s[1][1] for s in stops])
    b = np.interp(intensity, xs, [s[1][2] for s in stops])
    return np.stack([r, g, b], axis=-1).astype(np.uint8)


def generate(t: float, frame_idx: int, cols: int, rows: int, params: dict) -> FrameGrid:
    loop_frames = params.get("loop_frames", 120)
    seed = int(params.get("seed", 7))
    intensity_boost = params.get("intensity", 1.0)
    turbulence = params.get("turbulence", 1.0)
    palette = params.get("palette", "classic")
    color = params.get("color", True)

    phase = (frame_idx % loop_frames) / loop_frames  # 0..1, exact at the seam

    x = np.arange(cols)
    y = np.arange(rows)
    X, Y = np.meshgrid(x, y)  # both shape (rows, cols)

    rng = np.random.default_rng(seed)
    # Fixed per-run spatial frequencies/phases for column-height flicker --
    # randomized once per seed, but every *time* term uses an integer
    # multiple of the loop phase, so the whole field is exactly periodic.
    n_waves = 4
    freqs = rng.uniform(1.5, 4.5, n_waves)
    phases0 = rng.uniform(0, 2 * np.pi, n_waves)
    time_mult = rng.integers(1, 3, n_waves)

    height = np.full(cols, rows * 0.55 * intensity_boost)
    for i in range(n_waves):
        height = height + (rows * 0.12 * intensity_boost) * np.sin(
            2 * np.pi * (freqs[i] * x / cols + time_mult[i] * phase) + phases0[i]
        )
    height = np.clip(height, 1, rows)

    dist_from_bottom = (rows - 1 - Y).astype(np.float64)
    base = np.clip(1.0 - dist_from_bottom / height[np.newaxis, :], 0.0, 1.0)

    # Rising texture: two octaves of noise scrolling upward, again with
    # integer time multipliers so it stays exactly periodic.
    tex = (
        0.6 * (0.5 + 0.5 * np.sin(2 * np.pi * (0.35 * X - 2 * phase) + 0.12 * Y))
        + 0.4 * (0.5 + 0.5 * np.sin(2 * np.pi * (0.9 * X + 0.17 * Y - 3 * phase) + 1.7))
    )
    tex = 1.0 - turbulence * 0.5 * (1.0 - tex)

    field = np.clip(base * tex, 0.0, 1.0)
    # Fire dies out faster than it flares -- push mid-tones down for a more
    # natural taper instead of a flat wedge.
    field = field ** 1.4

    ramp_arr = np.array(list(FIRE_RAMP), dtype="<U1")
    idx = np.clip((field * (len(ramp_arr) - 1)).astype(np.int64), 0, len(ramp_arr) - 1)
    chars = ramp_arr[idx]
    chars[field < 0.03] = " "

    colors = _palette_to_rgb(field, palette) if color else None

    return FrameGrid(cols=cols, rows=rows, chars=chars, colors=colors)


SPEC = GeneratorSpec(
    key="fire",
    display_name="ASCII Fire",
    fn=generate,
    params=[
        ParamSpec("seed", "Seed", "int", 7, 0, 9999, 1),
        ParamSpec("intensity", "Intensity", "float", 1.0, 0.5, 1.8, 0.1),
        ParamSpec("turbulence", "Turbulence", "float", 1.0, 0.0, 2.0, 0.1),
        ParamSpec("palette", "Palette", "choice", "classic", choices=list(PALETTES.keys())),
        ParamSpec("color", "Color", "bool", True),
    ],
    loop_frames=120,
    default_cols=70,
    default_rows=26,
)
register(SPEC)
