import copy,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts/unreal'))
from t1_distant_scenery import qualify_distant_skirt

class DistantSkirtTests(unittest.TestCase):
 def fixture(self):
  source=dict(spatial=dict(bounds=dict(minX=-100,maxX=100,minZ=-100,maxZ=100),terrainBounds=dict(minX=0,maxX=20,minZ=0,maxZ=10)))
  terrain=dict(positions=[[0,0,0],[0,2000,100],[1000,0,50],[1000,2000,150]],normals=[[0,0,1]]*4)
  p=[];indices=[]
  for a,b,offset in [(0,1,[-1000,0,0]),(2,3,[1000,0,0]),(0,2,[0,-1000,0]),(1,3,[0,1000,0])]:
   start=len(p);p.extend([terrain['positions'][a][:],terrain['positions'][b][:],[v+d for v,d in zip(terrain['positions'][a],offset)],[v+d for v,d in zip(terrain['positions'][b],offset)]])
   for tri in [[0,1,2],[2,1,3]]:
    a,b,c=[p[start+j] for j in tri]
    if (b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0])>0:tri[1],tri[2]=tri[2],tri[1]
    indices.extend(start+j for j in tri)
  return source,terrain,dict(positions=p,normals=[[0,0,1] for _ in p],uvs=[[0,0] for _ in p],indices=indices)
 def test_exact_boundary_and_exterior_triangles_are_measured_without_mutation(self):
  s,t,m=self.fixture();before=copy.deepcopy(m);r=qualify_distant_skirt(s,t,m)
  self.assertEqual(r['boundaryVertices'],4);self.assertEqual(r['maximumBoundaryHeightErrorCm'],0);self.assertTrue(r['trianglesOutsideSampling']);self.assertEqual(m,before)
 def test_mismatched_seams_escaped_bounds_and_playable_crossings_fail(self):
  for kind in ['height','normal','bounds','crossing','winding']:
   s,t,m=self.fixture()
   if kind=='height':m['positions'][0][2]+=1
   if kind=='normal':m['normals'][0]=[1,0,0]
   if kind=='bounds':m['positions'][2][0]=-20000
   if kind=='crossing':m['indices'][:3]=[0,1,5]
   if kind=='winding':m['indices'][0],m['indices'][1]=m['indices'][1],m['indices'][0]
   with self.assertRaises(ValueError,msg=kind):qualify_distant_skirt(s,t,m)

if __name__=='__main__':unittest.main()
