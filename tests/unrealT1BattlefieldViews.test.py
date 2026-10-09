from pathlib import Path
import math
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts/unreal'))
from t1_battlefield_views import neighborhood_views,terrain_camera_sample


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

    def test_steep_terrain_can_be_a_focus_but_not_camera_footing(self):
        position=[100,200,300];normal=[.9,0,math.sqrt(1-.9**2)]
        self.assertEqual(terrain_camera_sample(position,normal,300,False),position)
        with self.assertRaises(ValueError):terrain_camera_sample(position,normal,300,True)
        self.assertEqual(terrain_camera_sample(position,[0,0,1],300,True),position)
    def test_camera_focus_requires_finite_matching_native_terrain(self):
        for position,normal,height in [([0,0,300],[0,0,1],302),([0,0,math.nan],[0,0,1],0),([0,0,0],[0,0,-1],0),([0,0,0],[0,0,2],0)]:
            with self.assertRaises(ValueError):terrain_camera_sample(position,normal,height,False)

if __name__=='__main__': unittest.main()
