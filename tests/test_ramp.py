import numpy as np

from ascii_video.core.ramp import brightness_to_chars, luminance


def test_luminance_black_and_white():
    rgb = np.array([[[0, 0, 0], [255, 255, 255]]], dtype=np.uint8)  # BGR order
    lum = luminance(rgb)
    assert lum[0, 0] == 0.0
    assert lum[0, 1] == 1.0


def test_brightness_to_chars_endpoints():
    brightness = np.array([[0.0, 1.0]])
    chars = brightness_to_chars(brightness, ramp=" .:-=+*#%@")
    assert chars[0, 0] == " "
    assert chars[0, 1] == "@"


def test_brightness_to_chars_invert():
    brightness = np.array([[0.0, 1.0]])
    chars = brightness_to_chars(brightness, ramp=" .:-=+*#%@", invert=True)
    assert chars[0, 0] == "@"
    assert chars[0, 1] == " "
