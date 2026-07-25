"""Video-frame -> FrameGrid: the shared core render function.

Used identically by live preview (on-demand, single frame) and by export
(dispatched per-frame across a process pool).
"""
from __future__ import annotations

from dataclasses import dataclass, field

import cv2
import numpy as np

from .color import bgr_to_rgb_u8
from .dither import dither_floyd_steinberg
from .edges import block_reduce_circular_mean, block_reduce_mean, edge_mask_and_chars, sobel_magnitude_direction
from .grid import FrameGrid
from .ramp import DEFAULT_RAMP, brightness_to_chars, luminance


@dataclass
class PipelineParams:
    char_aspect: float = 2.0          # h:w ratio of one monospace character cell
    edge_threshold: float = 0.35      # 0..1, adaptive against this frame's max gradient
    edge_upscale: float = 3.0         # edge-detection intermediate resolution multiplier vs. cell grid
    ramp: str = DEFAULT_RAMP
    invert: bool = False
    dither: bool = False
    color: bool = False
    direction_chars: list[str] = field(default_factory=lambda: ["-", "/", "|", "\\"])


def compute_rows(frame_w: int, frame_h: int, cols: int, char_aspect: float = 2.0) -> int:
    """Derive row count from column count + source aspect so shapes stay round."""
    rows = round(cols * (frame_h / frame_w) / char_aspect)
    return max(1, rows)


def render_frame(bgr_frame: np.ndarray, cols: int, rows: int, params: PipelineParams) -> FrameGrid:
    frame_h, frame_w = bgr_frame.shape[:2]

    # Cell-resolution resize feeds brightness + color sampling.
    cell_res = cv2.resize(bgr_frame, (cols, rows), interpolation=cv2.INTER_AREA)

    # Higher-resolution intermediate feeds Sobel so edges survive downscaling.
    edge_w = max(cols, int(cols * params.edge_upscale))
    edge_h = max(rows, int(rows * params.edge_upscale))
    edge_res = cv2.resize(bgr_frame, (edge_w, edge_h), interpolation=cv2.INTER_AREA)
    gray = cv2.cvtColor(edge_res, cv2.COLOR_BGR2GRAY).astype(np.float32)

    magnitude, direction = sobel_magnitude_direction(gray)
    cell_magnitude = block_reduce_mean(magnitude, rows, cols)
    cell_direction = block_reduce_circular_mean(direction, rows, cols)

    is_edge, edge_chars = edge_mask_and_chars(
        cell_magnitude, cell_direction, params.edge_threshold, params.direction_chars
    )

    brightness = luminance(cell_res)

    if params.dither:
        levels = len(params.ramp)
        b = 1.0 - brightness if params.invert else brightness
        idx = dither_floyd_steinberg(b, levels)
        ramp_arr = np.array(list(params.ramp), dtype="<U1")
        fill_chars = ramp_arr[idx]
    else:
        fill_chars = brightness_to_chars(brightness, params.ramp, params.invert)

    chars = np.where(is_edge, edge_chars, fill_chars)

    colors = bgr_to_rgb_u8(cell_res) if params.color else None

    return FrameGrid(cols=cols, rows=rows, chars=chars, colors=colors)
