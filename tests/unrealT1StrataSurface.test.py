import math,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts/unreal'))
from t1_strata_surface import strata_recipe,validate_strata,strata_sample
class StrataTests(unittest.TestCase):
    def test_layers_are_continuous_bounded_and_regionally_distinct(self):
        for identity in ('sunmeadow_march','cinderfen_outskirts'):
            r=strata_recipe(identity)
            for i in range(-100,101):
                h=i*.13;a=strata_sample(h,.42,0,r);b=strata_sample(h+.00001,.420001,0,r)
                self.assertTrue(1-r['contrast']<=a[0]<=1);self.assertLessEqual(abs(a[1]),r['bumpHeightCm']);self.assertLess(math.dist(a,b),.0003)
        self.assertNotEqual(strata_recipe('sunmeadow_march'),strata_recipe('cinderfen_outskirts'))
    def test_subpixel_layers_fade_to_constant_colour_and_zero_bump(self):
        r=strata_recipe('sunmeadow_march');expected=[1-r['contrast']*.5,0]
        for h in [-50,0,19,100]:self.assertEqual(strata_sample(h,.7,.46,r),expected)
        for i in range(46):
            f=i/100;a=strata_sample(1,.5,f,r);b=strata_sample(1,.5,f+.00001,r);self.assertLess(math.dist(a,b),.001)
    def test_unreviewed_and_nonfinite_controls_fail(self):
        r=strata_recipe('sunmeadow_march');validate_strata(r)
        with self.assertRaises(ValueError):validate_strata({**r,'bumpHeightCm':100})
        for h,n,f in [(math.nan,0,0),(0,2,0),(0,0,-1)]:
            with self.assertRaises(ValueError):strata_sample(h,n,f,r)
        with self.assertRaises(ValueError):strata_recipe('brightfen_approach')
if __name__=='__main__':unittest.main()
