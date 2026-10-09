from pathlib import Path
import math
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts/unreal'))
from t1_battlefield_views import neighborhood_views


class BattlefieldViewsTest(unittest.TestCase):
    def test_camera_stays_on_a_route_and_aims_at_the_cluster(self):
        paths=[dict(points=[dict(x=0,z=0),dict(x=100,z=0),dict(x=100,z=100)])]
        cells=[dict(id='zone_cell_grove',placements=[dict(x=40,z=30),dict(x=60,z=30)])]
        views=neighborhood_views(paths,cells)
        self.assertEqual(views,[('landscape_grove',dict(x=50,z=0),dict(x=50,z=30))])
        self.assertEqual(paths[0]['points'][0],dict(x=0,z=0))

    def test_empty_and_coincident_neighborhoods_do_not_produce_invalid_views(self):
        path=[dict(points=[dict(x=0,z=0),dict(x=100,z=0)])]
        self.assertEqual(neighborhood_views(path,[dict(id='empty',placements=[])]),[])
        self.assertEqual(neighborhood_views(path,[dict(id='on_route',placements=[dict(x=50,z=0)])]),[])
        with self.assertRaises(ValueError): neighborhood_views([dict(points=[dict(x=0,z=0),dict(x=0,z=0)])],[])
        with self.assertRaises(ValueError): neighborhood_views(path,[dict(id='invalid',placements=[dict(x=math.nan,z=0)])])


if __name__=='__main__': unittest.main()
