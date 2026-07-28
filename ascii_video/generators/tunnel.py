"""Classic polar-coordinate "tunnel" effect: angle/depth around the center
mapped to a scrolling checkerboard texture, with distance-based shading.
Both rotation and zoom are integer multiples of the loop phase, so it
closes exactly (a non-integer checker_freq can leave a faint seam)."""
from __future__ import annotations

import numpy as np

from ascii_video.core.grid import FrameGrid

from .base import GeneratorSpec, ParamSpec, hsv_to_rgb_u8, register

TUNNEL_RAMP = " .:-=+*#%@"


def generate(t: float, frame_idx: int, cols: int, rows: int, params: dict) -> FrameGrid:
    loop_frames = params.get("loop_frames", 120)
    rotate_speed = params.get("rotate_speed", 1.0)
    zoom_speed = params.get("zoom_speed", 1.0)
    checker_freq = params.get("checker_freq", 8.0)
    hue_deg = params.get("hue", 25.0)
    color = params.get("color", True)

    char_aspect = 2.0
    cx, cy = cols / 2.0, rows / 2.0
    x = np.arange(cols)
    y = np.arange(rows)
    X, Y = np.meshgrid(x, y)  # shape (rows, cols)
    dx = X - cx
    dy = (Y - cy) * char_aspect
    dist = np.hypot(dx, dy) + 1e-6
    angle = np.arctan2(dy, dx)

    idx_r = (frame_idx * rotate_speed) % loop_frames
    idx_z = (frame_idx * zoom_speed) % loop_frames
    rot_phase = (idx_r / loop_frames) * 2 * np.pi
    zoom_phase = (idx_z / loop_frames) * 2 * np.pi

    depth = (checker_freq / dist) - (zoom_phase / (2 * np.pi)) * checker_freq
    ang_coord = (angle + rot_phase) / (2 * np.pi) * checker_freq
    checker = (np.floor(depth).astype(np.int64) + np.floor(ang_coord).astype(np.int64)) % 2

    max_dist = np.hypot(cx, cy * char_aspect)
    shade = np.clip(1.0 - dist / max_dist, 0.0, 1.0)
    shade = shade * (0.45 + 0.55 * checker)

    ramp_arr = np.array(list(TUNNEL_RAMP), dtype="<U1")
    idx_arr = np.clip((shade * (len(ramp_arr) - 1)).astype(np.int64), 0, len(ramp_arr) - 1)
    chars = ramp_arr[idx_arr]

    colors = None
    if color:
        hue = np.full(shade.shape, (hue_deg % 360) / 360.0)
        colors = hsv_to_rgb_u8(hue, np.full_like(hue, 0.6), shade)

    return FrameGrid(cols=cols, rows=rows, chars=chars, colors=colors)


SPEC = GeneratorSpec(
    key="tunnel",
    display_name="Tunnel",
    fn=generate,
    params=[
        ParamSpec("rotate_speed", "Rotate speed", "float", 1.0, -4.0, 4.0, 0.5),
        ParamSpec("zoom_speed", "Zoom speed", "float", 1.0, 0.0, 4.0, 0.5),
        ParamSpec("checker_freq", "Texture freq", "float", 8.0, 2.0, 20.0, 1.0),
        ParamSpec("hue", "Hue", "float", 25.0, 0.0, 360.0, 5.0),
        ParamSpec("color", "Color", "bool", True),
    ],
    loop_frames=120,
    default_cols=70,
    default_rows=30,
)
register(SPEC)
