import unittest
import numpy as np
from joint_correctives import JointRelaxation, compact_modes, caudal_weight_transfer, fascia_displacement


class JointCorrectiveTests(unittest.TestCase):
    @staticmethod
    def patch():
        # A small curved point lattice crosses the actual proximal mask; one
        # attached sample lies outside it to represent an unaffected landmark.
        points = np.array([[.12+.01*np.sin(y*8), y, z] for z in np.linspace(.38, .72, 7) for y in np.linspace(.07, .42, 8)])
        edges = []
        for row in range(7):
            for col in range(8):
                at = row*8+col
                if col < 7: edges.append([at, at+1])
                if row < 6: edges.append([at, at+8])
        return points, np.array(edges)

    def test_rest_and_rigid_body_motion_are_exactly_invariant(self):
        points, edges = self.patch()
        relaxation = JointRelaxation(points, edges, 1)
        identity = np.broadcast_to(np.eye(3), (len(points), 3, 3))
        np.testing.assert_allclose(relaxation.delta(points, identity), 0, atol=1e-12)
        theta = .83
        matrix = np.array([[1, 0, 0], [0, np.cos(theta), -np.sin(theta)], [0, np.sin(theta), np.cos(theta)]])
        posed = points@matrix.T+[.13, -.28, .05]
        np.testing.assert_allclose(relaxation.delta(posed, np.broadcast_to(matrix, identity.shape)), 0, atol=1e-12)

    def test_unaffected_landmarks_and_uv_duplicates_stay_exact(self):
        points, edges = self.patch()
        points = np.concatenate([points, points[[8]], [[.04, -.7, 1.05]]])
        edges = np.concatenate([edges, [[56, 9], [56, 16], [57, 57]]])
        relaxation = JointRelaxation(points, edges, 1)
        posed = points.copy(); posed[20:35, 0] -= .025
        delta = relaxation.delta(posed, np.broadcast_to(np.eye(3), (len(points), 3, 3)))
        np.testing.assert_array_equal(delta[-1], [0, 0, 0])
        np.testing.assert_allclose(delta[8], delta[56], atol=1e-12)
        self.assertGreater(np.linalg.norm(delta).max(), .001)

    def test_compact_modes_reconstruct_zero_and_known_deformations(self):
        rng = np.random.default_rng(74)
        bases = rng.normal(size=(3, 30, 3))*.001
        coefficients = rng.normal(size=(40, 3))
        samples = np.einsum('sk,knc->snc', coefficients, bases)
        modes, weights, evidence = compact_modes(samples, 6)
        self.assertEqual(len(modes), 3)
        self.assertLess(evidence['maximum_reconstruction_error_m'], 1e-12)
        self.assertLessEqual(abs(weights).max(), 1)
        np.testing.assert_allclose(np.einsum('sk,knc->snc', weights, modes), samples, atol=1e-12)
        np.testing.assert_array_equal(np.zeros(len(modes))@modes.reshape(len(modes), -1), 0)

    def test_caudal_skin_keeps_pelvis_ownership_without_changing_contacts(self):
        weights = {'haunch_L': .65, 'pelvis': .35}
        result = caudal_weight_transfer([.14, .42, .58], weights, 1)
        self.assertGreater(result['pelvis'], .91)
        self.assertAlmostEqual(sum(result.values()), 1)
        self.assertLessEqual(len(result), 4)
        for point, original in [([.145, .375, .235], {'hock_L': .7, 'shin_L': .3}), ([.1, -.3, .56], {'shoulder_L': .6, 'chest': .4}), ([.05, -.7, 1.05], {'head': 1})]:
            self.assertEqual(caudal_weight_transfer(point, original, 1), original)

    def test_fascia_support_has_no_rest_extension_head_or_hoof_offset(self):
        points = np.array([[.18, .18, .49], [-.18, .18, .49], [.05, -.7, 1.05], [.145, .315, .039]])
        np.testing.assert_array_equal(fascia_displacement(points, 1, np.eye(3), {1: 0, -1: .8}), 0)
        moved = fascia_displacement(points, 1, np.eye(3), {1: -.6, -1: .4})
        self.assertGreater(moved[0, 0], .035)
        np.testing.assert_array_equal(moved[1:], 0)


if __name__ == '__main__':
    unittest.main()
