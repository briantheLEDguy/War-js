import copy,math,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts/unreal'))
from t1_rock_contact import rock_contact,bed_rock_body

class RockContactTests(unittest.TestCase):
 def fixture(self):
  points=[[0,0,-70]]+[[x,y,-40] for x in (-80,-30,30,80) for y in (-80,-30,30,80)]+[[x,y,70] for x in (-100,-30,30,100) for y in (-100,100)]
  mesh=dict(boundsOrigin=[0,0,0],boundsExtent=[100,100,70],positions=points)
  body=dict(location=[0,0,55],scale=1,yawDegrees=37,centreExposureCm=125,footprintCentre=[0,0])
  return body,mesh
 def test_perched_tip_gets_broad_contact_without_changing_horizontal_pose(self):
  body,mesh=self.fixture();before=copy.deepcopy((body,mesh));result=bed_rock_body(body,mesh,lambda x,z:0)
  self.assertEqual((body,mesh),before);self.assertEqual(result,bed_rock_body(body,mesh,lambda x,z:0));self.assertEqual(result['location'][:2],body['location'][:2]);self.assertEqual(result['yawDegrees'],37)
  self.assertEqual(result['burialDepthCm'],33);self.assertGreaterEqual(result['contact']['buriedFraction'],.08);self.assertEqual(result['contact']['contactQuadrants'],4)
 def test_already_supported_body_stays_put_and_duplicate_corners_do_not_bias_support(self):
  body,mesh=self.fixture();body['location'][2]=20;body['burialDepthCm']=50;body['centreExposureCm']=90
  first=bed_rock_body(body,mesh,lambda x,z:0);mesh['positions']*=4;second=bed_rock_body(body,mesh,lambda x,z:0)
  self.assertEqual(first,second);self.assertEqual(first['location'],body['location']);self.assertEqual(first['contact']['uniqueVertices'],25)
 def test_scaled_bedding_is_bounded_and_idempotent(self):
  body,mesh=self.fixture();mesh['positions']=[[x,y,z] for x in (-100,100) for y in (-100,100) for z in (-70,70)]
  result=bed_rock_body(body,mesh,lambda x,z:0);self.assertAlmostEqual(result['burialDepthCm'],25.2)
  self.assertEqual(result,bed_rock_body(result,mesh,lambda x,z:0))
 def test_exposure_and_burial_limits_reject_unsupported_body(self):
  body,mesh=self.fixture();body['centreExposureCm']=30;self.assertIsNone(bed_rock_body(body,mesh,lambda x,z:0))
  body['centreExposureCm']=125;body['location'][2]=500;self.assertIsNone(bed_rock_body(body,mesh,lambda x,z:0))
 def test_invalid_mesh_transforms_or_ground_fail(self):
  body,mesh=self.fixture()
  for positions in ([],[[0,0,0]]*5,[[math.nan,0,0]]*5):
   with self.assertRaises(ValueError):rock_contact(positions,[0,0,0],[0,0,0],1,0,lambda x,z:0)
  with self.assertRaises(ValueError):rock_contact(mesh['positions'],[0,0,0],[0,0,0],1,0,lambda x,z:math.nan)
  with self.assertRaises(ValueError):bed_rock_body(body,{k:v for k,v in mesh.items() if k!='positions'},lambda x,z:0)

if __name__=='__main__':unittest.main()
