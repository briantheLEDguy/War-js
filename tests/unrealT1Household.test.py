import copy
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts/unreal'))
from t1_household import household_recipe, BED_PARTS, ROLES

class HouseholdTests(unittest.TestCase):
    def setUp(self):
        self.catalog = {name:dict(origin=[0,0,55],extent=[66,121,55]) for name in BED_PARTS}
        self.catalog['SM_Bed_Matress']=dict(origin=[0,-1,47],extent=[57,113,15])
        self.catalog['SM_Bed_Pillow']=dict(origin=[0,-77,67],extent=[52,31,10])
        self.catalog['SM_Bed_Sheet']=dict(origin=[2,33,36],extent=[89,75,38])
        self.catalog.update(SM_Table_Round=dict(origin=[0,0,40],extent=[68,68,40]),
            SM_Bench_2=dict(origin=[0,0,22],extent=[160,24,22]),
            SM_Crate_2=dict(origin=[0,0,16],extent=[30,20,16]))

    def test_all_roles_fit_smallest_admitted_room_and_keep_central_aisle(self):
        before=copy.deepcopy(self.catalog)
        for role in ROLES:
            recipe=household_recipe(role,500,300,self.catalog)
            for row in recipe['placements']:
                x0,x1,y0,y1=row['footprintCm']
                self.assertTrue(x1<=-75 or x0>=75)
                self.assertGreaterEqual(y0,-300);self.assertLessEqual(y1,300)
            self.assertFalse(recipe['nativeFloorAndCollisionAccepted'])
        self.assertEqual(before,self.catalog)

    def test_bed_components_keep_common_pivot_and_only_frame_requires_collision(self):
        rows=[p for p in household_recipe('carter',560,460,self.catalog)['placements'] if p['group']=='west_bed']
        self.assertEqual(len(rows),4)
        self.assertEqual([p['localPositionCm'] for p in rows],[[-330,-240,0]]*4)
        self.assertEqual([p['collisionRequired'] for p in rows],[True,False,False,False])

    def test_rejects_furniture_overlap_between_separate_groups(self):
        self.catalog['SM_Table_Round']['extent']=[100,300,40]
        with self.assertRaisesRegex(ValueError,'Separate household'):household_recipe('carter',560,600,self.catalog)

    def test_native_support_fit_moves_complete_bed_groups_and_preserves_aisles(self):
        def supports(row):
            return row['group']!='west_bed' or row['footprintCm'][2]>=-300
        recipe=household_recipe('carter',560,460,self.catalog,supports)
        self.assertTrue(recipe['nativeSupportSamplerUsed'])
        beds=[p for p in recipe['placements'] if p['group']=='west_bed']
        self.assertEqual(len({tuple(p['localPositionCm']) for p in beds}),1)
        self.assertTrue(all(supports(p) for p in recipe['placements']))
        for row in recipe['placements']:
            x0,x1,_,_=row['footprintCm'];self.assertTrue(x1<=-75 or x0>=75)
        self.assertFalse(recipe['nativeFloorAndCollisionAccepted'])

    def test_long_bench_can_turn_on_supported_floor_without_rotating_beds(self):
        def supports(row):
            return row['asset'] != 'SM_Bench_2' or row['localYawDegrees'] == 90
        recipe=household_recipe('carter',560,460,self.catalog,supports)
        bench=next(p for p in recipe['placements'] if p['asset']=='SM_Bench_2')
        x0,x1,y0,y1=bench['footprintCm']
        self.assertEqual(bench['localYawDegrees'],90)
        self.assertEqual(x1-x0,48);self.assertEqual(y1-y0,320)
        self.assertTrue(all(p['localYawDegrees']==0 for p in recipe['placements'] if p['asset'] in BED_PARTS))
        self.assertTrue(x1<=-75 or x0>=75)
        self.assertFalse(recipe['nativeFloorAndCollisionAccepted'])

    def test_unsatisfiable_native_support_is_bounded_and_does_not_mutate_catalog(self):
        before=copy.deepcopy(self.catalog);calls=[]
        def unsupported(row):calls.append(row);return False
        with self.assertRaisesRegex(ValueError,'No bounded supported'):
            household_recipe('carter',560,460,self.catalog,unsupported)
        self.assertLessEqual(len(calls),169);self.assertEqual(self.catalog,before)
        with self.assertRaises(ValueError):household_recipe('carter',560,460,self.catalog,False)

    def test_rejects_missing_assets_and_room_or_aisle_overflow(self):
        for name in ['SM_Bed_Pillow','SM_Table_Round']:
            catalog=copy.deepcopy(self.catalog);del catalog[name]
            with self.assertRaises(ValueError):household_recipe('field_workers',500,300,catalog)
        for extent in ([400,121,55],[66,700,55],[True,121,55],[0,121,55]):
            catalog=copy.deepcopy(self.catalog);catalog['SM_Bed_2']['extent']=extent
            with self.assertRaises(ValueError):household_recipe('field_workers',500,300,catalog)
        for role,w,d in [('unknown',500,300),('carter',False,300),('carter',500,float('nan')),('carter',499,300)]:
            with self.assertRaises(ValueError):household_recipe(role,w,d,self.catalog)

if __name__=='__main__':unittest.main()
