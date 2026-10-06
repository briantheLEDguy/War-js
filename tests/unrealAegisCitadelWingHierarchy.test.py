"""Wing detail dimensions; source checks do not grant scene approval."""
import math
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts/unreal'))
from aegis_citadel_mesh import UPPER_FACTOR
from aegis_citadel_wing_hierarchy import wing_hierarchy


class WingHierarchyTests(unittest.TestCase):
    def test_each_final_cornice_preserves_a_clear_pointed_window_head(self):
        for bounds in ((27000,34400,6010,9700),(28100,34200,9700,11900),
                       (29300,33600,11900,13700)):
            row=wing_hierarchy(*bounds,UPPER_FACTOR)
            c=row['cornice']
            self.assertAlmostEqual(c['finalTopCm']-c['finalBottomCm'],80)
            self.assertAlmostEqual(c['sourceDepthCm']*UPPER_FACTOR,80)
            self.assertGreater(c['finalBottomCm'],9000)
            self.assertGreaterEqual(c['finalBottomCm']-row['finalWindowRevealTopCm'],30-1e-9)
            self.assertGreaterEqual(row['windowHeightCm'],600)
            self.assertFalse(row['integrated'])
            self.assertFalse(row['nativeApproved'])

    def test_primary_rhythm_retains_every_structural_bay_and_end_accent(self):
        row=wing_hierarchy(27000,34400,6010,9700,UPPER_FACTOR)
        self.assertEqual(row['bayPositionsCm'],list(range(27360,34150,560)))
        self.assertTrue(row['structuralBayPositionsUnchanged'])
        for key in ('rodBayIndices','pinnacleBayIndices'):
            indices=row[key]
            self.assertEqual(indices[0],0)
            self.assertEqual(indices[-1],len(row['bayPositionsCm'])-1)
            self.assertEqual(len(indices),len(set(indices)))
            self.assertLess(len(indices),len(row['bayPositionsCm']))

    def test_invalid_or_lower_precinct_bounds_fail_closed(self):
        for args in ((10,0,6010,9700,UPPER_FACTOR),(0,10,9000,8000,UPPER_FACTOR),
                     (0,3000,6010,8990,UPPER_FACTOR),(0,3000,6010,9700,0),
                     (0,3000,6010,9700,math.nan)):
            with self.subTest(args=args),self.assertRaises(ValueError):
                wing_hierarchy(*args)


if __name__=='__main__':
    unittest.main()
