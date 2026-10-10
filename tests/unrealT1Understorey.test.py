import copy,math,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts/unreal'))
from t1_understorey import understorey_layout,PLANTS,budget_understorey

class UnderstoreyTests(unittest.TestCase):
 def fixture(self):
  outline=[dict(x=x,z=z) for x,z in [(-100,-100),(100,-100),(100,100),(-100,100)]]
  source=dict(id='sunmeadow_march',spatial=dict(playableOutline=outline),paths=[dict(width=10,points=[dict(x=-100,z=0),dict(x=100,z=0)])],orvrLayout=dict(terrain=dict(flattenAreas=[])),npcs=[dict(x=50,z=50)])
  seeds=[dict(location=[z*100,x*100,0]) for x in range(-90,91,10) for z in range(-90,91,10)]
  return source,seeds,seeds[:100]
 def test_deterministic_colonies_retain_inputs_and_protect_routes_services(self):
  s,m,c=self.fixture();before=copy.deepcopy((s,m,c));r=understorey_layout(s,lambda x,z:0,[],m,c)
  self.assertEqual(r,understorey_layout(s,lambda x,z:0,[],m,c));self.assertEqual((s,m,c),before);self.assertEqual(set(r),set(PLANTS))
  self.assertGreater(sum(map(len,r.values())),100)
  for rows in r.values():
   for row in rows:
    z,x,y=row['location'];self.assertGreaterEqual(abs(z/100),6.5);self.assertGreaterEqual(math.hypot(x/100-50,z/100-50),10);self.assertEqual(y,0);self.assertGreaterEqual(row['scale'],.5);self.assertLessEqual(row['scale'],1.75)
 def test_submerged_steep_or_reserved_ground_receives_no_planting(self):
  s,m,c=self.fixture();water=[dict(x=0,z=0,radius=200,waterY=1,cosmeticWater=True,approach=[])]
  for height,pockets in [(lambda x,z:0,water),(lambda x,z:x*50,[])]:self.assertEqual(sum(map(len,understorey_layout(s,height,pockets,m,c).values())),0)
  s['orvrLayout']['terrain']['flattenAreas']=[dict(id='objective',x=0,z=0,radius=200,preserveFooting=True)]
  self.assertEqual(sum(map(len,understorey_layout(s,lambda x,z:0,[],m,c).values())),0)
 def test_budget_retains_species_ratios_and_is_independent_of_traversal_order(self):
  layout={name:[dict(location=[i*117.3,index*913.7,0],yaw=i,scale=1,shade=True) for i in range(count)] for index,(name,count) in enumerate(zip(PLANTS,[600,300,180,60]))};before=copy.deepcopy(layout)
  result,report=budget_understorey(layout,128)
  self.assertEqual(layout,before);self.assertEqual(sum(map(len,result.values())),128);self.assertEqual(report['thinned'],1012)
  reverse,_=budget_understorey({k:list(reversed(v)) for k,v in layout.items()},128)
  for name in PLANTS:
   self.assertEqual(sorted(r['location'] for r in result[name]),sorted(r['location'] for r in reverse[name]))
   self.assertLessEqual(abs(len(result[name])-len(layout[name])*128/1140),1)
  retained,_=budget_understorey(result,128);self.assertEqual(retained,result);retained[PLANTS[0]][0]['scale']=99;self.assertNotEqual(retained,result)
  for bad in [63,24001,True]:
   with self.assertRaises(ValueError):budget_understorey(layout,bad)
 def test_invalid_region_seeds_and_nonfinite_footing_fail(self):
  s,m,c=self.fixture()
  with self.assertRaises(ValueError):understorey_layout({**s,'id':'cinderfen_outskirts'},lambda x,z:0,[],m,c)
  with self.assertRaises(ValueError):understorey_layout(s,lambda x,z:math.nan,[],m,c)
  m[0]['location'][0]=math.inf
  with self.assertRaises(ValueError):understorey_layout(s,lambda x,z:0,[],m,c)

if __name__=='__main__':unittest.main()
