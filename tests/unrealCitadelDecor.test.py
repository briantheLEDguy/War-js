"""Placement mutations protect routes, native geometry and existing furnishings."""
import copy
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts/unreal'))
from aegis_citadel_mesh import Mesh
from aegis_citadel_furnishing_density import ARCHITECTURE_GROUPS
from citadel_decor import checked_decor, checked_requests


def architecture(z=6010, obstacle=None):
    meshes = [Mesh(key) for key in sorted(ARCHITECTURE_GROUPS)]
    for mesh in meshes:
        mesh.face([[25000, -7000, z], [34000, -7000, z], [34000, 7000, z], [25000, 7000, z]])
    if obstacle:
        meshes[-1].face(obstacle)
    return meshes


class DecorTests(unittest.TestCase):
    def setUp(self):
        self.row = dict(id='decor_archive_reading', group='west_archive',
                        source='public/assets/models/prop_aegis_civic_bench.glb',
                        point=[29500, -6100, 6010], scale=.8, yawDegrees=90, centerPlan=True)
        self.plan = dict(rooms=[dict(id='west_archive', bounds=[[28800, -6800, 6010], [33000, -4300, 8800]])],
                         routes=[], spawnApproaches=[], objectives=[], optionalObjectives=[],
                         gameplayPads=[], gates=[])

    def run_plan(self, **kwargs):
        return checked_decor(self.plan, kwargs.get('architecture', architecture()),
                             kwargs.get('existing', []), kwargs.get('requests', [self.row]),
                             kwargs.get('residents', []))

    def test_actual_props_have_nine_floor_probes_without_native_approval(self):
        meshes, ledger, inventory = self.run_plan()
        self.assertEqual(len(meshes), 1)
        self.assertEqual(len(inventory), 8)
        self.assertEqual(len(ledger[0]['architectureClearance']['floorSamples']), 9)
        self.assertTrue(ledger[0]['individuallyEditable'])
        self.assertFalse(ledger[0]['nativeClearanceVerified'])
        self.assertFalse(ledger[0]['visualApproved'])

    def test_shell_walls_and_unsupported_floors_reject_placements(self):
        x, y, z = self.row['point']
        obstacle = [[x, y-500, z], [x, y+500, z], [x, y, z+500]]
        with self.assertRaisesRegex(ValueError, 'Architecture intersection'):
            self.run_plan(architecture=architecture(obstacle=obstacle))
        with self.assertRaisesRegex(ValueError, 'Unsupported floor'):
            self.run_plan(architecture=architecture(z=5990))
        with self.assertRaisesRegex(ValueError, 'eight-group'):
            self.run_plan(architecture=architecture()[1:])

    def test_route_and_spawn_protection_are_elevation_aware(self):
        p = self.row['point']
        self.plan['routes'] = [dict(id='archive_entry', points=[[p[0]-1000, p[1], p[2]],
                                                             [p[0]+1000, p[1], p[2]]], width=600)]
        with self.assertRaisesRegex(ValueError, 'archive_entry'):
            self.run_plan()
        for point in self.plan['routes'][0]['points']:
            point[2] += 1200
        self.run_plan()
        self.plan['spawnApproaches'] = [dict(index=0, points=[p], widthCm=600)]
        with self.assertRaisesRegex(ValueError, 'spawn_0'):
            self.run_plan()

    def test_capture_service_gate_and_resident_volume_remain_clear(self):
        p = self.row['point']
        self.plan['optionalObjectives'] = [p]
        with self.assertRaisesRegex(ValueError, 'Objective'):
            self.run_plan()
        self.plan['optionalObjectives'] = []
        self.plan['gameplayPads'] = [dict(id='archive_service', footprintCentreFloorCm=p,
                                       maximumFootprintRadiusCm=150, maximumHeightCm=240)]
        with self.assertRaisesRegex(ValueError, 'Gameplay/service'):
            self.run_plan()
        self.plan['gameplayPads'] = []
        self.plan['gates'] = [dict(leaves=[dict(point=p, width=600, height=1000)])]
        with self.assertRaisesRegex(ValueError, 'Gate'):
            self.run_plan()
        self.plan['gates'] = []
        with self.assertRaisesRegex(ValueError, 'Resident'):
            self.run_plan(residents=[dict(id='scribe', pointCm=p, clearanceRadiusCm=100, heightCm=240)])

    def test_old_objects_and_new_objects_cannot_overlap_or_alias(self):
        _, ledger, _ = self.run_plan()
        old = dict(id='retained_desk', boundsCm=ledger[0]['boundsCm'])
        with self.assertRaisesRegex(ValueError, 'Decor overlap'):
            self.run_plan(existing=[old])
        old['id'] = self.row['id']
        with self.assertRaisesRegex(ValueError, 'aliases'):
            self.run_plan(existing=[old])
        second = {**self.row, 'id': 'decor_other_reading'}
        with self.assertRaisesRegex(ValueError, 'Decor overlap'):
            self.run_plan(requests=[self.row, second])

    def test_bounds_cannot_leave_a_signed_room(self):
        self.row['point'][1] = -6790
        with self.assertRaisesRegex(ValueError, 'signed room'):
            self.run_plan()

    def test_unknown_sources_mounts_and_nonfinite_transforms_fail_closed(self):
        changes = [dict(source='../secret.glb'), dict(group='new_room'), dict(point=[1, 2, float('nan')]),
                   dict(scale=0), dict(scale=True), dict(yawDegrees=float('inf')), dict(centerPlan=False),
                   dict(mount='ceiling'), dict(id='Decor_same'), dict(point=[0, 0])]
        for change in changes:
            with self.subTest(change=change), self.assertRaises(ValueError):
                checked_requests([{**self.row, **change}])
        with self.assertRaisesRegex(ValueError, 'Duplicate'):
            checked_requests([self.row, copy.deepcopy(self.row)])
        with self.assertRaises(ValueError):
            checked_requests([])


if __name__ == '__main__':
    unittest.main()
