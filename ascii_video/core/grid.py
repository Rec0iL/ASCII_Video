"""The shared frame representation every renderer and exporter consumes."""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass
class FrameGrid:
    """A single rendered ASCII frame.

    chars is a (rows, cols) array of single characters. colors, if present,
    is a (rows, cols, 3) uint8 array of per-cell RGB; None means monochrome.
    """

    cols: int
    rows: int
    chars: np.ndarray
    colors: np.ndarray | None = None

    def __post_init__(self) -> None:
        if self.chars.shape != (self.rows, self.cols):
            raise ValueError(
                f"chars shape {self.chars.shape} does not match "
                f"(rows={self.rows}, cols={self.cols})"
            )
        if self.colors is not None and self.colors.shape != (self.rows, self.cols, 3):
            raise ValueError(
                f"colors shape {self.colors.shape} does not match "
                f"(rows={self.rows}, cols={self.cols}, 3)"
            )

    def to_text(self) -> str:
        return "\n".join("".join(row) for row in self.chars)

    @staticmethod
    def blank(cols: int, rows: int, fill: str = " ") -> "FrameGrid":
        chars = np.full((rows, cols), fill, dtype="<U1")
        return FrameGrid(cols=cols, rows=rows, chars=chars)
