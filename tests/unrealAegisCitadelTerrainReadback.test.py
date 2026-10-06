"""Portable comparator regressions; these fixtures do not constitute native evidence."""
import copy
import hashlib
import json
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts/unreal'))
from aegis_citadel_terrain_readback import checked_committed_carve, checked_native_policy, SOURCE_POLICY, CORNER_POLICY, _stored

TARGET='/Game/WorldRebuild/AegisCitadel_123456789abc/Meshes/SM_HallCarvedMountain.SM_HallCarvedMountain'


def fixture():
    original=dict(mesh='/Game/Capitals/crownward/Terrain_mountain.Terrain_mountain',data=dict(positions=[[900,0,6000],[900,120,6000],[1020,0,6000]],
        normals=[[0,0,1]]*3,tangents=[[0,1,0]]*3,vertexColors=[[.1,.2,.3,.4]]*3,
        binormalSigns=[1]*3,uvs=[[0,0],[0,1],[1,0]],
        uvChannels=[[[0,0],[0,1],[1,0]],[[.125,.25],[.375,.5],[.625,.75]]],
        indices=[0,1,2],triangleMaterials=[0]),
        materialSlots=[dict(index=0,slotName='Surface')],polygonGroups=[dict(id=0,slotName='Surface')],trianglePolygonGroupIds=[0],
        cornerVertexInstanceIds=[4,6,11],cornerVertexIds=[2,7,9],triangleIds=[5])
    expected=copy.deepcopy(original['data'])
    expected['indices']=[0,1,3,0,3,4];expected['triangleMaterials']=[0,0]
    for key in ('positions','normals','tangents','vertexColors','binormalSigns','uvs'):
        values=expected[key]
        if key=='positions':values.extend([[960,60,6000],[960,0,6000]])
        elif key=='uvs':values.extend([[.5,.5],[.5,0]])
        else:values.extend(copy.deepcopy(values[:2]))
    expected['uvChannels'][0]=copy.deepcopy(expected['uvs'])
    expected['uvChannels'][1].extend([[.5,.625],[.375,.5]])
    raw=json.dumps(original)
    wrapper=dict(schemaVersion=1,sourceExportPayload=raw,sourceExportSha256=hashlib.sha256(raw.encode()).hexdigest(),data=expected,
        carveReceipt=dict(addedBoundaryVertices=[dict(index=3,sourceIndices=[0,1,2],weights=[0,.5,.5]),
            dict(index=4,sourceIndices=[0,1,2],weights=[.5,0,.5])],outsidePreservation=dict(sourceTriangleIds=[])))
    ids=expected['indices'];attrs=set(expected)-{'indices','triangleMaterials'}
    stored=dict(schemaVersion=1,readOnly=True,available=True,valid=True,sourcePolicy=SOURCE_POLICY,cornerPolicy=CORNER_POLICY,
        invalidValues=0,mesh=TARGET,instanceIds=[4,6,11,12,13],vertexIds=[2,7,9,16,17],
        sourceVertexCount=6,sourceVertexInstanceCount=5,sourceTriangleCount=2,data={k:_stored(expected[k]) for k in attrs})
    old_topology=dict(vertices=[dict(id=i,position=p) for i,p in zip([2,7,9,15],original['data']['positions']+[[77,88,99]])],
        edges=[dict(id=0,vertices=[2,7],hard=False),dict(id=1,vertices=[7,9],hard=False),dict(id=2,vertices=[9,2],hard=True)],
        triangles=[dict(id=5,polygonId=3,groupId=0,instances=[4,6,11],edges=[0,1,2])])
    stored['topology']=copy.deepcopy(old_topology)
    stored['topology']['vertices'] += [dict(id=16,position=[960,60,6000]),dict(id=17,position=[960,0,6000])]
    stored['topology']['edges'] += [dict(id=3,vertices=[7,16],hard=False),dict(id=4,vertices=[16,2],hard=False),
        dict(id=5,vertices=[16,17],hard=False),dict(id=6,vertices=[17,2],hard=True)]
    stored['topology']['triangles']=[dict(id=5,polygonId=3,groupId=0,instances=[4,6,12],edges=[0,3,4]),
        dict(id=6,polygonId=4,groupId=0,instances=[4,12,13],edges=[4,5,6])]
    original_stored=dict(schemaVersion=1,readOnly=True,available=True,valid=True,sourcePolicy=SOURCE_POLICY,
        cornerPolicy=CORNER_POLICY,mesh=original['mesh'],instanceIds=[4,6,11],vertexIds=[2,7,9],
        sourceVertexCount=4,sourceVertexInstanceCount=3,sourceTriangleCount=1,topology=old_topology,
        data={k:_stored(original['data'][k]) for k in attrs})
    expanded={}
    for key in attrs:
        value=expected[key]
        expanded[key]=_stored([[c[i] for i in ids] for c in value] if key=='uvChannels' else [value[i] for i in ids])
    expanded.update(indices=list(range(6)),triangleMaterials=[0,0])
    referenced=dict(readOnly=True,available=True,valid=True,sourcePolicy=SOURCE_POLICY,mesh=TARGET,
        sourceVertexCount=6,sourceVertexInstanceCount=5,sourceTriangleCount=2,data=expanded,
        materialSlots=original['materialSlots'],polygonGroups=original['polygonGroups'],trianglePolygonGroupIds=[0,0],
        cornerVertexInstanceIds=[[4,6,11,12,13][i] for i in ids],cornerVertexIds=[[2,7,9,16,17][i] for i in ids])
    return wrapper,referenced,stored,original_stored

def check(wrapper,referenced,stored,original_stored):
    return checked_committed_carve(wrapper,referenced,stored,TARGET,original_stored)


class TerrainReadbackTests(unittest.TestCase):
    def test_complete_stored_prefix_includes_a_genuinely_unused_corner(self):
        result=check(*fixture())
        self.assertEqual(result['unusedStoredCorners'],1)
        self.assertEqual(result['sourcePrefixCorners'],3)
        self.assertTrue(result['nativeSourcePrefixPreserved'])
        self.assertIs(result['nativeCollisionVerified'],False)
        self.assertIs(result['visualApproved'],False)
        self.assertEqual(result['nativeUnusedOriginalVerticesPreserved'],1)

    def test_shared_mapping_orphan_vertices_and_edge_hardness_cannot_be_flattened(self):
        for mutate in (lambda s:s['vertexIds'].__setitem__(0,0),
                       lambda s:s['topology']['vertices'][3]['position'].__setitem__(0,0),
                       lambda s:s['topology']['edges'][2].update(hard=False),
                       lambda s:s['topology']['edges'][-1].update(hard=False)):
            wrapper,referenced,stored,original_stored=fixture();mutate(stored)
            with self.subTest(mutation=mutate),self.assertRaises(ValueError):check(wrapper,referenced,stored,original_stored)

    def test_unused_position_normal_color_sign_and_secondary_uv_corruption_reject(self):
        for key in ('positions','normals','vertexColors','binormalSigns','tangents','uvChannels'):
            wrapper,referenced,stored,original_stored=fixture()
            values=stored['data'][key]
            if key=='uvChannels':values[1][2][0]=.99
            elif key=='binormalSigns':values[2]=-1
            else:values[2][0]=.99
            with self.subTest(key=key),self.assertRaises(ValueError):check(wrapper,referenced,stored,original_stored)

    def test_reversed_referenced_face_rejects(self):
        wrapper,referenced,stored,original_stored=fixture()
        referenced['cornerVertexInstanceIds'][1],referenced['cornerVertexInstanceIds'][2]=referenced['cornerVertexInstanceIds'][2],referenced['cornerVertexInstanceIds'][1]
        with self.assertRaises(ValueError):check(wrapper,referenced,stored,original_stored)

    def test_missing_attribute_and_stored_instance_reject(self):
        for mutate in (lambda s:s['data'].pop('tangents'),lambda s:s['instanceIds'].pop()):
            wrapper,referenced,stored,original_stored=fixture();mutate(stored)
            with self.assertRaises(ValueError):check(wrapper,referenced,stored,original_stored)

    def test_hash_or_material_group_tampering_rejects(self):
        wrapper,referenced,stored,original_stored=fixture();wrapper['sourceExportSha256']='0'*64
        with self.assertRaises(ValueError):check(wrapper,referenced,stored,original_stored)
        wrapper,referenced,stored,original_stored=fixture();referenced['trianglePolygonGroupIds'][1]=1
        with self.assertRaises(ValueError):check(wrapper,referenced,stored,original_stored)

    def test_working_cache_and_unavailable_data_cannot_substitute_for_committed_data(self):
        for mutate in (lambda s:s.update(sourcePolicy='working_copy'),lambda s:s.update(available=False)):
            wrapper,referenced,stored,original_stored=fixture();mutate(stored)
            with self.assertRaises(ValueError):check(wrapper,referenced,stored,original_stored)

    def test_structured_native_policy_retains_full_fields_and_rejects_unavailable_or_incomplete(self):
        policy=dict(sourceLods=1,buildSettings=[{'actualBuildField':1}],reductionSettings=[{'actualReductionField':.3}],
            mesh=dict(allow_cpu_access=True,auto_compute_lod_screen_size=True,light_map_coordinate_index=0,
                      light_map_resolution=64,lod_for_collision=0,lod_group='None',nanite_settings={'bEnabled':False}),
            bodySetup=dict(collision_trace_flag=3,double_sided_geometry=True,physics_type=0,collision_reponse=0,
                           generate_mirrored_collision=True,generate_non_mirrored_collision=True,
                           build_scale3d={'x':1,'y':1,'z':1},walkable_slope_override={'walkableSlopeAngle':0},phys_material=''))
        row=dict(schemaVersion=1,readOnly=True,available=True,valid=True,mesh=TARGET,
                 policySource='native_persistent_accessors_and_full_reflected_source_structs',policy=policy)
        self.assertEqual(checked_native_policy(json.dumps(row),TARGET),policy)
        for mutate in (lambda r:r.update(available=False),lambda r:r['policy']['buildSettings'].clear(),
                       lambda r:r['policy']['mesh'].pop('auto_compute_lod_screen_size'),
                       lambda r:r['policy']['bodySetup'].update(build_scale3d='invented repr'),
                       lambda r:r['policy']['buildSettings'][0].update(actualBuildField=float('nan'))):
            bad=copy.deepcopy(row);mutate(bad)
            with self.subTest(mutation=mutate),self.assertRaises(ValueError):checked_native_policy(json.dumps(bad),TARGET)


if __name__=='__main__':unittest.main()
