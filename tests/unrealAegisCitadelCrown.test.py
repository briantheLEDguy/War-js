"""Source-only proposal invariants; never substitutes for native visual/route review."""
import math
from pathlib import Path
import struct
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts/unreal'))
from aegis_citadel_crown import BELFRIES, ENVELOPE_CM, build_keep_crown, front_lancets
from aegis_citadel_mesh import MATERIALS, cross


def _dot(a, b):
    return sum(x*y for x, y in zip(a, b))


def _ray_hits(mesh, origin, end):
    direction = [b-a for a, b in zip(origin, end)]
    hits = []
    for offset in range(0, len(mesh.indices), 3):
        a, b, c = [mesh.positions[i] for i in mesh.indices[offset:offset+3]]
        e1, e2 = [[p[i]-a[i] for i in range(3)] for p in (b, c)]
        h = cross(direction, e2)
        det = _dot(e1, h)
        if abs(det) < 1e-8:
            continue
        inverse = 1/det
        s = [origin[i]-a[i] for i in range(3)]
        u = inverse*_dot(s, h)
        if not 0 <= u <= 1:
            continue
        q = cross(s, e1)
        v = inverse*_dot(direction, q)
        if v < 0 or u+v > 1:
            continue
        t = inverse*_dot(e2, q)
        if 0 <= t <= 1:
            hits.append(t)
    return hits


class CitadelCrownProposalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mesh, cls.contract = build_keep_crown()

    def test_final_upper_only_geometry_is_within_existing_keep_envelope(self):
        low, high = ENVELOPE_CM
        self.assertGreater(len(self.mesh.indices), 5000)
        for position in self.mesh.positions:
            self.assertGreater(position[2], 9000)
            for axis in range(3):
                self.assertTrue(low[axis] <= position[axis] <= high[axis], position)
        self.assertEqual(max(p[2] for p in self.mesh.positions), 17200)
        self.assertEqual(self.contract['coordinates'], 'final_unreal_centimetres')
        self.assertIn('append_after_upper_transform', self.contract['integration'])

    def test_reference_crown_has_three_distinct_substantial_joined_chambers(self):
        self.assertEqual(len(BELFRIES), 3)
        self.assertEqual(len({body.eaves for body in BELFRIES}), 3)
        self.assertEqual(len({body.ridge for body in BELFRIES}), 3)
        for body in BELFRIES:
            self.assertGreaterEqual(body.x1-body.x0, 3300)
            self.assertGreaterEqual(body.width, 1700)
            self.assertGreaterEqual(body.eaves-body.bottom, 1750)
            self.assertTrue(body.x0 > ENVELOPE_CM[0][0] and body.x1 < ENVELOPE_CM[1][0])
        # The solid podium covers all three base footprints; its shoulders bridge
        # both side masses to the central nave above that continuous base.
        self.assertTrue(_ray_hits(self.mesh, [30150, -1800, 10750], [30150, -2000, 10750]))
        self.assertTrue(_ray_hits(self.mesh, [30150, 1800, 10750], [30150, 2000, 10750]))
        self.assertEqual([row['frontLancets'] for row in self.contract['belfries']], [2, 3, 2])
        self.assertEqual([row['revealDepthCm'] for row in self.contract['belfries']], [290, 420, 290])
        central = self.contract['belfries'][1]
        self.assertGreater(central['frontBays'][1]['widthCm'], central['frontBays'][0]['widthCm']*2)
        self.assertGreater(central['frontBays'][1]['heightCm'], central['frontBays'][0]['heightCm'])

    def test_deep_lancets_are_actual_clear_holes_beside_solid_masonry(self):
        for body in BELFRIES:
            depth = 420 if body.id == 'central_belfry' else 290
            for centre, base, width, height in front_lancets(body):
                # Each paired traceried lancet retains a clear sub-opening.
                y = centre+width*.25
                z = base+height*.33
                self.assertFalse(_ray_hits(self.mesh, [body.x0-180, y, z], [body.x0+depth+180, y, z]), body.id)
            z = body.bottom+850
            pier_y = body.y+780 if body.id == 'central_belfry' else body.y
            self.assertTrue(_ray_hits(self.mesh,
                [body.x0-180, pier_y, z], [body.x0+depth+180, pier_y, z]), body.id)

    def test_sloping_roofs_and_unequal_attached_spires_form_a_supported_cluster(self):
        towers = [tower for body in self.contract['belfries'] for tower in body['towers']]
        self.assertEqual(len(towers), 6)
        self.assertEqual(len({tower['peakCm'] for tower in towers}), 6)
        for body in self.contract['belfries']:
            self.assertGreater(body['ridge']-body['eaves'], 500)
            self.assertGreaterEqual(body['roofSetbackCm'], 350)
        for tower in towers:
            self.assertGreaterEqual(tower['widthCm'], 650)
            self.assertGreater(tower['peakCm']-tower['stoneTopCm'], 1300)
            # The actual upper opening is above the keep coping and remains
            # clear through the complete tower, rather than facing a roof skin.
            x, y = tower['centreCm']
            z = tower['stoneTopCm']-205
            half = tower['widthCm']/2
            self.assertFalse(_ray_hits(self.mesh, [x-half-1, y, z], [x+half+1, y, z]), tower['id'])
        for index, material in enumerate(self.mesh.triangle_materials):
            if MATERIALS[material] != 'slate':
                continue
            points = [self.mesh.positions[i] for i in self.mesh.indices[index*3:index*3+3]]
            spans = [max(p[axis] for p in points)-min(p[axis] for p in points) for axis in range(3)]
            # The pitched connecting roofs remain below the larger central
            # lantern and its clustered spires rather than becoming a gable.
            if max(spans[:2]) > 700:
                self.assertLessEqual(spans[2], 2300)
        cluster=self.contract['centralCluster']
        self.assertEqual(cluster['peakCm'],17200)
        self.assertGreater(cluster['widthCm'],1300)
        self.assertEqual(len(cluster['satelliteTurrets']),4)
        self.assertGreater(cluster['stoneTopCm'],max(body['ridge'] for body in self.contract['belfries']))
        self.assertEqual(self.contract['coreCompressionHighestZCm'],14200)

    def test_actual_source_faces_normals_and_float32_uvs_remain_valid(self):
        f32 = lambda x: struct.unpack('f', struct.pack('f', x))[0]
        self.assertEqual(len(self.mesh.positions), len(self.mesh.normals))
        self.assertEqual(len(self.mesh.positions), len(self.mesh.uvs))
        self.assertEqual(len(self.mesh.indices)//3, len(self.mesh.triangle_materials))
        for offset in range(0, len(self.mesh.indices), 3):
            ids = self.mesh.indices[offset:offset+3]
            a, b, c = [self.mesh.positions[i] for i in ids]
            normal = cross([b[i]-a[i] for i in range(3)], [c[i]-a[i] for i in range(3)])
            length = math.sqrt(_dot(normal, normal))
            self.assertGreater(length, 1e-5, (offset, ids))
            normal = [v/length for v in normal]
            for index in ids:
                self.assertAlmostEqual(_dot(self.mesh.normals[index], self.mesh.normals[index]), 1, places=6)
                self.assertGreater(_dot(normal, self.mesh.normals[index]), .999999, offset)
            uv = [[f32(v) for v in self.mesh.uvs[i]] for i in ids]
            area = (uv[1][0]-uv[0][0])*(uv[2][1]-uv[0][1])-(uv[1][1]-uv[0][1])*(uv[2][0]-uv[0][0])
            self.assertGreater(abs(area), 1e-10, offset)
            self.assertTrue(all(math.isfinite(v) for row in (a, b, c, *uv) for v in row))
            self.assertIn(self.mesh.triangle_materials[offset//3], range(len(MATERIALS)))

    def test_proposal_is_deterministic_and_mints_no_approval(self):
        repeated, contract = build_keep_crown()
        self.assertEqual(repeated.export(), self.mesh.export())
        self.assertEqual(contract, self.contract)
        self.assertTrue(contract['proposalOnly'])
        for flag in ('visualApproval', 'nativeCollisionApproval', 'routeApproval'):
            self.assertIs(contract[flag], False)
        self.assertTrue(contract['freshNativeEvidenceRequired'])


if __name__ == '__main__':
    unittest.main()
