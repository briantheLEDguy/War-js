import unittest
import numpy as np
from texture_lods import reduce_pixels, rgba8_mip_bytes


class TextureLodTests(unittest.TestCase):
    def test_reduction_keeps_uniform_pigment_and_does_not_modify_master(self):
        pixels = np.full((8, 16, 4), [.13, .24, .41, 1], dtype=np.float32)
        original = pixels.copy()
        reduced = reduce_pixels(pixels, 2)
        self.assertEqual(reduced.shape, (2, 4, 4))
        np.testing.assert_allclose(reduced, np.broadcast_to([.13, .24, .41, 1], reduced.shape), atol=1e-6)
        np.testing.assert_array_equal(pixels, original)

    def test_filtered_normals_are_renormalized(self):
        pixels = np.ones((2, 2, 4), dtype=np.float32)
        pixels[:, 0, :3] = [.8, .5, .9]
        pixels[:, 1, :3] = [.2, .5, .9]
        reduced = reduce_pixels(pixels, 1, normal=True)
        np.testing.assert_allclose(reduced[0, 0, :3], [.5, .5, 1], atol=1e-6)

    def test_mip_estimate_includes_rectangular_tail(self):
        self.assertEqual(rgba8_mip_bytes(4, 2), (8 + 2 + 1) * 4)
        self.assertLess(rgba8_mip_bytes(1024, 512), rgba8_mip_bytes(4096, 2048) / 15)

    def test_invalid_atlas_shape_is_rejected(self):
        with self.assertRaises(ValueError):
            reduce_pixels(np.zeros((3, 5, 4)), 1)
