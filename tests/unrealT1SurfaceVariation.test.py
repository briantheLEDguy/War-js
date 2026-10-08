import math
from pathlib import Path
import sys
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts/unreal'))
from t1_surface_variation import surface_variation, validate_variation, rotated_uv


class SurfaceVariationTest(unittest.TestCase):
    def test_world_uv_is_continuous_and_rotation_preserves_physical_scale(self):
        row = surface_variation(); validate_variation(row)
        self.assertEqual(rotated_uv([300, 500, 700], 2, 0), [2.5, -1.5])
        a, b = rotated_uv([300, 500, 0], 3.66, .63), rotated_uv([300, 866, 5000], 3.66, .63)
        self.assertAlmostEqual(math.dist(a, b), 1)
        c = rotated_uv([300, 500.0001, 0], 3.66, .63)
        self.assertLess(math.dist(a, c), .000001)

    def test_recipe_rejects_nonfinite_or_out_of_range_controls(self):
        for field, value in [('secondaryScale', 0), ('macroMinimum', math.nan), ('vergeMetres', 50)]:
            with self.assertRaises(ValueError): validate_variation({**surface_variation(), field: value})
        with self.assertRaises(ValueError): rotated_uv([0, 0, 0], 0, 0)


if __name__ == '__main__': unittest.main()
