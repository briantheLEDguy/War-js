import copy,math,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts/unreal'))
from t1_meadow_patches import meadow_layout,meadow_weight

def source():
 return dict(id='sunmeadow_march',spatial=dict(playableOutline=[dict(x=-100,z=-100),dict(x=100,z=-100),dict(x=100,z=100),dict(x=-100,z=100)]),paths=[dict(id='road',width=12,points=[dict(x=-100,z=0),dict(x=100,z=0)])],orvrLayout=dict(terrain=dict(flattenAreas=[dict(x=0,z=20,radius=3,preserveFooting=True)]),keeps=[],battlefieldObjectives=[],stagingCamps=[]),resourceNodes=[dict(x=20,z=20)])
P=dict(id='meadow',x=0,z=0,radiusX=38,radiusZ=30,angle=.3,spacing=.7)
class MeadowTest(unittest.TestCase):
 def test_continuous_irregular_edges_and_bounded_density(self):
  self.assertEqual(meadow_weight(50,0,38,30,1,1),0)
  self.assertEqual(meadow_weight(0,0,38,30,.5,1),1)
  self.assertGreater(meadow_weight(30,0,38,30,1,1),meadow_weight(30,0,38,30,0,1))
  edge=38*.86
  self.assertLess(abs(meadow_weight(edge+.0001,0,38,30,.5,1)-meadow_weight(edge-.0001,0,38,30,.5,1)),1e-9)
  for args in [(0,0,0,30,.5,.5),(0,0,38,30,2,.5),(0,0,38,30,math.nan,.5)]:
   with self.assertRaises(ValueError):meadow_weight(*args)
 def test_native_centimetre_grounding_and_retained_reserves(self):
  s=source();before=copy.deepcopy(s);r=meadow_layout(s,lambda x,z:100+x*2,[P]);self.assertGreater(r['instances'],100)
  for p in r['rows']:
   self.assertGreaterEqual(abs(p['z']),7);self.assertGreaterEqual(math.hypot(p['x'],p['z']-20),7);self.assertGreaterEqual(math.hypot(p['x']-20,p['z']-20),12)
   self.assertAlmostEqual(p['y'],100+p['x']*2);self.assertAlmostEqual(p['grade'],.02);self.assertTrue(.8<=p['scale']<=1.15)
  self.assertEqual(s,before);self.assertFalse(r['nativeIntegrated'] or r['performanceAccepted'] or r['combatCoverAccepted'])
  narrow=meadow_layout(s,lambda x,z:100,[P],{'road':4});self.assertGreater(narrow['instances'],r['instances']);self.assertEqual(s['paths'][0]['width'],12)
 def test_determinism_order_independence_and_slope_rejection(self):
  s=source();patches=[P,{**P,'id':'second','x':45}];a=meadow_layout(s,lambda x,z:100,patches);self.assertEqual(a,meadow_layout(s,lambda x,z:100,list(reversed(patches))))
  self.assertNotEqual(a['rows'],meadow_layout(s,lambda x,z:100,[{**P,'id':'changed'}])['rows'])
  self.assertEqual(meadow_layout(s,lambda x,z:x*40,[P])['instances'],0)
  for height in [lambda x,z:math.nan,lambda x,z:35001]:
   with self.assertRaises(ValueError):meadow_layout(s,height,[P])
 def test_invalid_recipes_widths_and_finite_work_budgets(self):
  for p in [{**P,'spacing':.1},{**P,'radiusX':101},{**P,'x':True}]:
   with self.assertRaises(ValueError):meadow_layout(source(),lambda x,z:0,[p])
  with self.assertRaises(ValueError):meadow_layout(source(),lambda x,z:0,[P,P])
  with self.assertRaises(ValueError):meadow_layout(source(),lambda x,z:0,[{**P,'radiusX':100,'radiusZ':100,'spacing':.3}])
  with self.assertRaises(ValueError):meadow_layout(source(),lambda x,z:0,[P],limit=1)
  for widths in [[],{'missing':4},{'road':14},{'road':math.nan}]:
   with self.assertRaises(ValueError):meadow_layout(source(),lambda x,z:0,[P],widths)
if __name__=='__main__':unittest.main()
