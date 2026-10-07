"""CPU proposal geometry controls; these tests confer no native or visual acceptance."""
import copy
import json
import math
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT=next(p for p in Path(__file__).resolve().parents if (p/'package.json').exists())
sys.path[:0]=[str(Path(__file__).resolve().parents[1]/'scripts/unreal'),str(ROOT/'scripts/unreal')]
import aegis_citadel_mountain_fidelity as study

TRANSFORM=dict(translationCm=[25000,0,0],rotationQuaternion=[0,0,0,1],scale=[1,1,1])
BOUNDS=[[13500,-9600,2400],[34500,9600,24000]]

def document(faces):
    return dict(schemaVersion=1,readOnly=True,available=True,valid=True,lod=0,invalidValues=0,
        mesh='/Game/Owned/Saved.Saved',policy='actual_render_index_order_oriented_triangle_corners',
        triangles=[dict(index=i,materialIndex=0,positions=face,normals=[[0,0,-1] for unused in range(3)],
            uvChannels=[[[0,0],[1,0],[0,1]],[[.2,.1],[.7,.1],[.2,.8]]]) for i,face in enumerate(faces)])

class FidelityTests(unittest.TestCase):
    def test_normal_seams_repair_only_displaced_corners_without_reversing_faces(self):
        mesh=dict(positions=[[0,0,0],[1,0,0],[0,1,0]],normals=[[0,0,-1],[0,0,1],[0,0,1]],
            indices=[0,1,2],uvChannels=[[[0,0],[1,0],[0,1]],[[.2,.1],[.7,.1],[.2,.8]]])
        before=copy.deepcopy(mesh);source=copy.deepcopy(mesh['positions']);offsets=[0,1,1]
        self.assertEqual(study._retain_displaced_normal_side(mesh,source,offsets),1)
        self.assertEqual(mesh['indices'],[0,3,4])
        self.assertEqual(mesh['positions'][:3],before['positions'])
        self.assertEqual(mesh['normals'][:3],before['normals'])
        self.assertEqual([mesh['positions'][i] for i in mesh['indices']],before['positions'])
        self.assertEqual(mesh['normals'][3:],[[0,0,-1],[0,0,-1]])
        for original,current in zip(before['uvChannels'],mesh['uvChannels']):
            self.assertEqual([current[i] for i in mesh['indices']],original)
        immutable=copy.deepcopy(mesh)
        self.assertEqual(study._retain_displaced_normal_side(mesh,source,offsets),0)
        self.assertEqual(mesh,immutable)

    def test_low_terrain_and_every_uv_channel_are_exact(self):
        doc=document([[[20000,0,5000],[21000,0,5100],[20000,1000,5200]]]);before=copy.deepcopy(doc)
        mesh,audit=study.refine_saved_highland(doc,TRANSFORM,BOUNDS)
        self.assertEqual(doc,before);self.assertEqual(mesh['positions'],doc['triangles'][0]['positions'])
        self.assertEqual(mesh['normals'],doc['triangles'][0]['normals'])
        self.assertEqual(mesh['uvs'],doc['triangles'][0]['uvChannels'][0])
        self.assertEqual(mesh['lightmapUvs'],doc['triangles'][0]['uvChannels'][1])
        self.assertEqual(audit['untouchedSourceTriangles'],1);self.assertEqual(audit['maximumActualOffsetCm'],0)
    def test_upper_edit_footprint_stays_protected_even_above_its_roof(self):
        doc=document([[[4000,0,33000],[5000,0,32000],[4000,1000,31000]]])
        mesh,audit=study.refine_saved_highland(doc,TRANSFORM,BOUNDS)
        self.assertEqual(mesh['positions'],doc['triangles'][0]['positions'])
        self.assertEqual(mesh['indices'],[0,1,2]);self.assertEqual(audit['refinementPasses'],[])
        self.assertEqual(study.eligibility([34500,0,40000],BOUNDS),0)
    def test_shared_edges_are_conforming_and_uv_interpolation_is_preserved(self):
        a,b,c,d=[20000,0,24000],[21200,0,24000],[20000,1200,24000],[21200,1200,24000]
        mesh,audit=study.refine_saved_highland(document([[a,b,c],[b,d,c]]),TRANSFORM,BOUNDS)
        edges={}
        for offset in range(0,len(mesh['indices']),3):
            ids=mesh['indices'][offset:offset+3]
            for left,right in zip(ids,ids[1:]+ids[:1]):
                points=[mesh['positions'][i] for i in (left,right)]
                if all(abs(p[0]+p[1]-21200)<1e-6 for p in points):
                    key=tuple(sorted(tuple(p) for p in points));edges[key]=edges.get(key,0)+1
        self.assertTrue(edges);self.assertTrue(all(count==2 for count in edges.values()))
        self.assertTrue(audit['allNativeUvChannelsPreserved']==2)
        self.assertTrue(all(all(math.isfinite(v) for v in n) and abs(sum(v*v for v in n)-1)<1e-6 for n in mesh['normals']))
    def test_all_split_patterns_preserve_oriented_area(self):
        corners=[dict(p=p,n=[0,0,-1],uv=[[0,0]]) for p in ([0,0,24000],[1000,0,24000],[0,1000,24000])]
        for mask in range(8):
            marked={study._edge(corners[i],corners[(i+1)%3]) for i in range(3) if mask&(1<<i)}
            children=study._split(corners,marked);areas=[]
            for row in children:
                a,b,c=[v['p'] for v in row]
                areas.append(study._cross([b[i]-a[i] for i in range(3)],[c[i]-a[i] for i in range(3)])[2])
            self.assertEqual(len(children),1+len(marked));self.assertTrue(all(a>0 for a in areas));self.assertAlmostEqual(sum(areas),1000000)
    def test_signed_gullies_and_ledges_are_bounded_and_deterministic(self):
        values=[study.relief_offset([45000,y,28000],BOUNDS) for y in range(-10000,10000,100)]
        self.assertLess(min(values),-100);self.assertGreater(max(values),100)
        self.assertGreaterEqual(min(values),-study.SPEC['maximumCutCm']);self.assertLessEqual(max(values),study.SPEC['maximumRiseCm'])
        self.assertEqual(values,[study.relief_offset([45000,y,28000],BOUNDS) for y in range(-10000,10000,100)])
        self.assertEqual(study.relief_offset([45000,0,16000],BOUNDS),0)
    def test_malformed_nonfinite_duplicate_and_wrong_uv_counts_fail(self):
        base=document([[[20000,0,24000],[21000,0,24000],[20000,1000,24000]]])
        cases=[lambda d:d.update(readOnly=False),lambda d:d.update(invalidValues=False),
            lambda d:d['triangles'][0]['positions'][0].__setitem__(0,math.nan),
            lambda d:d['triangles'][0].update(materialIndex=True),lambda d:d['triangles'].append(copy.deepcopy(d['triangles'][0])),
            lambda d:d['triangles'][0]['uvChannels'][1][0].__setitem__(0,math.inf)]
        for change in cases:
            doc=copy.deepcopy(base);change(doc)
            with self.assertRaises(ValueError):study.refine_saved_highland(doc,TRANSFORM,BOUNDS)
    def test_unreviewed_transform_bounds_and_triangle_budget_fail(self):
        doc=document([[[20000,0,24000],[21000,0,24000],[20000,1000,24000]]])
        for bounds in ([[0,0,0],[0,1,1]],[[0,0,0],[1,1,math.nan]]):
            with self.assertRaises(ValueError):study.refine_saved_highland(doc,TRANSFORM,bounds)
        with self.assertRaises(ValueError):study.refine_saved_highland(doc,dict(TRANSFORM,scale=[2,1,1]),BOUNDS)
        with patch.dict(study.SPEC,maximumOutputTriangles=1):
            with self.assertRaisesRegex(ValueError,'budget'):study.refine_saved_highland(doc,TRANSFORM,BOUNDS)
    def test_closure_retains_original_controls_and_covers_both_terrain_ends(self):
        original=[[78000+i*2000,70000+i*20000,15000+i*1000] for i in range(8)];before=copy.deepcopy(original)
        controls=study.closure_controls(original)
        self.assertEqual(original,before);self.assertEqual(controls[-8:],original)
        self.assertEqual(len(controls),22);self.assertTrue(all(a[1]<b[1] for a,b in zip(controls,controls[1:])))
        self.assertLess(controls[0][1],-52000);self.assertGreater(controls[-1][1],52000)
        with self.assertRaises(ValueError):study.closure_controls(original[:7])
    def test_color_recipe_uses_original_rock_and_measured_native_masks(self):
        self.assertEqual(study.COLOR_RECIPE['worldPositionMask'],[1,1,1,1,0])
        self.assertEqual(study.COLOR_RECIPE['normalMask'],[0,0,0,0,0])
        self.assertIn('Rock*',study.COLOR_SHADER);self.assertIn('-normalize(N).z',study.COLOR_SHADER)
        self.assertFalse(study.COLOR_RECIPE['normalRootChanges']);self.assertFalse(study.COLOR_RECIPE['shaderCompiled'])
    def test_apron_meets_exact_far_and_side_rim_and_excludes_retained_rectangle(self):
        doc=document([[[0,-52000,0],[65000,-52000,0],[65000,52000,0]],
            [[0,-52000,0],[65000,52000,0],[0,52000,0]],
            [[0,0,2400],[1000,0,2400],[0,1000,2400]]])
        # The forward raised edge remains unrelated to the far/side zero-height rim.
        before=study.digest(doc);mesh,audit=study.build_saved_boundary_apron(doc,TRANSFORM)
        self.assertEqual(study.digest(doc),before);self.assertFalse(mesh['collision'])
        self.assertTrue(audit['sourceBoundaryPointsPreserved']);self.assertFalse(audit['forwardBoundaryExtended'])
        self.assertTrue(all(not (25000<p[0]<90000 and -52000<p[1]<52000) for p in mesh['positions']))
        self.assertTrue(all(all(math.isfinite(v) for v in p) for p in mesh['positions']))
        self.assertFalse(audit['nativeVerified'])
    def test_apron_rejects_unmeasured_edge_height_instead_of_normalizing_it(self):
        doc=document([[[0,-52000,0],[65000,-52000,0],[65000,52000,2]],[[0,-52000,0],[65000,52000,2],[0,52000,0]]])
        with self.assertRaisesRegex(ValueError,'boundary differs'):study.build_saved_boundary_apron(doc,TRANSFORM)
    def test_acceptance_and_gameplay_flags_stay_false(self):
        mesh,audit=study.refine_saved_highland(document([[[20000,0,24000],[21000,0,24000],[20000,1000,24000]]]),TRANSFORM,BOUNDS)
        for key in ('collisionChanged','navigationChanged','lightingChanged','walkingRecordsChanged','nativeVerified','performanceVerified','visualApproved','releaseAcceptance'):
            self.assertIs(audit[key],False)

if __name__=='__main__':unittest.main()
