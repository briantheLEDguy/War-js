import math
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts/unreal'))
from t1_building_materials import rock_scale_recipe, ATLAS, CHANNELS

class BuildingMaterialScaleTests(unittest.TestCase):
    def channels(self):
        return {key: ATLAS + suffix + '.T_MH_02_Atlas_02_' + suffix for key, suffix in CHANNELS.items()}

    def test_admits_only_whole_rock_channels_without_mutating_source(self):
        textures = self.channels(); previous = dict(textures)
        recipe = rock_scale_recipe(textures, 'wall', 2)
        self.assertEqual(textures, previous)
        self.assertEqual(recipe['channels'], textures)
        self.assertEqual(recipe['uvChannel'], 0)
        self.assertFalse(recipe['geometryChanged'])
        self.assertFalse(recipe['appearanceApproved'])

    def test_rejects_mixed_atlases_foreign_channels_and_non_wall_roles(self):
        for key in CHANNELS:
            textures = self.channels(); textures[key] = textures[key].replace('Atlas_02', 'Atlas_01')
            self.assertIsNone(rock_scale_recipe(textures, 'wall'))
            del textures[key]
            self.assertIsNone(rock_scale_recipe(textures, 'wall'))
        for role in ('roof', 'floor', 'original', 'furniture'):
            self.assertIsNone(rock_scale_recipe(self.channels(), role))

    def test_bounds_detail_scale_and_rejects_nonfinite_or_boolean_values(self):
        for scale in (0, 1, 3.01, math.nan, math.inf, -math.inf, True, '2'):
            with self.assertRaises(ValueError): rock_scale_recipe(self.channels(), 'wall', scale)
        self.assertEqual(rock_scale_recipe(self.channels(), 'wall', 3)['scale'], 3)

if __name__ == '__main__': unittest.main()
