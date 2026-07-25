import numpy as np

from ascii_video.core.edges import (
    block_reduce_mean,
    direction_to_bucket,
    edge_mask_and_chars,
    sobel_magnitude_direction,
)


def test_block_reduce_mean_exact_divide():
    arr = np.array([[1, 1, 2, 2], [1, 1, 2, 2], [3, 3, 4, 4], [3, 3, 4, 4]], dtype=np.float32)
    out = block_reduce_mean(arr, 2, 2)
    assert out.shape == (2, 2)
    np.testing.assert_allclose(out, [[1, 2], [3, 4]])


def test_block_reduce_mean_uneven_pads():
    arr = np.ones((3, 5), dtype=np.float32)
    out = block_reduce_mean(arr, 2, 2)
    assert out.shape == (2, 2)
    np.testing.assert_allclose(out, np.ones((2, 2)))


def test_direction_to_bucket_range():
    direction = np.linspace(-np.pi, np.pi, 50)
    buckets = direction_to_bucket(direction, 4)
    assert buckets.min() >= 0
    assert buckets.max() < 4


def test_sobel_on_vertical_edge_points_horizontally():
    img = np.zeros((20, 20), dtype=np.float32)
    img[:, 10:] = 255.0
    magnitude, direction = sobel_magnitude_direction(img)
    # Strongest response should be at the column boundary.
    col_energy = magnitude.sum(axis=0)
    assert col_energy.argmax() in (9, 10, 11)


def test_edge_mask_all_flat_image_has_no_edges():
    magnitude = np.zeros((4, 4), dtype=np.float32)
    direction = np.zeros((4, 4), dtype=np.float32)
    is_edge, chars = edge_mask_and_chars(magnitude, direction, threshold=0.35)
    assert not is_edge.any()
    assert chars.shape == (4, 4)
