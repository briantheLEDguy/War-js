import sys
import unittest
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts/unreal'))
from world_landscapes import surface_kind, validate_chunk_coverage


class LandscapeTests(unittest.TestCase):
    def test_rectangular_variable_tile_coverage(self):
        definition={'size':300,'spatial':{'bounds':{'minX':-150,'maxX':150,'minZ':-50,'maxZ':50}},
            'orvrLayout':{'terrain':{'chunks':[{'id':str(i),'x':-100+i*100,'z':0,'width':100,'depth':100} for i in range(3)]}}}
        self.assertEqual(len(validate_chunk_coverage(definition)),3)
        definition['orvrLayout']['terrain']['chunks'].pop()
        with self.assertRaises(ValueError): validate_chunk_coverage(definition)

    def test_overlapping_tiles_are_not_complete_coverage(self):
        definition={'size':100,'orvrLayout':{'terrain':{'chunks':[
            {'id':str(i),'x':0,'z':0,'width':100,'depth':100} for i in range(2)]}}}
        with self.assertRaises(ValueError): validate_chunk_coverage(definition)

    def test_fractional_tile_thirds_share_complete_edges(self):
        definition={'size':1700,'spatial':{'bounds':{'minX':-850,'maxX':850,'minZ':-650,'maxZ':650}},
            'orvrLayout':{'terrain':{'chunks':[
                {'id':f'{x}_{z}','x':-850+(x+.5)*1700/4,'z':-650+(z+.5)*1300/3,
                 'width':1700/4,'depth':1300/3} for z in range(3) for x in range(4)]}}}
        self.assertEqual(len(validate_chunk_coverage(definition)),12)
        definition['orvrLayout']['terrain']['chunks'][0]['depth']-=.01
        with self.assertRaises(ValueError):validate_chunk_coverage(definition)

    def test_only_authored_land_receives_ground_collision(self):
        self.assertEqual(surface_kind({'name':'tile_surface_LOD0'}),'ground')
        self.assertEqual(surface_kind({'name':'tile_roads'}),'road')
        self.assertEqual(surface_kind({'name':'tile_peat_water','extras':{'noGroundSupport':True}}),'water')
        with self.assertRaises(ValueError): surface_kind({'name':'unreviewed_surface'})
        with self.assertRaises(ValueError): surface_kind({'name':'tile_peat_water','extras':{'noGroundSupport':False}})


if __name__=='__main__': unittest.main()
