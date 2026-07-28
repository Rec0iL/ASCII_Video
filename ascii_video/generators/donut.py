"""Classic spinning ASCII donut/torus (z-buffer + luminance dot product).

Algorithm follows the well-known donut.c approach (also used in the sibling
ASCIImation project's gen_rotating_donut_frames), vectorized over all
theta/phi surface points instead of a nested Python loop. Exposes the usual
"cool options" for this effect: independent rotation speeds on each axis,
tube/ring radii, viewing distance, zoom, charset and color.
"""
from __future__ import annotations

import numpy as np

from ascii_video.core.grid import FrameGrid
from ascii_video.core.ramp import RAMP_PRESETS

from .base import GeneratorSpec, ParamSpec, hsv_to_rgb_u8, register

LUM_CHARS = ".,-~:;=!*#$@"
DONUT_RAMP_CHOICES = {"luminance": LUM_CHARS, **RAMP_PRESETS}


def generate(t: float, frame_idx: int, cols: int, rows: int, params: dict) -> FrameGrid:
    loop_frames = params.get("loop_frames", 180)
    spin_x = params.get("spin_x", 2.0)
    spin_y = params.get("spin_y", 1.0)
    r1 = params.get("r1", 1.0)   # tube radius
    r2 = params.get("r2", 2.0)   # ring (center-to-tube) radius
    k2 = params.get("k2", 5.0)   # viewing distance
    zoom = params.get("zoom", 1.0)
    ramp = DONUT_RAMP_CHOICES.get(params.get("ramp", "luminance"), LUM_CHARS)
    color = params.get("color", False)

    # Wrap via modulo *before* scaling to radians, same reasoning as
    # sine_wave: lands frame_idx == loop_frames on angle == 0.0 bit-for-bit,
    # matching frame 0 exactly at the seam (only exact for integer spin_x/y).
    idx_a = (frame_idx * spin_x) % loop_frames
    idx_b = (frame_idx * spin_y) % loop_frames
    A = (idx_a / loop_frames) * 2 * np.pi
    B = (idx_b / loop_frames) * 2 * np.pi

    theta = np.linspace(0, 2 * np.pi, 90, endpoint=False)
    phi = np.linspace(0, 2 * np.pi, 314, endpoint=False)
    T, P = np.meshgrid(theta, phi, indexing="xy")
    T = T.ravel()
    P = P.ravel()

    sin_t, cos_t = np.sin(T), np.cos(T)
    sin_p, cos_p = np.sin(P), np.cos(P)
    sin_A, cos_A = np.sin(A), np.cos(A)
    sin_B, cos_B = np.sin(B), np.cos(B)

    circle_x = r1 * cos_t + r2
    circle_y = r1 * sin_t

    x = circle_x * (cos_B * cos_p + sin_A * sin_B * sin_p) - circle_y * cos_A * sin_B
    y = circle_x * (sin_B * cos_p - sin_A * cos_B * sin_p) + circle_y * cos_A * cos_B
    z = circle_x * cos_A * sin_p + circle_y * sin_A
    ooz = 1.0 / (z + k2)

    scale = 0.35 * zoom
    xp = np.round(cols / 2 + cols * scale * ooz * x).astype(np.int64)
    yp = np.round(rows / 2 - rows * scale * ooz * y).astype(np.int64)

    L = (
        cos_p * cos_t * sin_B
        - cos_A * cos_t * sin_p
        - sin_A * sin_t
        + cos_B * (cos_A * sin_t - cos_t * sin_A * sin_p)
    )

    valid = (xp >= 0) & (xp < cols) & (yp >= 0) & (yp < rows)
    xp, yp, ooz_v, L_v, P_v = xp[valid], yp[valid], ooz[valid], L[valid], P[valid]
    flat_idx = yp * cols + xp

    zbuf = np.full(cols * rows, -np.inf)
    np.maximum.at(zbuf, flat_idx, ooz_v)
    winning = ooz_v >= (zbuf[flat_idx] - 1e-9)

    ramp_arr = np.array(list(ramp), dtype="<U1")
    n = len(ramp_arr)
    lum_idx = np.clip((L_v * 8).astype(np.int64), 0, n - 1)

    chars = np.full(rows * cols, " ", dtype="<U1")
    chars[flat_idx[winning]] = ramp_arr[lum_idx[winning]]
    chars = chars.reshape(rows, cols)

    colors = None
    if color:
        colors_flat = np.zeros((rows * cols, 3), dtype=np.uint8)
        hue = (P_v[winning] / (2 * np.pi)) % 1.0
        colors_flat[flat_idx[winning]] = hsv_to_rgb_u8(hue, np.full_like(hue, 0.6), np.full_like(hue, 1.0))
        colors = colors_flat.reshape(rows, cols, 3)

    return FrameGrid(cols=cols, rows=rows, chars=chars, colors=colors)


SPEC = GeneratorSpec(
    key="donut",
    display_name="Spinning Donut (Torus)",
    fn=generate,
    params=[
        ParamSpec("spin_x", "Spin X", "float", 2.0, 0.0, 6.0, 1.0),
        ParamSpec("spin_y", "Spin Y", "float", 1.0, 0.0, 6.0, 1.0),
        ParamSpec("r1", "Tube radius", "float", 1.0, 0.2, 2.0, 0.1),
        ParamSpec("r2", "Ring radius", "float", 2.0, 0.5, 4.0, 0.1),
        ParamSpec("k2", "Distance", "float", 5.0, 3.0, 12.0, 0.5),
        ParamSpec("zoom", "Zoom", "float", 1.0, 0.3, 2.5, 0.1),
        ParamSpec("ramp", "Charset", "choice", "luminance", choices=list(DONUT_RAMP_CHOICES.keys())),
        ParamSpec("color", "Color", "bool", False),
    ],
    loop_frames=180,
    default_cols=70,
    default_rows=28,
)
register(SPEC)
