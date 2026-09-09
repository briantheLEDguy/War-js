import unittest
import numpy as np
from hamstring_contour import hamstring_displacement


class HamstringContourTests(unittest.TestCase):
    def test_rest_and_previously_reviewed_quarters_stay_exact(self):
        points = np.array([[.13, .40, .45], [-.13, .40, .45], [0, .4, .46]])
        for flexions in [{1: 0, -1: 0}, {1: -.409261, -1: -.562997}, {1: .463559, -1: .889783}, {1: .703267, -1: .444907}]:
            np.testing.assert_array_equal(hamstring_displacement(points, 1, np.eye(3), flexions), 0)

    def test_peak_tuck_curves_only_its_lower_caudal_region(self):
        points = np.array([[.13, .4, .45], [-.13, .4, .45], [.13, .40, .72], [.02, .52, .65],
                           [.05, -.7, 1.05], [.145, .315, .039], [.13, .1, .45]])
        delta = hamstring_displacement(points, 1, np.eye(3), {1: -.62, -1: -.3})
        self.assertGreater(delta[0, 2], .06)
        self.assertLessEqual(delta[0, 2], .065)
        np.testing.assert_array_equal(delta[0, :2], 0)
        np.testing.assert_array_equal(delta[1:], 0)

    def test_lift_follows_pelvis_rotation_and_physical_scale(self):
        points = np.array([[.13, .4, .45], [0, .4, .46]])
        angle = .7; rotation = np.array([[1, 0, 0], [0, np.cos(angle), -np.sin(angle)], [0, np.sin(angle), np.cos(angle)]])
        flexions = {1: -.61, -1: -.59}
        ordinary = hamstring_displacement(points, 1, np.eye(3), flexions)
        np.testing.assert_allclose(hamstring_displacement(points*.9, .9, rotation, flexions), ordinary@rotation.T*.9, atol=1e-12)


if __name__ == '__main__':
    unittest.main()
