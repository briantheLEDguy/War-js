import copy
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts/unreal'))
from t1_relief import relief_recipe, relief_height, deformation_mask, deform_surface


class ReliefTest(unittest.TestCase):
    def test_regional_mass_is_distinct_and_substantial(self):
        sun=relief_recipe('sunmeadow_march'); cinder=relief_recipe('cinderfen_outskirts')
        self.assertGreater(relief_height(0,475,sun['features']),130)
        self.assertGreater(relief_height(80,410,cinder['features']),110)
        self.assertNotEqual(sun['features'],cinder['features'])
        self.assertFalse(sun['offRouteTraversalAccepted'])
        with self.assertRaises(ValueError): relief_recipe('brightfen_approach')

    def test_roads_anchors_scenery_and_approaches_stay_unchanged(self):
        recipe=relief_recipe('sunmeadow_march'); corridor=[([[-500,0],[500,0]],6)]
        for z in (0,9,25): self.assertEqual(deformation_mask(0,z,corridor,[],[],recipe),0)
        self.assertGreater(deformation_mask(0,90,corridor,[],[],recipe),0)
        self.assertEqual(deformation_mask(0,0,[],[dict(x=0,z=0,radius=95,feather=35)],[],recipe),0)
        self.assertEqual(deformation_mask(25,0,[],[],[[-20,20,-20,20]],recipe),0)
        self.assertGreater(deformation_mask(100,100,[],[],[[-20,20,-20,20]],recipe),0)

    def test_surface_rebuild_preserves_xy_topology_uvs_and_input(self):
        positions=[[z*100,x*100,0] for z in (450,475,500) for x in (-25,0,25)]
        indices=[]
        for z in range(2):
            for x in range(2):
                a=z*3+x; indices.extend([a,a+3,a+1,a+1,a+3,a+4])
        data=dict(zoneId='sunmeadow_march',positions=positions,indices=indices,normals=[[0,0,1]]*9,uvs=[[0,0]]*9)
        source=dict(id=data['zoneId'],paths=[],orvrLayout=dict(terrain=dict(flattenAreas=[])))
        before=copy.deepcopy(data); result,report=deform_surface(data,source,[],[])
        self.assertEqual(data,before); self.assertEqual(result['indices'],indices); self.assertEqual(result['uvs'],data['uvs'])
        self.assertEqual([p[:2] for p in result['positions']],[p[:2] for p in data['positions']])
        self.assertGreater(report['maximumAddedHeightMetres'],130)
        for normal in result['normals']:
            self.assertGreater(normal[2],0); self.assertAlmostEqual(sum(v*v for v in normal),1)
        masked,_=deform_surface(data,source,[[-50,50,400,550]],[])
        self.assertEqual(masked['positions'],data['positions'])
        clockwise={**data,'indices':[i for n in range(0,len(indices),3) for i in reversed(indices[n:n+3])]}
        reversed_mesh,_=deform_surface(clockwise,source,[],[])
        self.assertEqual(reversed_mesh['positions'],result['positions'])
        for a,b in zip(reversed_mesh['normals'],result['normals']):
            for x,y in zip(a,b): self.assertAlmostEqual(x,y)

    def test_nonfinite_or_mismatched_mesh_fails_closed(self):
        source=dict(id='sunmeadow_march',paths=[],orvrLayout=dict(terrain=dict(flattenAreas=[])))
        with self.assertRaises(ValueError): deform_surface(dict(zoneId='other',indices=[]),source,[],[])
        with self.assertRaises(ValueError): deform_surface(dict(zoneId=source['id'],indices=[],positions=[[0,float('nan'),0]]),source,[],[])


if __name__=='__main__': unittest.main()
