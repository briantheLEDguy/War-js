"""Continuous highland refinement and preservation of measured low terrain."""
import copy
import math
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts/unreal'))
from aegis_citadel_alpine_relief import refine_native_highland,SPEC


def document(faces):
    return dict(schemaVersion=1,readOnly=True,available=True,valid=True,lod=0,invalidValues=0,
        mesh='/Game/WorldRebuild/MeasuredMountain.MeasuredMountain',
        policy='actual_render_index_order_oriented_triangle_corners',triangles=[dict(index=i,
            positions=face,normals=[[0,0,-1]]*3,uvChannels=[[[0,0],[1,0],[0,1]]],materialIndex=0)
            for i,face in enumerate(faces)])


class AlpineReliefTests(unittest.TestCase):
    def test_low_terrain_is_verbatim_and_input_is_immutable(self):
        original=document([[[0,0,6000],[1000,0,6500],[0,1000,6100]]]);before=copy.deepcopy(original)
        mesh,receipt=refine_native_highland(original)
        self.assertEqual(original,before)
        self.assertEqual(mesh['positions'],original['triangles'][0]['positions'])
        self.assertEqual(mesh['normals'],original['triangles'][0]['normals'])
        self.assertEqual(mesh['uvs'],original['triangles'][0]['uvChannels'][0])
        self.assertEqual(mesh['indices'],[0,1,2])
        self.assertEqual(receipt['maximumActualRiseCm'],0)
        self.assertFalse(receipt['collisionChanged'])

    def test_shared_high_edges_remain_identical_after_refinement(self):
        a,b,c,d=[0,0,23000],[1000,0,23000],[0,1000,23000],[1000,1000,23000]
        mesh,receipt=refine_native_highland(document([[a,b,c],[b,d,c]]))
        count=(SPEC['subdivisions']+1)*(SPEC['subdivisions']+2)//2
        left={tuple(p) for p in mesh['positions'][:count] if p[0]+p[1]==1000}
        right={tuple(p) for p in mesh['positions'][count:] if p[0]+p[1]==1000}
        self.assertEqual(left,right);self.assertEqual(len(left),SPEC['subdivisions']+1)
        self.assertEqual(receipt['outputTriangles'],2*SPEC['subdivisions']**2)
        self.assertGreater(receipt['maximumActualRiseCm'],0)
        self.assertLessEqual(receipt['maximumActualRiseCm'],SPEC['maximumRiseCm'])
        self.assertTrue(all(abs(sum(v*v for v in n)-1)<1e-6 and n[2]<0 for n in mesh['normals']))

    def test_refinement_fades_out_at_low_boundary(self):
        mesh,_=refine_native_highland(document([[[0,0,16000],[800,0,16000],[0,800,24000]]]))
        edge=[p for p in mesh['positions'] if p[1]==0]
        self.assertTrue(all(p[2]==16000 for p in edge))

    def test_missing_or_nonfinite_native_evidence_is_rejected(self):
        base=document([[[0,0,24000],[1000,0,24000],[0,1000,24000]]])
        mutations=[lambda d:d.update(readOnly=False),lambda d:d['triangles'][0]['positions'][0].__setitem__(2,math.nan),
            lambda d:d['triangles'][0].update(materialIndex=1),lambda d:d['triangles'].append(copy.deepcopy(d['triangles'][0]))]
        for mutate in mutations:
            value=copy.deepcopy(base);mutate(value)
            with self.assertRaises(ValueError):refine_native_highland(value)


if __name__=='__main__':unittest.main()
