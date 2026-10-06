"""Portable geometry checks for the independent sentinel proposal, not approval."""
import math
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts' / 'unreal'))
from aegis_citadel_statue import LEGACY_NODE_SCALE, NOMINAL_ENVELOPE_CM, build_sentinel, sculpture_report


class SentinelProposalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mesh = build_sentinel()
        cls.report = sculpture_report(cls.mesh)

    def test_existing_effective_envelope_and_foot_origin(self):
        self.assertGreaterEqual(self.report['triangles'], 25_000)
        self.assertLessEqual(self.report['triangles'], 40_000)
        for actual, maximum in zip(self.report['dimensionsCm'], NOMINAL_ENVELOPE_CM):
            self.assertLessEqual(actual, maximum)
        self.assertEqual(self.report['boundsCm'][2][0], 0)
        # The original 780 cm GLB node was uniformly scaled before placement.
        self.assertAlmostEqual(self.report['dimensionsCm'][2], 780, delta=1e-8)
        self.assertAlmostEqual(self.report['reviewEffectiveDimensionsCm'][2], 780 * LEGACY_NODE_SCALE, delta=1e-8)
        scaled = sculpture_report(build_sentinel(LEGACY_NODE_SCALE))
        self.assertAlmostEqual(scaled['dimensionsCm'][2], 780 * LEGACY_NODE_SCALE, delta=1e-8)
        self.assertEqual(self.report['faceDirectionNative'], [-1, 0, 0])
        self.assertEqual(self.report['proposedFootWitness']['actualMinimumZCm'], 135)
        original = self.report['originalFootWitness']['primitiveWitnesses'][0]
        self.assertAlmostEqual(original['actualMinimumYMetres'] * 100, 135, delta=0.001)
        self.assertEqual(original['footVertexCount'], 40)
        self.assertTrue(self.report['standingPlaneFit']['xyPreservedFromPreviousProposal'])

    def test_all_triangle_corners_have_coherent_normals_and_uvs(self):
        m = self.mesh
        self.assertEqual(len(m.positions), len(m.normals))
        self.assertEqual(len(m.positions), len(m.uvs))
        self.assertEqual(len(m.indices), len(m.triangle_materials) * 3)
        for p, n, uv in zip(m.positions, m.normals, m.uvs):
            self.assertTrue(all(math.isfinite(q) for q in p + n + uv))
            self.assertAlmostEqual(sum(q * q for q in n), 1, places=8)
        for offset in range(0, len(m.indices), 3):
            ids = m.indices[offset:offset + 3]
            self.assertTrue(all(0 <= i < len(m.positions) for i in ids))
            a, b, c = [m.positions[i] for i in ids]
            u, v = [b[k] - a[k] for k in range(3)], [c[k] - a[k] for k in range(3)]
            n = [u[1] * v[2] - u[2] * v[1], u[2] * v[0] - u[0] * v[2], u[0] * v[1] - u[1] * v[0]]
            length = math.sqrt(sum(q * q for q in n))
            self.assertGreater(length, 1e-7)
            for i in ids:
                self.assertGreater(sum(n[k] / length * m.normals[i][k] for k in range(3)), 0)
            a, b, c = [m.uvs[i] for i in ids]
            determinant = (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])
            self.assertGreater(abs(determinant), 1e-12)

    def test_authored_parts_and_proposal_boundaries(self):
        names = {part['name'] for part in self.mesh.parts}
        for expected in ('tailored_cuirass', 'sculpted_helmet_calotte', 'closed_helm_bevor',
                         'weighted_cloak_deep_folds', 'convex_carved_kite_shield',
                         'shield_carved_sun_heraldry_orb', 'sword_sculpted_pommel'):
            self.assertIn(expected, names)
        self.assertTrue(any('articulated_finger' in name for name in names))
        self.assertTrue(any('layered_tasset' in name for name in names))
        self.assertTrue(self.report['proposalOnly'])
        for flag in ('integrated', 'nativeCollisionVerified', 'visualApproved'):
            self.assertIs(self.report[flag], False)
        self.assertEqual(sculpture_report(build_sentinel())['geometrySha256'], self.report['geometrySha256'])

    def test_court_placement_stays_inside_measured_existing_world_bounds(self):
        # Actual retained court_oath source bounds measured by the native survey.
        bounds = [(20528.1753, 21064.761), (-264.761, 264.761), (4710, 5743.4948)]
        point = (20800, 0, 4710)
        scaled = build_sentinel(LEGACY_NODE_SCALE * 1.97)
        for p in scaled.positions:
            for i in range(3):
                self.assertGreaterEqual(p[i] + point[i], bounds[i][0] - 0.001)
                self.assertLessEqual(p[i] + point[i], bounds[i][1] + 0.001)

    def test_invalid_transform_rejected(self):
        for scale in (0, -1, float('nan'), float('inf')):
            with self.assertRaises(ValueError): build_sentinel(scale)


if __name__ == '__main__': unittest.main()
