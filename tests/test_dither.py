import numpy as np

from ascii_video.core.dither import dither_floyd_steinberg


def test_dither_output_in_range():
    rng = np.random.default_rng(0)
    brightness = rng.random((10, 10))
    levels = 5
    out = dither_floyd_steinberg(brightness, levels)
    assert out.min() >= 0
    assert out.max() < levels


def test_dither_flat_midgray_alternates():
    # A flat 0.5 field with 2 levels should produce a mix of both levels
    # (dithering), not collapse to a single level everywhere.
    brightness = np.full((8, 8), 0.5)
    out = dither_floyd_steinberg(brightness, levels=2)
    assert set(np.unique(out).tolist()) == {0, 1}
