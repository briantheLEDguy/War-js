import math
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts/unreal'))
from t1_town_ground import patch_height, valley_height, fitted_height, reframe_inventory, ground_normals


class GroundTests(unittest.TestCase):
    def test_seam_and_court(self):
        self.assertEqual(patch_height(265, 5, 17, 44), 17)
        self.assertEqual(valley_height(55, -40, 44), 44)
        self.assertGreater(abs(valley_height(-100, 100, 44)-valley_height(0, -100, 44)), 5)
        epsilon = .001
        self.assertLess(abs(patch_height(265-epsilon, 5, 17, 44)-17), .00001)

    def test_independent_pads(self):
        lots = [dict(x=0, z=0, rotY=0, halfWidth=3, halfDepth=4, height=50),
                dict(x=30, z=0, rotY=math.pi/2, halfWidth=3, halfDepth=4, height=56)]
        self.assertEqual(fitted_height(0, 0, 40, lots), 50)
        self.assertEqual(fitted_height(30, 0, 40, lots), 56)
        self.assertEqual(fitted_height(15, 0, 40, lots), 40)

    def test_complete_frame(self):
        states = {key: dict(location=[10, 22, 5], rotation=[0, 5, 0], scale=[1, 2, 3], mesh='retained')
                  for key in ('house', 'house_bed', 'other')}
        result, counts = reframe_inventory(states, {'house': dict(old=[10, 20, 0], new=[100, 200, 10], yaw=90)})
        self.assertEqual(counts, {'house': 2})
        self.assertEqual(result['house_bed']['location'], [98, 200, 15])
        self.assertEqual(result['house_bed']['rotation'], [0, 95, 0])
        self.assertEqual(result['house_bed']['scale'], [1, 2, 3])
        self.assertEqual(result['other'], states['other'])
        self.assertEqual(states['house']['location'], [10, 22, 5])
        with self.assertRaises(ValueError): reframe_inventory(states, {'missing': {}})
        with self.assertRaises(ValueError):
            reframe_inventory(states, {'house': {}, 'house_bed': {}})

    def test_upward_normals(self):
        self.assertEqual(ground_normals([[0, 0, 0], [1, 0, 0], [0, 1, 0]], [0, 2, 1]), [[0, 0, 1]]*3)


if __name__ == '__main__': unittest.main()
