"""Floyd-Steinberg error diffusion at ASCII-grid resolution.

This runs on the (small) cell grid, not the source pixels, so a plain
row-sequential Python loop is cheap even though it can't be vectorized
(each cell's error depends on already-diffused neighbors).
"""
from __future__ import annotations

import numpy as np


def dither_floyd_steinberg(brightness: np.ndarray, levels: int) -> np.ndarray:
    """brightness: 0..1 float (rows, cols). Returns int level indices 0..levels-1."""
    rows, cols = brightness.shape
    buf = brightness.astype(np.float64).copy()
    out = np.zeros((rows, cols), dtype=np.int64)
    step = 1.0 / (levels - 1) if levels > 1 else 1.0

    for y in range(rows):
        for x in range(cols):
            old = buf[y, x]
            level = int(round(np.clip(old, 0.0, 1.0) / step)) if levels > 1 else 0
            level = max(0, min(levels - 1, level))
            out[y, x] = level
            quant = level * step
            err = old - quant

            if x + 1 < cols:
                buf[y, x + 1] += err * 7 / 16
            if y + 1 < rows:
                if x - 1 >= 0:
                    buf[y + 1, x - 1] += err * 3 / 16
                buf[y + 1, x] += err * 5 / 16
                if x + 1 < cols:
                    buf[y + 1, x + 1] += err * 1 / 16

    return out
