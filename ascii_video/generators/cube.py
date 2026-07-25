"""Rotating 3D wireframe cube."""
from __future__ import annotations

import math

import numpy as np

from ascii_video.core.grid import FrameGrid

from .base import GeneratorSpec, ParamSpec, register

NODES = [
    (-1, -1, -1), (1, -1, -1), (1, 1, -1), (-1, 1, -1),
    (-1, -1, 1), (1, -1, 1), (1, 1, 1), (-1, 1, 1),
]
EDGES = [
    (0, 1), (1, 2), (2, 3), (3, 0),
    (4, 5), (5, 6), (6, 7), (7, 4),
    (0, 4), (1, 5), (2, 6), (3, 7),
]


def generate(t: float, frame_idx: int, cols: int, rows: int, params: dict) -> FrameGrid:
    loop_frames = params.get("loop_frames", 48)
    speed = params.get("speed", 1.0)
    color = params.get("color", False)

    idx = frame_idx * speed
    angle = (idx / loop_frames) * 2 * math.pi
    sin_a, cos_a = math.sin(angle), math.cos(angle)
    sin_b, cos_b = math.sin(angle * 2), math.cos(angle * 2)

    chars = np.full((rows, cols), " ", dtype="<U1")
    proj = []
    for x, y, z in NODES:
        xz = x * cos_a - z * sin_a
        zz = x * sin_a + z * cos_a
        yz = y * cos_b - zz * sin_b
        zz = y * sin_b + zz * cos_b
        fov = 3.6
        px = int(cols / 2 + (xz * fov / (zz + 4.2)) * (cols / 2.4))
        py = int(rows / 2 + (yz * fov / (zz + 4.2)) * (rows / 2.4))
        proj.append((px, py))
        if 0 <= px < cols and 0 <= py < rows:
            chars[py, px] = "#"

    for p1, p2 in EDGES:
        x0, y0 = proj[p1]
        x1, y1 = proj[p2]
        dx, dy = abs(x1 - x0), abs(y1 - y0)
        steps = max(dx, dy, 1)
        for i in range(steps + 1):
            cx = int(x0 + (x1 - x0) * i / steps)
            cy = int(y0 + (y1 - y0) * i / steps)
            if 0 <= cx < cols and 0 <= cy < rows and chars[cy, cx] == " ":
                chars[cy, cx] = "*"

    colors = None
    if color:
        colors = np.zeros((rows, cols, 3), dtype=np.uint8)
        colors[chars != " "] = (80, 220, 255)

    return FrameGrid(cols=cols, rows=rows, chars=chars, colors=colors)


SPEC = GeneratorSpec(
    key="cube",
    display_name="3D Spinning Wireframe Cube",
    fn=generate,
    params=[
        ParamSpec("speed", "Speed", "float", 1.0, 0.1, 4.0, 0.1),
        ParamSpec("color", "Color", "bool", False),
    ],
    loop_frames=48,
    default_cols=54,
    default_rows=24,
)
register(SPEC)
