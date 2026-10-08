import copy
from pathlib import Path
import sys
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts/unreal'))
from t1_home_ceiling import ceiling_recipe, validate_ceiling_witnesses, TIMBER

WALL = '/Game/Medieval_Environment/Meshes/SM_MH_02_Stone_Wall_01.SM_MH_02_Stone_Wall_01'
FLOOR = '/Game/Medieval_Environment/Meshes/SM_MH_02_Stone_Floor_01.SM_MH_02_Stone_Floor_01'


class HomeCeilingTest(unittest.TestCase):
    def setUp(self):
        self.template = dict(kind='home', interior=True, upperFloor=False, roomSize=[600, 900], components=[
            dict(mesh=WALL, anchor=[0,0,10], scale=[1,1,1], role='wall'),
            dict(mesh=FLOOR, anchor=[0,0,0], scale=[1,1,1], role='floor')])
        self.bounds = {WALL: dict(origin=[150,5,150], extent=[150,23,150]),
                       FLOOR: dict(origin=[150,-150,5], extent=[150,150,5])}
        self.timber = dict(origin=[150,-150,-2.4], extent=[150,150,12.6])

    def recipe(self, zone='sunmeadow_march'):
        return ceiling_recipe(self.template, self.bounds, self.timber, zone)

    def test_inverted_planks_tile_the_room_and_preserve_parent(self):
        original = copy.deepcopy(self.template); recipe = self.recipe()
        self.assertEqual(self.template, original)
        self.assertEqual(len(recipe['panels']), 6)
        centres = []
        for p in recipe['panels']:
            self.assertEqual(p['mesh'], TIMBER); self.assertEqual(p['rotation'], [180,0,0])
            centres.append([p['location'][0]-150, p['location'][1]-150])
            # Inverted high/low source bounds become the measured underside/top.
            self.assertAlmostEqual(p['location'][2]-10.2, recipe['bottomZ'])
            self.assertAlmostEqual(p['location'][2]+15, recipe['topZ'])
        self.assertEqual(centres, [[-150,-300],[-150,0],[-150,300],[150,-300],[150,0],[150,300]])
        self.assertAlmostEqual(recipe['minimumHeadroomCm'], 274.8)

    def test_large_room_and_regional_tints_are_explicit(self):
        self.template['roomSize'] = [900,900]
        self.assertEqual(len(self.recipe()['panels']), 9)
        self.assertEqual(len(self.recipe()['probes']), 36)
        self.assertNotEqual(self.recipe()['tint'], self.recipe('cinderfen_outskirts')['tint'])
        fill=self.recipe()['fill']
        self.assertLess(fill['position'][2]+fill['sourceRadiusCm'],self.recipe()['bottomZ'])
        self.assertFalse(fill['castShadows'])
        self.assertLess(fill['nightLumens'],fill['dayLumens'])
        self.assertLessEqual(fill['dayLumens'],5000)
        self.assertFalse(self.recipe()['visualApproved'])

    def test_unmeasured_geometry_or_insufficient_clearance_fails(self):
        for size in ([700,900], [1200,900], [float('nan'),900]):
            with self.assertRaises(ValueError): ceiling_recipe({**self.template,'roomSize':size},self.bounds,self.timber,'sunmeadow_march')
        for extent in ([151,150,12.6], [150,150,35], [150,150,float('nan')]):
            with self.assertRaises(ValueError): ceiling_recipe(self.template,self.bounds,{**self.timber,'extent':extent},'sunmeadow_march')
        self.bounds[WALL]['extent'][2] = 130
        with self.assertRaises(ValueError): self.recipe()

    def test_other_batches_upper_floors_and_duplicate_installation_fail(self):
        with self.assertRaises(ValueError): self.recipe('brightfen_approach')
        for field,value in [('upperFloor',True),('kind','shop'),('ceiling',{'existing':True})]:
            with self.assertRaises(ValueError): ceiling_recipe({**self.template,field:value},self.bounds,self.timber,'sunmeadow_march')

    def test_all_upward_witnesses_must_hit_the_ceiling_in_order(self):
        recipe = self.recipe()
        rows = [dict(probe=p,blockedByCeiling=True,localHeight=recipe['bottomZ']+10) for p in recipe['probes']]
        validate_ceiling_witnesses(recipe,rows)
        for changed in (rows[:-1],list(reversed(rows)),[{**rows[0],'blockedByCeiling':False}]+rows[1:],
                        [{**rows[0],'localHeight':recipe['topZ']+1}]+rows[1:]):
            with self.assertRaises(ValueError): validate_ceiling_witnesses(recipe,changed)


if __name__ == '__main__': unittest.main()
