import math,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts/unreal'))
from t1_habitat_surface import habitat_recipe,validate_habitat,habitat_masks,habitat_shore_band

class HabitatTests(unittest.TestCase):
    def test_negative_grid_edges_are_continuous_bounded_and_regionally_distinct(self):
        for identity in ['sunmeadow_march','cinderfen_outskirts']:
            for i in range(-150,151):
                x=i*3.17;z=i*-.71;a=habitat_masks(x,z,identity);b=habitat_masks(x+.0001,z-.0001,identity)
                self.assertTrue(all(0<=v<=1 for v in a));self.assertLess(max(abs(u-v) for u,v in zip(a,b)),.0001)
                self.assertEqual(a,habitat_masks(x,z,identity))
        self.assertNotEqual(habitat_masks(10,20,'sunmeadow_march'),habitat_masks(10,20,'cinderfen_outskirts'))
    def test_moisture_fades_without_steps_and_stays_local_to_water_height(self):
        for moisture in [0,.25,.5,.75,1]:
            self.assertEqual(habitat_shore_band(-1,moisture,'sunmeadow_march'),1)
            self.assertEqual(habitat_shore_band(1.61,moisture,'sunmeadow_march'),0)
            for i in range(161):
                y=i/100;a=habitat_shore_band(y,moisture,'sunmeadow_march');b=habitat_shore_band(y+.0001,moisture,'sunmeadow_march')
                self.assertGreaterEqual(a,b);self.assertLess(a-b,.0003)
        self.assertLess(habitat_shore_band(.8,0,'sunmeadow_march'),habitat_shore_band(.8,1,'sunmeadow_march'))
    def test_unreviewed_or_nonfinite_inputs_fail_and_recipe_is_fresh(self):
        r=habitat_recipe('sunmeadow_march');r['seed']=0
        with self.assertRaises(ValueError):validate_habitat(r)
        validate_habitat(habitat_recipe('sunmeadow_march'))
        for x in [math.inf,math.nan,5001]:
            with self.assertRaises(ValueError):habitat_masks(x,0,'sunmeadow_march')
        with self.assertRaises(ValueError):habitat_masks(0,0,'brightfen_approach')
        with self.assertRaises(ValueError):habitat_shore_band(0,2,'sunmeadow_march')

if __name__=='__main__':unittest.main()
