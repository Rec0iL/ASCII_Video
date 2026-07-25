import numpy as np
import pytest

from ascii_video.core.grid import FrameGrid


def test_blank_grid_shape_and_fill():
    g = FrameGrid.blank(cols=5, rows=3)
    assert g.chars.shape == (3, 5)
    assert (g.chars == " ").all()


def test_to_text_joins_rows():
    chars = np.array([["a", "b"], ["c", "d"]], dtype="<U1")
    g = FrameGrid(cols=2, rows=2, chars=chars)
    assert g.to_text() == "ab\ncd"


def test_mismatched_chars_shape_raises():
    chars = np.array([["a", "b"]], dtype="<U1")
    with pytest.raises(ValueError):
        FrameGrid(cols=5, rows=1, chars=chars)


def test_mismatched_colors_shape_raises():
    chars = np.array([["a", "b"]], dtype="<U1")
    colors = np.zeros((1, 3, 3), dtype=np.uint8)
    with pytest.raises(ValueError):
        FrameGrid(cols=2, rows=1, chars=chars, colors=colors)
