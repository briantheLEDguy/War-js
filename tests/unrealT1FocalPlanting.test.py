import copy,math,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts/unreal'))
from t1_focal_planting import focal_layout

class FocalPlantingTests(unittest.TestCase):
 def fixture(self):
  outline=[dict(x=x,z=z) for x,z in [(-100,-100),(100,-100),(100,100),(-100,100)]]
  return dict(id='sunmeadow_march',spatial=dict(playableOutline=outline),paths=[dict(width=10,points=[dict(x=-100,z=0),dict(x=100,z=0)])],orvrLayout=dict(terrain=dict(flattenAreas=[])),npcs=[dict(x=10,z=15)])
 def test_deterministic_colonies_protect_roads_services_and_inputs(self):
  source=self.fixture();before=copy.deepcopy(source);patches=[(0,0,35)];out=focal_layout(source,lambda x,z:0,[],[],patches)
  self.assertEqual(out,focal_layout(source,lambda x,z:0,[],[],patches));self.assertEqual(source,before);self.assertGreater(sum(map(len,out.values())),100)
  for rows in out.values():
   for row in rows:
    z,x,y=row['location'];self.assertGreaterEqual(abs(z/100),6.5);self.assertGreaterEqual(math.hypot(x/100-10,z/100-15),10);self.assertEqual(y,0)
    self.assertGreaterEqual(row['scale'],.45);self.assertLessEqual(row['scale'],1.5)
 def test_existing_and_overlapping_patch_plants_have_full_spacing(self):
  source=self.fixture();first=focal_layout(source,lambda x,z:0,[],[],[(0,0,20)]);existing=[row for rows in first.values() for row in rows];before=copy.deepcopy(existing)
  second=focal_layout(source,lambda x,z:0,[],existing,[(0,0,25),(10,0,25)]);self.assertEqual(existing,before)
  added=[row for rows in second.values() for row in rows]
  self.assertGreater(len(added),0)
  for i,row in enumerate(added):
   for other in [*existing,*added[:i]]:self.assertGreaterEqual(math.dist(row['location'][:2],other['location'][:2]),60-1e-7)
 def test_water_steep_ground_and_military_pads_remain_clear(self):
  source=self.fixture();patches=[(0,0,20)]
  wet=[dict(x=0,z=0,radius=100,waterY=1,cosmeticWater=True,approach=[])]
  for height,pockets in [(lambda x,z:0,wet),(lambda x,z:x*50,[])]:self.assertEqual(sum(map(len,focal_layout(source,height,pockets,[],patches).values())),0)
  source['orvrLayout']['terrain']['flattenAreas']=[dict(id='objective',x=0,z=0,radius=100,preserveFooting=True)]
  self.assertEqual(sum(map(len,focal_layout(source,lambda x,z:0,[],[],patches).values())),0)
 def test_invalid_inventory_patch_or_ground_fails(self):
  source=self.fixture()
  for patches in [[],[(0,0,101)],[(0,math.inf,20)]]:
   with self.assertRaises(ValueError):focal_layout(source,lambda x,z:0,[],[],patches)
  with self.assertRaises(ValueError):focal_layout(source,lambda x,z:math.nan,[],[],[(0,0,20)])
  with self.assertRaises(ValueError):focal_layout(source,lambda x,z:0,[],[dict(location=[0,math.inf,0])],[(0,0,20)])
  with self.assertRaises(ValueError):focal_layout({**source,'id':'cinderfen_outskirts'},lambda x,z:0,[],[])

if __name__=='__main__':unittest.main()
