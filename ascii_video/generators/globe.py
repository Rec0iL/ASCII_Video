"""Rotating wireframe globe/sphere (latitude/longitude wireframe)."""
from __future__ import annotations

import numpy as np

from ascii_video.core.grid import FrameGrid

from .base import GeneratorSpec, ParamSpec, register


def generate(t: float, frame_idx: int, cols: int, rows: int, params: dict) -> FrameGrid:
    loop_frames = params.get("loop_frames", 48)
    speed = params.get("speed", 1.0)

    idx = frame_idx * speed
    angle = (idx / loop_frames) * 2 * np.pi

    chars = np.full((rows, cols), " ", dtype="<U1")
    radius = max(1, min(cols // 4, rows // 2 - 1))
    cx, cy = cols // 2, rows // 2

    for lat in range(-2, 3):
        lat_angle = lat * np.pi / 5
        r = radius * np.cos(lat_angle)
        y_offset = radius * np.sin(lat_angle) * 0.6
        for i in range(80):
            tt = (i / 80) * 2 * np.pi
            x3d = r * np.cos(tt)
            z3d = r * np.sin(tt)
            rx = x3d * np.cos(angle) - z3d * np.sin(angle)
            rz = x3d * np.sin(angle) + z3d * np.cos(angle)
            if rz > -radius * 0.3:
                px = int(cx + rx)
                py = int(cy + y_offset)
                if 0 <= px < cols and 0 <= py < rows:
                    chars[py, px] = "." if rz < radius * 0.5 else "-"

    for lon in range(6):
        lon_angle = lon * np.pi / 3 + angle
        for i in range(60):
            tt = (i / 60) * 2 * np.pi
            x3d = radius * np.cos(tt) * np.cos(lon_angle)
            y3d = radius * np.sin(tt)
            z3d = radius * np.cos(tt) * np.sin(lon_angle)
            if z3d > -radius * 0.2:
                px = int(cx + x3d)
                py = int(cy + y3d * 0.6)
                if 0 <= px < cols and 0 <= py < rows:
                    chars[py, px] = "|" if abs(x3d) < 2 else "/"

    for i in range(120):
        tt = (i / 120) * 2 * np.pi
        x3d = radius * np.cos(tt)
        z3d = radius * np.sin(tt)
        rx = x3d * np.cos(angle) - z3d * np.sin(angle)
        rz = x3d * np.sin(angle) + z3d * np.cos(angle)
        if rz > -radius * 0.1:
            px = int(cx + rx)
            if 0 <= px < cols:
                chars[cy, px] = "="

    return FrameGrid(cols=cols, rows=rows, chars=chars, colors=None)


SPEC = GeneratorSpec(
    key="globe",
    display_name="Rotating Wireframe Globe",
    fn=generate,
    params=[
        ParamSpec("speed", "Speed", "float", 1.0, 0.1, 4.0, 0.1),
    ],
    loop_frames=48,
    default_cols=50,
    default_rows=22,
)
register(SPEC)
