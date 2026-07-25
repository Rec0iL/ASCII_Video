"""Per-cell color sampling."""
from __future__ import annotations

import numpy as np


def bgr_to_rgb_u8(cell_res_bgr: np.ndarray) -> np.ndarray:
    """cell_res_bgr: (rows, cols, 3) uint8 in BGR (OpenCV order). Returns RGB uint8."""
    return cell_res_bgr[..., ::-1].copy()
