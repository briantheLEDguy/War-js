import math
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts/unreal'))
from t1_water_surface import water_surface,ripple_normal

class WaterSurfaceTests(unittest.TestCase):
    def test_oblique_cosmetic_slopes_stay_gentle_across_time_and_source_variation(self):
        recipe=water_surface('cinderfen_outskirts')
        for wave in recipe['waves']:
            self.assertGreater(abs(math.sin(wave['angle'])*math.cos(wave['angle'])),.1)
        for i in range(250):
            n=ripple_normal(i*.37,i*-.61,i*.71,(i%13)/12,recipe)
            self.assertAlmostEqual(sum(v*v for v in n),1)
            self.assertLess(math.hypot(*n[:2]),.054)
            self.assertGreater(n[2],.998)
        a=ripple_normal(13,27,3,.4,recipe);b=ripple_normal(13,27,3,.8,recipe)
        self.assertNotEqual(a,b)
        c=ripple_normal(13.001,27.001,3.001,.40001,recipe)
        self.assertLess(max(abs(x-y) for x,y in zip(a,c)),.0001)

    def test_regional_recipe_is_fresh_and_rejects_nonfinite_input(self):
        sun=water_surface('sunmeadow_march');cinder=water_surface('cinderfen_outskirts')
        self.assertNotEqual(sun['absorption'],cinder['absorption'])
        self.assertLess(max(cinder['absorption'])/min(cinder['absorption']),3)
        sun['waves'][0]['slope']=1
        self.assertEqual(water_surface('sunmeadow_march')['waves'][0]['slope'],.023)
        for noise in (-1,2,math.nan):
            with self.assertRaises(ValueError):ripple_normal(0,0,0,noise,cinder)
        with self.assertRaises(ValueError):water_surface('unreviewed_zone')
        with self.assertRaises(ValueError):ripple_normal(math.inf,0,0,0,cinder)

if __name__=='__main__':unittest.main()
