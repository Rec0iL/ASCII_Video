"""Concentric expanding rings ("radio waves"/ripple) emanating from a center
point. Each ring's radius is a closed-form sawtooth of frame_idx modulo the
loop, so any frame is independently computable and the loop closes exactly."""
from __future__ import annotations

import numpy as np

from ascii_video.core.grid import FrameGrid

from .base import GeneratorSpec, ParamSpec, hsv_to_rgb_u8, register

WAVE_CHARS = " .:-=+*#@"


def generate(t: float, frame_idx: int, cols: int, rows: int, params: dict) -> FrameGrid:
    loop_frames = params.get("loop_frames", 96)
    speed = params.get("speed", 1.0)
    num_rings = int(params.get("num_rings", 4))
    ring_spacing = params.get("ring_spacing", 6.0)
    thickness = params.get("thickness", 1.0)
    hue_deg = params.get("hue", 130.0)
    color = params.get("color", True)

    char_aspect = 2.0  # monospace cells are ~2:1 h:w -- widen y-distance so rings read as circles
    cx, cy = cols / 2.0, rows / 2.0
    x = np.arange(cols)
    y = np.arange(rows)
    X, Y = np.meshgrid(x, y)  # shape (rows, cols)
    dist = np.hypot(X - cx, (Y - cy) * char_aspect)

    max_radius = ring_spacing * num_rings
    idx = (frame_idx * speed) % loop_frames
    base_r = (idx / loop_frames) * max_radius

    field = np.zeros((rows, cols))
    for k in range(num_rings):
        ring_r = (base_r + k * ring_spacing) % max_radius
        d = np.abs(dist - ring_r)
        fade = 1.0 - (ring_r / max_radius)  # a freshly-emitted ring is brightest
        field += fade * np.clip(1.0 - d / (1.2 * thickness), 0.0, 1.0)
    field = np.clip(field, 0.0, 1.0)

    ramp_arr = np.array(list(WAVE_CHARS), dtype="<U1")
    idx_arr = np.clip((field * (len(ramp_arr) - 1)).astype(np.int64), 0, len(ramp_arr) - 1)
    chars = ramp_arr[idx_arr]
    chars[field < 0.05] = " "

    colors = None
    if color:
        hue = np.full(field.shape, (hue_deg % 360) / 360.0)
        colors = hsv_to_rgb_u8(hue, np.full_like(hue, 0.75), field)

    return FrameGrid(cols=cols, rows=rows, chars=chars, colors=colors)


SPEC = GeneratorSpec(
    key="radio_waves",
    display_name="Radio Waves",
    fn=generate,
    params=[
        ParamSpec("speed", "Speed", "float", 1.0, 0.1, 4.0, 0.1),
        ParamSpec("num_rings", "Ring count", "int", 4, 1, 10, 1),
        ParamSpec("ring_spacing", "Ring spacing", "float", 6.0, 2.0, 14.0, 0.5),
        ParamSpec("thickness", "Thickness", "float", 1.0, 0.3, 3.0, 0.1),
        ParamSpec("hue", "Hue", "float", 130.0, 0.0, 360.0, 5.0),
        ParamSpec("color", "Color", "bool", True),
    ],
    loop_frames=96,
    default_cols=60,
    default_rows=26,
)
register(SPEC)
