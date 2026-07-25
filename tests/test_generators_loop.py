import pytest

from ascii_video.generators import GENERATORS


@pytest.mark.parametrize("key", list(GENERATORS.keys()))
def test_generator_seam_closes(key):
    """frame[0] must equal frame[loop_frames] at default params -- no jump
    at the loop seam when the animation is played back on repeat."""
    spec = GENERATORS[key]
    params = spec.defaults()
    params["loop_frames"] = spec.loop_frames

    if key == "dvd_bounce":
        from ascii_video.generators.dvd_bounce import loop_frames_for
        params["loop_frames"] = loop_frames_for(spec.default_cols, spec.default_rows)

    frame0 = spec.fn(0.0, 0, spec.default_cols, spec.default_rows, params)
    frame_n = spec.fn(0.0, params["loop_frames"], spec.default_cols, spec.default_rows, params)

    assert (frame0.chars == frame_n.chars).all(), f"{key}: seam mismatch at frame {params['loop_frames']}"


@pytest.mark.parametrize("key", list(GENERATORS.keys()))
def test_generator_produces_nonblank_output(key):
    spec = GENERATORS[key]
    params = spec.defaults()
    params["loop_frames"] = spec.loop_frames
    mid = spec.loop_frames // 3
    grid = spec.fn(0.0, mid, spec.default_cols, spec.default_rows, params)
    assert grid.chars.shape == (spec.default_rows, spec.default_cols)
    assert (grid.chars != " ").any()
