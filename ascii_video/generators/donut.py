"""Classic spinning ASCII donut/torus (z-buffer + luminance dot product).

Algorithm follows the well-known donut.c approach (also used in the sibling
ASCIImation project's gen_rotating_donut_frames), vectorized over all
theta/phi surface points instead of a nested Python loop.
"""
from __future__ import annotations

import numpy as np

from ascii_video.core.grid import FrameGrid

from .base import GeneratorSpec, ParamSpec, hsv_to_rgb_u8, register

LUM_CHARS = ".,-~:;=!*#$@"


def generate(t: float, frame_idx: int, cols: int, rows: int, params: dict) -> FrameGrid:
    loop_frames = params.get("loop_frames", 180)
    speed = params.get("speed", 1.0)
    ramp = params.get("ramp", LUM_CHARS)
    color = params.get("color", False)

    idx = frame_idx * speed
    A = idx * (4 * np.pi / loop_frames)
    B = idx * (2 * np.pi / loop_frames)

    theta = np.linspace(0, 2 * np.pi, 90, endpoint=False)
    phi = np.linspace(0, 2 * np.pi, 314, endpoint=False)
    T, P = np.meshgrid(theta, phi, indexing="xy")
    T = T.ravel()
    P = P.ravel()

    sin_t, cos_t = np.sin(T), np.cos(T)
    sin_p, cos_p = np.sin(P), np.cos(P)
    sin_A, cos_A = np.sin(A), np.cos(A)
    sin_B, cos_B = np.sin(B), np.cos(B)

    circle_x = cos_t + 2
    circle_y = sin_t

    x = circle_x * (cos_B * cos_p + sin_A * sin_B * sin_p) - circle_y * cos_A * sin_B
    y = circle_x * (sin_B * cos_p - sin_A * cos_B * sin_p) + circle_y * cos_A * cos_B
    z = circle_x * cos_A * sin_p + circle_y * sin_A
    ooz = 1.0 / (z + 5)

    xp = np.round(cols / 2 + cols * 0.35 * ooz * x).astype(np.int64)
    yp = np.round(rows / 2 - rows * 0.35 * ooz * y).astype(np.int64)

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
        ParamSpec("speed", "Speed", "float", 1.0, 0.1, 4.0, 0.1),
        ParamSpec("color", "Color", "bool", False),
    ],
    loop_frames=180,
    default_cols=70,
    default_rows=28,
)
register(SPEC)
