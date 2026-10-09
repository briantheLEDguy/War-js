import copy,math,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts/unreal'))
from t1_rock_clusters import rock_clusters,NAMES

class RockClusterTests(unittest.TestCase):
 def fixture(self,yaw=37):
  parents=[dict(id='ridge',x=20,z=-30,width=30,depth=7,height=5,yawDegrees=yaw)]
  meshes={name:dict(boundsOrigin=[13,-7,11],boundsExtent=[150,90,70],positions=[[13+x,-7+y,11+z] for x in (-150,150) for y in (-90,90) for z in (-70,70)]) for name in NAMES}
  return parents,meshes
 def test_rotated_clusters_fit_parent_reserve_and_preserve_inputs(self):
  for yaw in (0,37,90,-167,327):
   parents,meshes=self.fixture(yaw);before=copy.deepcopy((parents,meshes));result=rock_clusters(parents,meshes,lambda x,z:100)
   self.assertEqual(result,rock_clusters(parents,meshes,lambda x,z:100));self.assertEqual((parents,meshes),before)
   self.assertEqual(result['replacedIds'],['ridge']);self.assertEqual(len(result['bodies']),4)
   for body in result['bodies']:
    dx,dz=body['footprintCentre'][0]-20,body['footprintCentre'][1]+30;t=math.radians(-yaw)
    along=dx*math.cos(t)+dz*math.sin(t);across=-dx*math.sin(t)+dz*math.cos(t)
    self.assertLessEqual(abs(along)+body['parentProjectedWidth']/2,15)
    self.assertLessEqual(abs(across)+body['parentProjectedDepth']/2,3.5)
 def test_nonzero_mesh_origin_and_footing_match_full_rotated_bounds(self):
  parents,meshes=self.fixture();height=lambda x,z:100+x*3+z*2
  for body in rock_clusters(parents,meshes,height)['bodies']:
   origin=meshes[body['meshName']]['boundsOrigin'];extent=meshes[body['meshName']]['boundsExtent'];angle=math.radians(body['yawDegrees']);scale=body['scale'];p=body['location']
   self.assertAlmostEqual(p[0]+(math.cos(angle)*origin[0]-math.sin(angle)*origin[1])*scale,body['footprintCentre'][1]*100)
   self.assertAlmostEqual(p[1]+(math.sin(angle)*origin[0]+math.cos(angle)*origin[1])*scale,body['footprintCentre'][0]*100)
   heading=math.radians(90-body['yawDegrees']);x,z=body['footprintCentre'];w,d=body['footprintWidth'],body['footprintDepth']
   samples=[height(x+math.cos(heading)*w*u/4-math.sin(heading)*d*v/4,z+math.sin(heading)*w*u/4+math.cos(heading)*d*v/4) for u in range(-2,3) for v in range(-2,3)]
   self.assertAlmostEqual(p[2]+(origin[2]-extent[2])*scale,min(samples)-body['burialDepthCm'])
   self.assertGreaterEqual(body['centreExposureCm'],extent[2]*2*scale*.2)
 def test_buried_or_unscalable_bodies_retain_original_parent(self):
  parents,meshes=self.fixture();result=rock_clusters(parents,meshes,lambda x,z:abs(x-20)*10000)
  self.assertEqual(result['bodies'],[]);self.assertEqual(result['retainedIds'],['ridge'])
  parents[0].update(width=.1,depth=.1,height=.1)
  self.assertEqual(rock_clusters(parents,meshes,lambda x,z:0)['retainedIds'],['ridge'])
 def test_invalid_inventories_and_nonfinite_ground_fail_closed(self):
  parents,meshes=self.fixture()
  for p in ([parents[0],parents[0]],[{**parents[0],'width':101}],[{**parents[0],'yawDegrees':math.nan}],[{**parents[0],'id':''}]):
   with self.assertRaises(ValueError):rock_clusters(p,meshes,lambda x,z:0)
  for extent in ([0,1,1],[1,1],[1,math.inf,1]):
   bad=copy.deepcopy(meshes);bad[NAMES[0]]['boundsExtent']=extent
   with self.assertRaises(ValueError):rock_clusters(parents,bad,lambda x,z:0)
  with self.assertRaises(ValueError):rock_clusters(parents,meshes,lambda x,z:math.nan)

if __name__=='__main__':unittest.main()
