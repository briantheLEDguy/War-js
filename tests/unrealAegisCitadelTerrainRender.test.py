"""Portable render-array fixtures only; these never represent native acceptance."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts/unreal'))
from aegis_citadel_terrain import native_terrain_carve_document
from aegis_citadel_terrain_render_readback import checked_rendered_carve, RENDER_POLICY

SOURCE = '/Game/Capitals/crownward/Terrain_mountain.Terrain_mountain'
TARGET = '/Game/WorldRebuild/AegisCitadel_0123456789ab/Meshes/SM_HallCarvedMountain.SM_HallCarvedMountain'


def fixture(generated=True):
    points = [[900,0,6010],[800,-200,6010],[800,200,6010],
              [900,0,6010],[1100,0,6010],[900,200,6010], [0,0,0],[100,0,0],[0,100,0]]
    uv = [[0,0],[1,0],[0,1]] * 3
    source = dict(schemaVersion=1,readOnly=True,available=True,valid=True,lod=0,mesh=SOURCE,invalidValues=0,
        sourcePolicy='committed_mesh_description_bulk_data_no_working_copy',coordinateSpace='mesh_local_cm',
        triangleOrder='native_triangle_ids_and_corner_order',optionalAttributePolicy='stored_registered_values_authorship_not_inferred',
        sourceTriangleCount=3,sourceVertexCount=8,sourceVertexInstanceCount=9,
        triangleIds=[100,101,102],trianglePolygonIds=[100,101,102],trianglePolygonGroupIds=[0,0,0],
        cornerVertexIds=[3,4,5,3,6,7,0,1,2],cornerVertexInstanceIds=list(range(9)),
        materialSlots=[dict(index=0,slotName='Surface',importedSlotName='Surface',material='/Game/Materials/Portable.Portable')],
        polygonGroups=[dict(id=0,slotName='Surface',materialIndex=0)],
        data=dict(positions=points,indices=list(range(9)),normals=[[0,0,1]]*9,uvs=uv,uvChannels=[uv],triangleMaterials=[0]*3))
    raw=json.dumps(source)
    wrapper=native_terrain_carve_document(raw,source_provenance={'portableFixture':True})
    policy=dict(sourceLods=1,buildSettings=[dict(bGenerateLightmapUVs=generated,srcLightmapIndex=0,dstLightmapIndex=1,
        buildScale3D={'x':1,'y':1,'z':1})],reductionSettings=[dict(percentTriangles=1,percentVertices=1,maxDeviation=0,bRecalculateNormals=False)],
        mesh={'nanite_settings':{'bEnabled':False}},bodySetup={})

    def render(data, mesh):
        triangles=[]
        for offset in range(0,len(data['indices']),3):
            ids=data['indices'][offset:offset+3]
            channels=[[channel[i] for i in ids] for channel in data['uvChannels']]
            if generated: channels.append([[.1,.1],[.3,.1],[.1,.3]])
            triangles.append(dict(index=offset//3,section=0,materialIndex=data['triangleMaterials'][offset//3],vertexIds=ids,
                positions=[data['positions'][i] for i in ids],normals=[[0,0,1]]*3,tangents=[[1,0,0]]*3,
                binormals=[[0,1,0]]*3,uvChannels=channels))
        return dict(schemaVersion=1,readOnly=True,available=True,valid=True,mesh=mesh,lod=0,policy=RENDER_POLICY,
                    uvChannels=2 if generated else 1,invalidValues=0,triangles=triangles)
    return wrapper,render(source['data'],SOURCE),render(wrapper['data'],TARGET),policy


def compare(values):return checked_rendered_carve(*values,TARGET)


class CitadelTerrainRenderedTests(unittest.TestCase):
    def test_exact_original_vertex_star_and_generated_atlas_repack(self):
        values=fixture();wrapper,before,after,policy=values
        for face in after['triangles']:face['uvChannels'][1]=[[.7,.7],[.9,.7],[.7,.9]]
        # Only the unchanged face sharing a genuinely touched original native
        # vertex may receive a different healthy computed basis.
        after['triangles'][0]['normals']=[[0,1,0]]*3
        after['triangles'][0]['binormals']=[[0,0,-1]]*3
        report=compare(values)
        self.assertEqual(report['computedBasisExcludedSourceTriangleIds'],[100])
        self.assertEqual(report['touchedVertexStarSourceTriangleIds'],[100,101])
        self.assertEqual(report['computedBasisComparedTriangles'],1)
        self.assertEqual(report['authoredUvChannels'],[0]);self.assertEqual(report['generatedDestinationUvChannels'],[1])
        self.assertEqual(report['touchedVertexStarWorldBounds'],[[25800,-200,6010],[26100,200,6010]])
        self.assertFalse(report['visualApproved']);self.assertFalse(report['nativeCollisionVerified'])

    def test_basis_change_outside_exact_star_rejects(self):
        values=fixture();face=values[2]['triangles'][-1]
        face['normals']=[[0,1,0]]*3;face['binormals']=[[0,0,-1]]*3
        with self.assertRaises(ValueError):compare(values)

    def test_star_does_not_exempt_position_material_winding_or_authored_uv(self):
        for mutate in (lambda f:f['positions'][0].__setitem__(0,905),
                       lambda f:f.__setitem__('materialIndex',1),
                       lambda f:f['uvChannels'][0][0].__setitem__(0,.2),
                       lambda f:[f[key].reverse() for key in ('positions','normals','tangents','binormals')]
                               + [channel.reverse() for channel in f['uvChannels']]):
            values=fixture();mutate(values[2]['triangles'][0])
            with self.subTest(mutate=mutate),self.assertRaises(ValueError):compare(values)

    def test_generated_destination_is_policy_only_and_finite_bounded(self):
        for mutate in (lambda v:v[3]['buildSettings'][0].__setitem__('bGenerateLightmapUVs',False),
                       lambda v:v[3]['buildSettings'][0].__setitem__('dstLightmapIndex',0),
                       lambda v:v[2]['triangles'][0]['uvChannels'][1][0].__setitem__(0,2),
                       lambda v:v[2]['triangles'][0]['uvChannels'][1][0].__setitem__(0,float('nan')),
                       lambda v:v[2].__setitem__('uvChannels',3)):
            values=fixture();mutate(values)
            with self.subTest(mutate=mutate),self.assertRaises(ValueError):compare(values)
        report=compare(fixture(False));self.assertEqual(report['generatedDestinationUvChannels'],[])

    def test_reordered_rotated_actual_faces_preserve_orientation(self):
        values=fixture();after=values[2]
        after['triangles'].reverse()
        for index,face in enumerate(after['triangles']):
            face['index']=index
            for key in ('positions','normals','tangents','binormals','vertexIds'):face[key]=face[key][1:]+face[key][:1]
            face['uvChannels']=[channel[1:]+channel[:1] for channel in face['uvChannels']]
        compare(values)

    def test_complete_render_counts_basis_and_raw_identity_are_required(self):
        for mutate in (lambda v:v[2]['triangles'].pop(),
                       lambda v:v[2]['triangles'].__setitem__(-1,deepcopy(v[2]['triangles'][0])),
                       lambda v:v[2]['triangles'][0]['tangents'].__setitem__(0,[0,0,0]),
                       lambda v:v[0].__setitem__('sourceExportSha256','f'*64),
                       lambda v:v[0]['carveReceipt'].__setitem__('touchedSourceTriangles',[0,1]),
                       lambda v:v[3]['reductionSettings'][0].__setitem__('percentTriangles',.5)):
            values=fixture();mutate(values)
            with self.subTest(mutate=mutate),self.assertRaises(ValueError):compare(values)


if __name__=='__main__':unittest.main()
