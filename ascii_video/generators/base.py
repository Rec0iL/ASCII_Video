"""Generator plugin contract + registry.

A generator is a pure function of (t, frame_idx, cols, rows, params) so any
frame can be rendered independently (needed for scrubbing/exporting out of
order), and loop-closure comes from closed-form math (frame_idx % loop_frames)
rather than an accumulated simulation.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

import numpy as np

from ascii_video.core.grid import FrameGrid

GeneratorFn = Callable[[float, int, int, int, dict], FrameGrid]


@dataclass
class ParamSpec:
    key: str
    label: str
    kind: str  # "float" | "int" | "bool" | "choice"
    default: Any
    min: float | None = None
    max: float | None = None
    step: float | None = None
    choices: list[str] | None = None


@dataclass
class GeneratorSpec:
    key: str
    display_name: str
    fn: GeneratorFn
    params: list[ParamSpec] = field(default_factory=list)
    loop_frames: int = 120
    default_cols: int = 70
    default_rows: int = 28

    def defaults(self) -> dict:
        return {p.key: p.default for p in self.params}


GENERATORS: dict[str, GeneratorSpec] = {}


def register(spec: GeneratorSpec) -> None:
    GENERATORS[spec.key] = spec


def hsv_to_rgb_u8(h: np.ndarray, s: np.ndarray, v: np.ndarray) -> np.ndarray:
    """Vectorized HSV (0..1 each) -> uint8 RGB, shape (..., 3)."""
    h6 = np.mod(h, 1.0) * 6.0
    i = (np.floor(h6).astype(np.int64)) % 6
    f = h6 - np.floor(h6)
    p = v * (1 - s)
    q = v * (1 - s * f)
    tt = v * (1 - s * (1 - f))
    conditions = [i == 0, i == 1, i == 2, i == 3, i == 4, i == 5]
    r = np.select(conditions, [v, q, p, p, tt, v])
    g = np.select(conditions, [tt, v, v, q, p, p])
    b = np.select(conditions, [p, p, tt, v, v, q])
    rgb = np.stack([r, g, b], axis=-1)
    return np.clip(rgb * 255, 0, 255).astype(np.uint8)
