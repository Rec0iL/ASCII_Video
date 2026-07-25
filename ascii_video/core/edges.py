"""Sobel edge detection and direction-to-character bucketing."""
from __future__ import annotations

import cv2
import numpy as np

# 4-way bucketing at 45 degree offsets. Order matches bucket index 0..3.
DIRECTION_CHARS = ["-", "/", "|", "\\"]


def sobel_magnitude_direction(gray: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """gray: float32 2D array. Returns (magnitude, direction_radians)."""
    gx = cv2.Sobel(gray, cv2.CV_32F, 1, 0, ksize=3)
    gy = cv2.Sobel(gray, cv2.CV_32F, 0, 1, ksize=3)
    magnitude = np.hypot(gx, gy)
    direction = np.arctan2(gy, gx)
    return magnitude, direction


def block_reduce_mean(arr: np.ndarray, out_rows: int, out_cols: int) -> np.ndarray:
    """Downsample a 2D array to (out_rows, out_cols) by averaging blocks.

    Pads with edge values if the source doesn't divide evenly.
    """
    h, w = arr.shape
    pad_h = (-h) % out_rows
    pad_w = (-w) % out_cols
    if pad_h or pad_w:
        arr = np.pad(arr, ((0, pad_h), (0, pad_w)), mode="edge")
        h, w = arr.shape
    block_h = h // out_rows
    block_w = w // out_cols
    reshaped = arr.reshape(out_rows, block_h, out_cols, block_w)
    return reshaped.mean(axis=(1, 3))


def block_reduce_circular_mean(direction: np.ndarray, out_rows: int, out_cols: int) -> np.ndarray:
    """Downsample an angle field (radians) respecting circular wraparound."""
    sin_part = block_reduce_mean(np.sin(direction), out_rows, out_cols)
    cos_part = block_reduce_mean(np.cos(direction), out_rows, out_cols)
    return np.arctan2(sin_part, cos_part)


def direction_to_bucket(direction: np.ndarray, num_buckets: int = 4) -> np.ndarray:
    """Map radians in [-pi, pi] to an integer bucket index in [0, num_buckets)."""
    # Gradient direction is perpendicular to the edge itself, so rotate by
    # 90deg to get the edge's own orientation before bucketing.
    edge_angle = direction + np.pi / 2
    step = np.pi / num_buckets
    bucket = np.round(edge_angle / step).astype(np.int64) % num_buckets
    return bucket


def edge_mask_and_chars(
    magnitude: np.ndarray,
    direction: np.ndarray,
    threshold: float,
    chars: list[str] | None = None,
) -> tuple[np.ndarray, np.ndarray]:
    """Returns (is_edge boolean mask, char array) for a cell-resolution grid.

    threshold is applied relative to this frame's own max magnitude (adaptive),
    in [0, 1].
    """
    chars = chars or DIRECTION_CHARS
    num_buckets = len(chars)
    max_mag = float(magnitude.max()) if magnitude.size else 0.0
    if max_mag <= 1e-6:
        is_edge = np.zeros(magnitude.shape, dtype=bool)
    else:
        is_edge = (magnitude / max_mag) > threshold
    bucket = direction_to_bucket(direction, num_buckets)
    char_lut = np.array(chars, dtype="<U1")
    edge_chars = char_lut[bucket]
    return is_edge, edge_chars
