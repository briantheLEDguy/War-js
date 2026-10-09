import math,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts/unreal'))
from t1_nature_canopy import canopy_transform,canopy_identities,MAPPING

class NatureCanopyTests(unittest.TestCase):
 def test_retains_original_height_and_bottom_with_off_centre_roots(self):
  source=[[20,-40,600],[400,500,700]];target=[[40,80,450],[500,550,500]]
  r=canopy_transform(source,target,[1.2,1.2,1.5],[1200,2300,400],[0,71,0])
  for value in r['scale']:self.assertAlmostEqual(value,2.1)
  self.assertEqual(r['retainedHeightCm'],2100);self.assertEqual(r['retainedBottomCm'],250)
  self.assertAlmostEqual(r['location'][2]+(450-500)*2.1,250);self.assertEqual(r['location'][:2],[1200,2300])
 def test_upright_geometry_positive_bounds_and_bounded_scale_are_required(self):
  b=[[0,0,500],[100,100,500]]
  for scale,rotation in [([1,1,0],[0,0,0]),([1,1,1],[1,0,0]),([1,1,5],[0,0,0])]:
   with self.assertRaises(ValueError):canopy_transform(b,b,scale,[0,0,0],rotation)
 def test_nonfinite_or_unbounded_placement_fails(self):
  b=[[0,0,500],[100,100,500]]
  for location in [[0,0,math.nan],[400000,0,0]]:
   with self.assertRaises(ValueError):canopy_transform(b,b,[1,1,1],location,[0,0,0])

 def test_canopy_inventory_uses_exact_revision_identities_without_mutating_sources(self):
  import copy
  names=list(MAPPING);states={str(i):dict(kind='mesh',mesh='/Game/Source/'+names[i%3]+'.'+names[i%3]) for i in range(203)}
  states['lamp']=dict(kind='light');states['rock']=dict(kind='mesh',mesh='/Game/Source/Rock.Rock');before=copy.deepcopy(states)
  self.assertEqual(canopy_identities(states),tuple(sorted(str(i) for i in range(203))));self.assertEqual(states,before)
 def test_missing_or_excessive_canopy_inventories_fail(self):
  name=next(iter(MAPPING));state=dict(kind='mesh',mesh='/Game/Source/'+name+'.'+name)
  for count in [0,199,501]:
   with self.assertRaises(ValueError):canopy_identities({str(i):state for i in range(count)})

if __name__=='__main__':unittest.main()
