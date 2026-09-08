import unittest
import numpy as np
from texture_detail import pelt_strokes, tangent_normals
from surface_detail import deer_face_position


class TextureTests(unittest.TestCase):
    def test_normal_signs_follow_actual_pixel_order(self):
        y, x = np.mgrid[:4, :4].astype(float)
        bottom = tangent_normals(x + 2 * y, 1)
        raster = tangent_normals(x + 2 * y, 1, False)
        self.assertLess(bottom[1, 1, 0], 0)
        self.assertLess(bottom[1, 1, 1], 0)
        self.assertGreater(raster[1, 1, 1], 0)
        np.testing.assert_allclose(np.linalg.norm(bottom, axis=-1), 1)

    def test_strokes_are_repeatable_and_have_no_cell_lattice(self):
        a, pigment = pelt_strokes(128, 27)
        b, _ = pelt_strokes(128, 27)
        np.testing.assert_array_equal(a, b)
        self.assertGreater(np.std(a), .1)
        self.assertLess(abs(float(np.corrcoef(a[:, :-16].ravel(), a[:, 16:].ravel())[0, 1])), .12)
        self.assertTrue(np.isfinite(pigment).all())

    def test_face_planes_are_mirrored_and_leave_body_untouched(self):
        eye = [.079, -.644, 1.082]
        left = deer_face_position((.07, -.616, 1.021), eye)
        right = deer_face_position((-.07, -.616, 1.021), eye)
        self.assertAlmostEqual(left[0], -right[0])
        self.assertGreater(left[0], .07)
        self.assertEqual(deer_face_position((.15, .2, .7), eye), (.15, .2, .7))
