import copy
import importlib.util
import math
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location('t1_native_homes', Path(__file__).parents[1]/'scripts/unreal/t1_native_homes.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class NativeHomeAdapter(unittest.TestCase):
    def setUp(self):
        self.lot = dict(id='home', x=100, z=-200, rotY=0, interiorRequired=True,
            reservation=dict(width=14, depth=16, height=10), approach=[dict(x=100, z=-210), dict(x=90, z=-220)])
        self.template = dict(id='aegis_interior_00_home', kind='home', interior=True, upperFloor=False,
            mesh='/Game/LicensedKits/CapitalExpansion/V1/SM_home.SM_home', sha256='a'*64,
            origin=[0, -140, 500], extent=[320, 610, 500], entrance=[150, -630, 10], roomSize=[600, 900])

    def test_source_axes_pivot_floor_and_aligned_door_route(self):
        original = copy.deepcopy((self.lot, self.template))
        home = module.native_home(self.lot, self.template, 5)
        self.assertEqual((self.lot, self.template), original)
        self.assertEqual(home['yawDegrees'], -90)
        self.assertAlmostEqual(home['location'][0], -19860)
        self.assertAlmostEqual(home['location'][1], 10000)
        self.assertEqual(home['location'][2], 500)
        self.assertEqual(home['interiorRoute'][0], [-20490, 9850, 510])
        self.assertEqual(home['interiorRoute'][-1], home['interiorRoute'][0])
        self.assertEqual(home['interiorRoute'][0][1], home['interiorRoute'][1][1])
        self.assertFalse(home['visualApproved'])
        self.assertFalse(home['walkAccepted'])
        self.assertFalse(home['licensedDistributionApproved'])

    def test_rotated_lots_remain_rigid_and_invalid_bindings_fail(self):
        first = module.native_home(self.lot, self.template, 0)
        self.lot['rotY'] = math.pi/2
        second = module.native_home(self.lot, self.template, 0)
        for a, b in zip(first['interiorRoute'], second['interiorRoute']):
            self.assertAlmostEqual(a[0]+20000, b[1]-10000)
            self.assertAlmostEqual(a[1]-10000, -(b[0]+20000))
        self.template['mesh'] = '/Game/Unreviewed/SM_home'
        with self.assertRaises(ValueError):
            module.native_home(self.lot, self.template, 0)
        self.template['mesh'] = '/Game/LicensedKits/CapitalExpansion/V1/SM_home.SM_home'
        self.template['extent'][1] = 1000
        with self.assertRaises(ValueError):
            module.native_home(self.lot, self.template, 0)


if __name__ == '__main__':
    unittest.main()
