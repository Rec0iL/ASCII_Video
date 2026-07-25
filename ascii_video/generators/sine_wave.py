"""Animated sine wave oscillator with a second-harmonic overtone."""
from __future__ import annotations

import numpy as np

from ascii_video.core.grid import FrameGrid

from .base import GeneratorSpec, ParamSpec, register


def generate(t: float, frame_idx: int, cols: int, rows: int, params: dict) -> FrameGrid:
    loop_frames = params.get("loop_frames", 48)
    speed = params.get("speed", 1.0)

    # Wrap via modulo *before* scaling to radians so frame_idx == loop_frames
    # lands on phase == 0.0 bit-for-bit, matching frame 0 exactly at the seam
    # (adding a full 2*pi and relying on sin()'s argument reduction to cancel
    # it does not reliably round-trip at float precision).
    idx = (frame_idx * speed) % loop_frames
    phase = (idx / loop_frames) * 2 * np.pi

    chars = np.full((rows, cols), " ", dtype="<U1")
    mid_y = rows // 2
    chars[mid_y, :] = "-"

    for x in range(cols):
        val = np.sin((x / cols) * 4 * np.pi + phase)
        val += 0.4 * np.sin((x / cols) * 8 * np.pi - phase * 2)
        y = int(mid_y - val * (rows / 2 - 1.5))
        y = max(0, min(rows - 1, y))
        chars[y, x] = "+" if chars[y, x] == "-" else "*"
        step = 1 if y > mid_y else -1
        if y != mid_y:
            for ty in range(mid_y + step, y, step):
                if 0 <= ty < rows:
                    chars[ty, x] = ":"

    return FrameGrid(cols=cols, rows=rows, chars=chars, colors=None)


SPEC = GeneratorSpec(
    key="sine_wave",
    display_name="Sine Wave Oscillator",
    fn=generate,
    params=[
        ParamSpec("speed", "Speed", "float", 1.0, 0.1, 4.0, 0.1),
    ],
    loop_frames=48,
    default_cols=60,
    default_rows=18,
)
register(SPEC)
