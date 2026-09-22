import sys
import unittest
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts/unreal'))
from world_landscapes import surface_kind


class LandscapeTests(unittest.TestCase):
    def test_only_authored_land_receives_ground_collision(self):
        self.assertEqual(surface_kind({'name':'tile_surface_LOD0'}),'ground')
        self.assertEqual(surface_kind({'name':'tile_roads'}),'road')
        self.assertEqual(surface_kind({'name':'tile_peat_water','extras':{'noGroundSupport':True}}),'water')
        with self.assertRaises(ValueError): surface_kind({'name':'unreviewed_surface'})
        with self.assertRaises(ValueError): surface_kind({'name':'tile_peat_water','extras':{'noGroundSupport':False}})


if __name__=='__main__': unittest.main()
