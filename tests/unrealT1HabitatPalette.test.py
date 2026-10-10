import math,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts/unreal'))
from t1_habitat_palette import habitat_weights,installed_rock_palette
class HabitatPaletteTests(unittest.TestCase):
 def test_forest_shelter_remains_independent_of_dry_patch_noise(self):
  for coarse in (0,.5,1):
   for fine in (0,.5,1):
    w=habitat_weights(1,coarse,fine,.5);self.assertEqual(w['forest'],.92);self.assertEqual(w['regional'],0)
 def test_open_ground_has_soft_bounded_nonuniform_colour(self):
  last=-1
  for i in range(1001):
   v=i/1000;w=habitat_weights(0,v,v,v);self.assertGreaterEqual(w['forest'],last);self.assertLessEqual(w['forest'],.75);self.assertLessEqual(abs(w['forest']-last),.003 if last>=0 else 2);last=w['forest']
   self.assertGreaterEqual(w['macro'],.68);self.assertLessEqual(w['macro'],1.08);self.assertEqual(w['regional'],.22)
  self.assertEqual(habitat_weights(0,0,0,0)['forest'],0);self.assertEqual(habitat_weights(0,1,1,1)['forest'],.75)
 def test_basalt_scales_source_tint_without_changing_alpha_or_sunmeadow(self):
  tint=[.53125,.711954,1,.8];r=installed_rock_palette('cinderfen_outskirts',tint)
  self.assertAlmostEqual(r['tint'][0],.1859375,12);self.assertEqual(r['tint'][1:],[.711954*.35,.35,.8]);self.assertEqual(r['desaturation'],.35);self.assertEqual(tint,[.53125,.711954,1,.8])
  self.assertEqual(installed_rock_palette('sunmeadow_march',tint)['tint'],tint)
 def test_invalid_samples_or_unadmitted_regions_fail(self):
  for bad in (math.inf,math.nan,-.1,1.1):
   with self.assertRaises(ValueError):habitat_weights(0,bad,.5,.5)
  for region,tint in [('brightfen_approach',[1,1,1,1]),('cinderfen_outskirts',[1,math.nan,1,1]),('sunmeadow_march',[1,1,1])]:
   with self.assertRaises(ValueError):installed_rock_palette(region,tint)
if __name__=='__main__':unittest.main()
