import unittest
from gait_curves import foot_trajectory


class GaitCurvesTests(unittest.TestCase):
    def test_landing_and_takeoff_match_planted_velocity(self):
        stance, stride, lift, step = .24, .432, .135, 1e-6
        for phase in [0, stance]:
            left = foot_trajectory(phase-step, stance, stride, lift)
            right = foot_trajectory(phase+step, stance, stride, lift)
            self.assertAlmostEqual((right[0]-left[0])/(2*step), stride/stance, places=4)
            self.assertAlmostEqual((right[1]-left[1])/(2*step), 0, places=4)

    def test_stance_has_no_vertical_slide_and_constant_speed(self):
        a = foot_trajectory(.04, .24, .432, .135)
        b = foot_trajectory(.14, .24, .432, .135)
        self.assertEqual(a[1], 0)
        self.assertEqual(b[1], 0)
        self.assertAlmostEqual((b[0]-a[0])/.1, .432/.24)

    def test_cycle_seam_and_swing_clearance(self):
        self.assertEqual(foot_trajectory(0,.24,.432,.135),foot_trajectory(1,.24,.432,.135))
        self.assertAlmostEqual(foot_trajectory(.62,.24,.432,.135)[1],.135)

    def test_return_does_not_overextend_anatomical_stride(self):
        positions=[foot_trajectory(i/1000,.24,.432,.135)[0] for i in range(1001)]
        self.assertLess(max(abs(p) for p in positions),.432*.56)
